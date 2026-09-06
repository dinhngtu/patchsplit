from __future__ import annotations

import difflib
import re
from collections import defaultdict
from pathlib import Path

import pygit2

from .inventory import Inventory, InventoryItem
from .model import ChangeUnit


def _label(item: InventoryItem) -> str:
    if item.resolution.owner is not None:
        return item.resolution.owner.value
    return "mixed" if item.resolution.mixed else "unresolved"


def _blob_bytes(repo: pygit2.Repository, oid: str) -> bytes:
    if not oid:
        return b""
    obj = repo[oid]
    if not isinstance(obj, pygit2.Blob):
        raise TypeError(f"{oid} is not a blob")
    return bytes(obj.data)


def _hunk_start(change: ChangeUnit) -> int:
    # In unified-diff coordinates an empty old range names the line before the
    # insertion; a non-empty range is one-based.
    return change.old_start if change.old_lines == 0 else change.old_start - 1


def _snapshot(
    base: bytes,
    changes: list[tuple[ChangeUnit, str]],
    included: set[str],
) -> bytes:
    base_lines = base.splitlines(keepends=True)
    result: list[bytes] = []
    cursor = 0

    for change, label in sorted(changes, key=lambda pair: _hunk_start(pair[0])):
        start = _hunk_start(change)
        end = start + change.old_lines
        if start < cursor or end > len(base_lines):
            raise ValueError(f"overlapping or invalid hunk for {change.path}: {change.header}")

        deleted = [line.content for line in change.lines if line.origin == "-"]
        if b"".join(base_lines[start:end]) != b"".join(deleted):
            raise ValueError(f"old content does not match hunk for {change.path}: {change.header}")

        result.extend(base_lines[cursor:start])
        if label in included:
            result.extend(line.content for line in change.lines if line.origin == "+")
        else:
            result.extend(base_lines[start:end])
        cursor = end

    result.extend(base_lines[cursor:])
    return b"".join(result)


def _exists(
    status: str,
    changes: list[tuple[ChangeUnit, str]],
    included: set[str],
) -> bool:
    selected = sum(label in included for _, label in changes)
    if status == "A":
        return selected > 0
    if status == "D":
        return selected < len(changes)
    return True


def _fix_missing_newlines(lines: list[bytes]) -> bytes:
    output = bytearray()
    for index, line in enumerate(lines):
        output.extend(line)
        if index >= 2 and not line.endswith(b"\n"):
            output.extend(b"\n\\ No newline at end of file\n")
    return bytes(output)


def _file_diff(
    path: str,
    before: bytes,
    after: bytes,
    *,
    before_exists: bool,
    after_exists: bool,
) -> bytes:
    if before == after and before_exists == after_exists:
        return b""

    encoded_path = path.encode("utf-8", "surrogateescape")
    old_name = b"a/" + encoded_path if before_exists else b"/dev/null"
    new_name = b"b/" + encoded_path if after_exists else b"/dev/null"
    lines = list(
        difflib.diff_bytes(
            difflib.unified_diff,
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=old_name,
            tofile=new_name,
            n=3,
        )
    )
    if not lines:
        raise ValueError(f"cannot represent empty-file-only change for {path}")

    header = b"diff --git a/" + encoded_path + b" b/" + encoded_path + b"\n"
    if not before_exists:
        header += b"new file mode 100644\n"
    elif not after_exists:
        header += b"deleted file mode 100644\n"
    return header + _fix_missing_newlines(lines)


def write_patch_series(inventory: Inventory, output: str | Path) -> tuple[Path, ...]:
    """Write contextual patches in the order listed by the series file.

    A mixed or unresolved hunk is kept whole and emitted under the corresponding
    label. Each stage is diffed against the cumulative previous stage, so hunks
    from different owners may safely touch the same file.
    """

    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    repo = pygit2.Repository(inventory.repository)

    by_path: dict[str, list[tuple[ChangeUnit, str]]] = defaultdict(list)
    labels: list[str] = []
    for item in inventory.items:
        label = _label(item)
        by_path[item.change.path].append((item.change, label))
        if label not in labels:
            labels.append(label)

    bases = {
        path: _blob_bytes(repo, changes[0][0].old_blob_id) for path, changes in by_path.items()
    }

    # Refuse to publish a series if reconstructing every selected hunk does not
    # produce the blob that libgit2 originally classified.
    all_labels = set(labels)
    for path, changes in by_path.items():
        target_oid = changes[-1][0].new_blob_id
        if target_oid and _snapshot(bases[path], changes, all_labels) != _blob_bytes(
            repo, target_oid
        ):
            raise ValueError(f"reconstructed content does not match target blob for {path}")

    written: list[Path] = []
    included: set[str] = set()
    for number, label in enumerate(labels, 1):
        next_included = included | {label}
        patch = bytearray()
        for path, changes in by_path.items():
            if not any(change_label == label for _, change_label in changes):
                continue
            status = changes[0][0].status
            before = _snapshot(bases[path], changes, included)
            after = _snapshot(bases[path], changes, next_included)
            patch.extend(
                _file_diff(
                    path,
                    before,
                    after,
                    before_exists=_exists(status, changes, included),
                    after_exists=_exists(status, changes, next_included),
                )
            )

        safe_label = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") or "patch"
        path = destination / f"{number:04d}-{safe_label}.patch"
        path.write_bytes(bytes(patch))
        written.append(path)
        included = next_included

    (destination / "series").write_text(
        "".join(f"{path.name}\n" for path in written),
        encoding="utf-8",
        newline="\n",
    )
    return tuple(written)
