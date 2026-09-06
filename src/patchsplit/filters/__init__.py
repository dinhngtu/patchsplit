from __future__ import annotations

from .base import ChangeFilter, FilterSet, load_filter_module
from .branding import ZsBrandingFilter
from .general import CoderPropertyFilter, GeneralFeatureFilter, WhitespaceOnlyFilter
from .paths import BuildFileFilter, PathOwnershipFilter
from .ui import ConsoleMainFilter, UiPurposeFilter


def builtin_filters() -> tuple[ChangeFilter, ...]:
    return (
        PathOwnershipFilter(),
        BuildFileFilter(),
        GeneralFeatureFilter(),
        CoderPropertyFilter(),
        ZsBrandingFilter(),
        WhitespaceOnlyFilter(),
        UiPurposeFilter(),
        ConsoleMainFilter(),
    )


__all__ = [
    "ChangeFilter",
    "FilterSet",
    "builtin_filters",
    "load_filter_module",
]
