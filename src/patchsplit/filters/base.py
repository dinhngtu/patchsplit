from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from importlib import import_module

from ..categories import Category, MatchStrength
from ..model import ChangeUnit, Evidence


class ChangeFilter(ABC):
    """A side-effect-free source of classification evidence."""

    name: str

    @abstractmethod
    def classify(self, change: ChangeUnit) -> Iterable[Evidence]:
        raise NotImplementedError


@dataclass(frozen=True)
class FilterSet:
    filters: tuple[ChangeFilter, ...]

    def classify(self, change: ChangeUnit) -> tuple[Evidence, ...]:
        evidence: list[Evidence] = []
        for change_filter in self.filters:
            for item in change_filter.classify(change):
                if not isinstance(item, Evidence):
                    raise TypeError(
                        f"filter {change_filter.name!r} returned {type(item).__name__}, "
                        "expected Evidence"
                    )
                if not isinstance(item.category, Category):
                    raise TypeError(
                        f"filter {change_filter.name!r} used an unregistered category: "
                        f"{item.category!r}"
                    )
                if not isinstance(item.strength, MatchStrength):
                    raise TypeError(
                        f"filter {change_filter.name!r} used an invalid match strength: "
                        f"{item.strength!r}"
                    )
                evidence.append(item)
        return tuple(evidence)


def load_filter_module(module_name: str) -> Sequence[ChangeFilter]:
    """Load optional filters without coupling them to the core package.

    A module may expose either ``get_filters()`` or an iterable ``FILTERS``.
    """

    module = import_module(module_name)
    if hasattr(module, "get_filters"):
        filters = module.get_filters()
    elif hasattr(module, "FILTERS"):
        filters = module.FILTERS
    else:
        raise ValueError(f"filter module {module_name!r} must expose get_filters() or FILTERS")
    return tuple(filters)


def evidence(
    change_filter: ChangeFilter,
    category: Category,
    strength: MatchStrength,
    reason: str,
) -> Evidence:
    return Evidence(category, strength, reason, change_filter.name)
