from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .categories import Category, MatchStrength
from .model import Candidate, Evidence, Resolution


def resolve(
    all_evidence: Iterable[Evidence],
) -> Resolution:
    grouped: dict[Category, list[Evidence]] = defaultdict(list)
    for item in all_evidence:
        grouped[item.category].append(item)

    candidates = tuple(
        sorted(
            (
                Candidate(category, max(item.strength for item in items), tuple(items))
                for category, items in grouped.items()
            ),
            key=lambda item: (-item.strength, item.category.value),
        )
    )
    exact = tuple(item for item in candidates if item.strength == MatchStrength.EXACT)
    strong = tuple(item for item in candidates if item.strength == MatchStrength.STRONG)
    mixed = len(exact) > 1 or (not exact and len(strong) > 1)

    owner: Category | None = None
    if len(exact) == 1:
        owner = exact[0].category
    elif not exact and len(strong) == 1:
        owner = strong[0].category
    elif not exact and not strong:
        weak = tuple(item for item in candidates if item.strength == MatchStrength.WEAK)
        fallbacks = tuple(item for item in candidates if item.strength == MatchStrength.FALLBACK)
        if not weak and len(fallbacks) == 1:
            owner = fallbacks[0].category

    return Resolution(owner, candidates, mixed)
