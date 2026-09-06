from __future__ import annotations

from dataclasses import dataclass

from .categories import Category, MatchStrength
from .filters import FilterSet
from .model import ChangeLine, ChangeUnit
from .resolve import resolve


@dataclass(frozen=True)
class LineSlice:
    """A classifier-derived sub-hunk boundary suggestion.

    Slices are evidence for later structural atomization; they are not directly
    emitted as patches because adjacent C/C++ table entries or blocks may need
    to remain atomic for an intermediate revision to compile.
    """

    start_index: int
    end_index: int
    origins: str
    old_start: int | None
    old_end: int | None
    new_start: int | None
    new_end: int | None
    categories: tuple[Category, ...]
    preview: str


def _line_unit(parent: ChangeUnit, line: ChangeLine, index: int) -> ChangeUnit:
    old_number = line.old_lineno if line.old_lineno >= 0 else parent.old_start
    new_number = line.new_lineno if line.new_lineno >= 0 else parent.new_start
    return ChangeUnit(
        path=parent.path,
        status=parent.status,
        old_blob_id=parent.old_blob_id,
        new_blob_id=parent.new_blob_id,
        old_start=old_number,
        old_lines=line.num_lines if line.old_lineno >= 0 else 0,
        new_start=new_number,
        new_lines=line.num_lines if line.new_lineno >= 0 else 0,
        header=f"{parent.header} [line {index}]",
        section=parent.section,
        lines=(line,),
        patch_data=line.origin.encode("ascii", "replace") + line.content,
    )


def suggest_line_slices(
    change: ChangeUnit,
    filters: FilterSet,
) -> tuple[LineSlice, ...]:
    classified: list[tuple[int, ChangeLine, tuple[Category, ...]]] = []
    for index, line in enumerate(change.lines):
        if line.origin not in {"+", "-"}:
            continue
        result = resolve(filters.classify(_line_unit(change, line, index)))
        categories = tuple(
            candidate.category
            for candidate in result.candidates
            if candidate.strength >= MatchStrength.STRONG
            and candidate.category != Category.CLEANUP_WHITESPACE_ONLY
        )
        classified.append((index, line, categories))

    if not classified:
        return ()

    groups: list[list[tuple[int, ChangeLine, tuple[Category, ...]]]] = []
    for entry in classified:
        if groups and entry[0] == groups[-1][-1][0] + 1 and entry[2] == groups[-1][-1][2]:
            groups[-1].append(entry)
        else:
            groups.append([entry])

    slices: list[LineSlice] = []
    for group in groups:
        old_numbers = [line.old_lineno for _, line, _ in group if line.old_lineno >= 0]
        new_numbers = [line.new_lineno for _, line, _ in group if line.new_lineno >= 0]
        preview = " / ".join(
            f"{line.origin}{line.content.decode('utf-8', 'replace').strip()}"
            for _, line, _ in group[:3]
            if line.content.strip()
        )
        slices.append(
            LineSlice(
                start_index=group[0][0],
                end_index=group[-1][0] + 1,
                origins="".join(line.origin for _, line, _ in group),
                old_start=min(old_numbers) if old_numbers else None,
                old_end=max(old_numbers) if old_numbers else None,
                new_start=min(new_numbers) if new_numbers else None,
                new_end=max(new_numbers) if new_numbers else None,
                categories=group[0][2],
                preview=preview[:180],
            )
        )
    return tuple(slices)
