from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from ..categories import Category, MatchStrength
from ..model import ChangeUnit, Evidence
from .base import ChangeFilter, evidence


@dataclass(frozen=True)
class PathRule:
    pattern: re.Pattern[str]
    category: Category
    strength: MatchStrength = MatchStrength.FALLBACK


class PathOwnershipFilter(ChangeFilter):
    name = "path-ownership"

    def __init__(self) -> None:
        specifications = (
            (r"^C/zstd/", Category.VENDOR_ZSTD, MatchStrength.EXACT),
            (r"^C/brotli/", Category.VENDOR_BROTLI, MatchStrength.EXACT),
            (r"^C/(?:lizard|lz4|lz5)/", Category.VENDOR_LZ_FAMILY, MatchStrength.EXACT),
            (r"^C/fast-lzma2/", Category.VENDOR_FAST_LZMA2, MatchStrength.EXACT),
            (r"^C/zstdmt/", Category.CODEC_MT_SUPPORT, MatchStrength.EXACT),
            (r"^C/hashes/", Category.HASH_BACKENDS, MatchStrength.EXACT),
            (r"^CPP/7zip/Compress/", Category.CODEC_ADAPTERS, MatchStrength.FALLBACK),
            (r"^CPP/7zip/Archive/", Category.ARCHIVE_FORMATS, MatchStrength.FALLBACK),
            (r"^CPP/7zip/UI/", Category.UI_MISC, MatchStrength.FALLBACK),
            (r"^CPP/7zip/Bundles/", Category.BUILD_BUNDLES, MatchStrength.EXACT),
            (r"^CPP/(?:Common|Windows)/", Category.COMMON_PLATFORM, MatchStrength.FALLBACK),
        )
        self.rules = tuple(
            PathRule(re.compile(pattern), category, strength)
            for pattern, category, strength in specifications
        )

    def classify(self, change: ChangeUnit) -> Iterable[Evidence]:
        for rule in self.rules:
            if rule.pattern.search(change.path):
                yield evidence(
                    self,
                    rule.category,
                    rule.strength,
                    f"path matches {rule.pattern.pattern}",
                )
                return


class BuildFileFilter(ChangeFilter):
    name = "build-files"
    _path = re.compile(
        r"(?:^|/)(?:makefile(?:\..*)?|[^/]+\.(?:mak|dsp)|build-(?:it\.cmd|lx\.sh))$",
        re.IGNORECASE,
    )

    def classify(self, change: ChangeUnit) -> Iterable[Evidence]:
        if self._path.search(change.path):
            yield evidence(
                self,
                Category.BUILD_INTEGRATION,
                MatchStrength.STRONG,
                "build-description path",
            )
