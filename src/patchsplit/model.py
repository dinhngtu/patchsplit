from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from hashlib import sha256

from .categories import Category, MatchStrength


@dataclass(frozen=True)
class ChangeLine:
    """A raw line from a libgit2 hunk."""

    origin: str
    content: bytes
    old_lineno: int
    new_lineno: int

    @property
    def num_lines(self) -> int:
        return self.content.count(b"\n")


@dataclass(frozen=True)
class ChangeUnit:
    """The initial classification unit.

    The prototype uses one zero-context Git hunk per unit. Filters may attach
    multiple labels; mixed units are candidates for a later atomizer pass.
    """

    path: str
    status: str
    old_blob_id: str
    new_blob_id: str
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    header: str
    section: str
    lines: tuple[ChangeLine, ...]
    patch_data: bytes = field(repr=False)

    @property
    def changed_bytes(self) -> bytes:
        return b"".join(
            line.origin.encode("ascii", "replace") + line.content
            for line in self.lines
            if line.origin in {"+", "-"}
        )

    @property
    def added_bytes(self) -> bytes:
        return b"".join(line.content for line in self.lines if line.origin == "+")

    @property
    def deleted_bytes(self) -> bytes:
        return b"".join(line.content for line in self.lines if line.origin == "-")

    @property
    def searchable_text(self) -> str:
        data = self.section.encode("utf-8", "replace") + b"\n" + self.changed_bytes
        return data.decode("utf-8", "replace")

    @property
    def unit_id(self) -> str:
        material = b"\0".join(
            (
                self.path.encode("utf-8", "surrogateescape"),
                self.old_blob_id.encode("ascii", "replace"),
                str(self.old_start).encode("ascii"),
                str(self.old_lines).encode("ascii"),
                self.changed_bytes,
            )
        )
        return sha256(material).hexdigest()[:16]

    @property
    def raw_sha256(self) -> str:
        return sha256(self.patch_data).hexdigest()

    @property
    def added_count(self) -> int:
        return sum(line.num_lines for line in self.lines if line.origin == "+")

    @property
    def deleted_count(self) -> int:
        return sum(line.num_lines for line in self.lines if line.origin == "-")

    def preview(self, limit: int = 180) -> str:
        changed = []
        for line in self.lines:
            if line.origin not in {"+", "-"}:
                continue
            text = line.content.decode("utf-8", "replace").strip()
            if text:
                changed.append(f"{line.origin}{text}")
            if len(changed) == 3:
                break
        result = " / ".join(changed).replace("\t", " ")
        return result if len(result) <= limit else result[: limit - 3] + "..."


@dataclass(frozen=True)
class Evidence:
    category: Category
    strength: MatchStrength
    reason: str
    filter_name: str


@dataclass(frozen=True)
class Candidate:
    category: Category
    strength: MatchStrength
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Resolution:
    owner: Category | None
    candidates: tuple[Candidate, ...]
    mixed: bool

    @property
    def patch_category(self) -> Category:
        if self.owner is not None:
            return self.owner
        return Category.MIXED if self.mixed else Category.UNRESOLVED


def exact_bytes_hash(parts: Iterable[bytes]) -> str:
    digest = sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()
