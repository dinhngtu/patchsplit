from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import TextIO

from .inventory import Inventory, InventoryItem


def _evidence_record(item) -> dict[str, object]:
    return {
        "category": item.category.value,
        "strength": item.strength.name.lower(),
        "reason": item.reason,
        "filter_name": item.filter_name,
    }


def _candidate_record(item) -> dict[str, object]:
    return {
        "category": item.category.value,
        "strength": item.strength.name.lower(),
        "evidence": [_evidence_record(evidence) for evidence in item.evidence],
    }


def _slice_record(item) -> dict[str, object]:
    result = asdict(item)
    result["categories"] = [category.value for category in item.categories]
    return result


def _record(item: InventoryItem) -> dict[str, object]:
    change = item.change
    resolution = item.resolution
    return {
        "id": change.unit_id,
        "path": change.path,
        "status": change.status,
        "old_blob_id": change.old_blob_id,
        "new_blob_id": change.new_blob_id,
        "old_range": [change.old_start, change.old_lines],
        "new_range": [change.new_start, change.new_lines],
        "added": change.added_count,
        "deleted": change.deleted_count,
        "section": change.section,
        "preview": change.preview(),
        "raw_sha256": change.raw_sha256,
        "owner": resolution.owner.value if resolution.owner else None,
        "mixed": resolution.mixed,
        "candidates": [_candidate_record(candidate) for candidate in resolution.candidates],
        "line_slices": [_slice_record(line_slice) for line_slice in item.line_slices],
    }


def write_jsonl(inventory: Inventory, stream: TextIO) -> None:
    metadata = {
        "type": "metadata",
        "repository": inventory.repository,
        "base": inventory.base,
        "source_path_count": inventory.source_path_count,
        "selected_path_count": inventory.path_count,
        "unit_count": len(inventory.items),
        "mixed_count": inventory.mixed_count,
        "unresolved_count": inventory.unresolved_count,
        "libgit2_patch_id": inventory.patch_id,
    }
    stream.write(json.dumps(metadata, ensure_ascii=False) + "\n")
    stream.writelines(
        json.dumps({"type": "change", **_record(item)}, ensure_ascii=False) + "\n"
        for item in inventory.items
    )


def write_inventory(inventory: Inventory, output: str | Path | None) -> None:
    if output is None:
        import sys

        write_jsonl(inventory, sys.stdout)
        return
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as stream:
        write_jsonl(inventory, stream)
