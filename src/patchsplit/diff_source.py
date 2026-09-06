from __future__ import annotations

import os
import re
import subprocess
import tempfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pygit2

from .model import ChangeLine, ChangeUnit

_SECTION_RE = re.compile(r"^@@ .*? @@(?P<section>.*)$")


class PatchApplyError(RuntimeError):
    pass


@dataclass(frozen=True)
class PatchCollection:
    """Patch objects plus their owning Diff.

    Keeping the Diff alive matters: pygit2 patch wrappers may refer to memory
    owned by the parent libgit2 diff.
    """

    diff: pygit2.Diff
    patches: tuple[pygit2.Patch, ...]

    @property
    def patch_id(self) -> str | None:
        return str(self.diff.patchid) if self.patches else None


def _oid_text(oid: object) -> str:
    value = str(oid)
    return "" if set(value) == {"0"} else value


def _status_text(delta: pygit2.DiffDelta) -> str:
    return delta.status_char()


def _range_text(start: int, count: int) -> str:
    return str(start) if count == 1 else f"{start},{count}"


def _make_unit(
    patch: pygit2.Patch,
    path: str,
    group: list[ChangeLine],
    group_old_start: int,
    group_new_start: int,
    section: str,
) -> ChangeUnit | None:
    if not group:
        return None

    old_lines = sum(line.origin == "-" for line in group)
    new_lines = sum(line.origin == "+" for line in group)

    # Empty unified-diff ranges name the line before the insertion
    # or deletion point.
    old_start = group_old_start if old_lines else max(group_old_start - 1, 0)
    new_start = group_new_start if new_lines else max(group_new_start - 1, 0)

    header = f"@@ -{_range_text(old_start, old_lines)} +{_range_text(new_start, new_lines)} @@"
    if section:
        header += f" {section}"

    return ChangeUnit(
        path=path,
        status=_status_text(patch.delta),
        old_blob_id=_oid_text(patch.delta.old_file.id),
        new_blob_id=_oid_text(patch.delta.new_file.id),
        old_start=old_start,
        old_lines=old_lines,
        new_start=new_start,
        new_lines=new_lines,
        header=header,
        section=section,
        lines=tuple(group),
        patch_data=patch.data,
    )


def _to_units(patch: pygit2.Patch) -> Iterator[ChangeUnit]:
    path = patch.delta.new_file.path or patch.delta.old_file.path

    for hunk in patch.hunks:
        original_header = hunk.header.rstrip("\r\n")
        match = _SECTION_RE.match(original_header)
        section = match.group("section").strip() if match else ""

        old_cursor = hunk.old_start
        new_cursor = hunk.new_start
        group: list[ChangeLine] = []
        group_old_start = old_cursor
        group_new_start = new_cursor

        for line in hunk.lines:
            if line.origin == " ":
                unit = _make_unit(
                    patch,
                    path,
                    group,
                    group_old_start,
                    group_new_start,
                    section,
                )
                if unit is not None:
                    yield unit
                    group = []

                old_cursor += 1
                new_cursor += 1
                continue

            if not group and line.origin in {"+", "-"}:
                group_old_start = old_cursor
                group_new_start = new_cursor

            group.append(
                ChangeLine(
                    origin=line.origin,
                    content=line.raw_content,
                    old_lineno=line.old_lineno,
                    new_lineno=line.new_lineno,
                )
            )

            if line.origin == "-":
                old_cursor += 1
            elif line.origin == "+":
                new_cursor += 1

        unit = _make_unit(
            patch,
            path,
            group,
            group_old_start,
            group_new_start,
            section,
        )
        if unit is not None:
            yield unit


def collect_patches(
    repo: pygit2.Repository,
    patch_file: str | Path,
    base: str = "HEAD",
) -> PatchCollection:
    """Apply a patch to a temporary index initialized from ``base``.

    The repository's real index and working tree are not read as diff inputs
    and are not changed.
    """

    patch_path = Path(patch_file).resolve()
    if not patch_path.is_file():
        raise FileNotFoundError(f"patch file does not exist: {patch_path}")

    base_tree = repo.revparse_single(base).peel(pygit2.Tree)
    with tempfile.TemporaryDirectory(prefix="patchsplit-") as directory:
        index_path = Path(directory) / "index"
        index = pygit2.Index(index_path)
        index.read_tree(base_tree)
        index.write()

        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = str(index_path)
        workdir = repo.workdir
        command = [
            "git",
            "--git-dir",
            repo.path,
            *(["--work-tree", workdir] if workdir else []),
            "apply",
            "--cached",
            "--whitespace=nowarn",
            str(patch_path),
        ]
        result = subprocess.run(
            command,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "git apply failed"
            raise PatchApplyError(f"could not apply {patch_path} to {base}: {detail}")

        # git apply replaces the on-disk index, so reload it before diffing.
        index = pygit2.Index(index_path)
        diff = base_tree.diff_to_index(index, context_lines=0, interhunk_lines=0)
        patches = tuple(patch for patch in diff if patch is not None)
        return PatchCollection(diff=diff, patches=patches)


def iter_units(
    patches: Iterable[pygit2.Patch],
    *,
    path_prefixes: tuple[str, ...] = (),
) -> Iterator[ChangeUnit]:
    for patch in patches:
        path = patch.delta.new_file.path or patch.delta.old_file.path
        if path_prefixes and not any(path.startswith(prefix) for prefix in path_prefixes):
            continue
        yield from _to_units(patch)
