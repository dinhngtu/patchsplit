from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pygit2

from .atomize import LineSlice, suggest_line_slices
from .categories import Category
from .diff_source import collect_patches, iter_units
from .filters import FilterSet, builtin_filters
from .model import ChangeUnit, Resolution
from .resolve import resolve


@dataclass(frozen=True)
class InventoryItem:
    change: ChangeUnit
    resolution: Resolution
    line_slices: tuple[LineSlice, ...] = ()


@dataclass(frozen=True)
class Inventory:
    repository: str
    base: str
    source_path_count: int
    path_count: int
    items: tuple[InventoryItem, ...]
    patch_id: str | None

    @property
    def mixed_count(self) -> int:
        return sum(item.resolution.mixed for item in self.items)

    @property
    def unresolved_count(self) -> int:
        return sum(item.resolution.patch_category is Category.UNRESOLVED for item in self.items)

    def owner_counts(self) -> Counter[str]:
        return Counter(item.resolution.patch_category.value for item in self.items)


def build_inventory(
    repository: str | Path,
    *,
    patch_file: str | Path,
    base: str = "HEAD",
    filters: FilterSet | None = None,
    path_prefixes: tuple[str, ...] = (),
) -> Inventory:
    repo = pygit2.Repository(str(repository))
    active_filters = filters or FilterSet(builtin_filters())
    collection = collect_patches(repo, patch_file, base)
    items_list: list[InventoryItem] = []
    for change in iter_units(collection.patches, path_prefixes=path_prefixes):
        resolution = resolve(active_filters.classify(change))
        slices = suggest_line_slices(change, active_filters) if resolution.mixed else ()
        items_list.append(InventoryItem(change, resolution, slices))
    items = tuple(items_list)
    source_paths = {
        patch.delta.new_file.path or patch.delta.old_file.path for patch in collection.patches
    }
    selected_paths = {item.change.path for item in items}
    return Inventory(
        repository=str(Path(repo.workdir or repository).resolve()),
        base=base,
        source_path_count=len(source_paths),
        path_count=len(selected_paths),
        items=items,
        patch_id=collection.patch_id,
    )
