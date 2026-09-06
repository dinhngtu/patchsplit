from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from ..categories import Category, MatchStrength
from ..model import ChangeUnit, Evidence
from .base import ChangeFilter, evidence


@dataclass(frozen=True)
class GeneralRule:
    category: Category
    pattern: re.Pattern[str]
    strength: MatchStrength
    reason: str


class GeneralFeatureFilter(ChangeFilter):
    name = "general-features"

    def __init__(self) -> None:
        specs = (
            (
                Category.WORKFLOW_OPEN_TARGET_FOLDER,
                r"OpnTrgFold|BrowseToPath|FirstExtractedPath",
                MatchStrength.STRONG,
            ),
            (
                Category.WORKFLOW_VOLUME_NAMING,
                r"VolNumberAfterExt|VolPrefix|VolPostfix|DigitCount",
                MatchStrength.STRONG,
            ),
            (
                Category.PARSING_COMMAND_LINE_QUOTING,
                r"GetQuotedString|SplitCommandLine|_SplitCommandLine",
                MatchStrength.STRONG,
            ),
            (
                Category.PLATFORM_TIME_CONVERSION,
                r"FileTimeToLocalFileTime2|LocalFileTimeToFileTime2",
                MatchStrength.STRONG,
            ),
            (
                Category.ARCHIVE_METHOD_PRESERVATION,
                r"ObtainMethodFromBlocks|ObtainBlockMethods",
                MatchStrength.STRONG,
            ),
            (
                Category.CODEC_THREAD_PROPERTIES,
                r"ParseMtProp|kNumThreads|numThreads",
                MatchStrength.WEAK,
            ),
            (
                Category.CORE_METHOD_PROPERTIES,
                r"SetCommonProperty|g_NameToPropID|NCoderPropID",
                MatchStrength.WEAK,
            ),
        )
        self.rules = tuple(
            GeneralRule(category, re.compile(pattern), strength, f"matches {pattern}")
            for category, pattern, strength in specs
        )

    def classify(self, change: ChangeUnit) -> Iterable[Evidence]:
        text = change.searchable_text
        for rule in self.rules:
            if change.path.startswith("CPP/7zip/UI/") and rule.category in {
                Category.WORKFLOW_OPEN_TARGET_FOLDER,
                Category.WORKFLOW_VOLUME_NAMING,
                Category.PARSING_COMMAND_LINE_QUOTING,
            }:
                continue
            if rule.pattern.search(text):
                yield evidence(self, rule.category, rule.strength, rule.reason)


class WhitespaceOnlyFilter(ChangeFilter):
    name = "whitespace-only"

    @staticmethod
    def _normalized(data: bytes) -> bytes:
        return re.sub(rb"\s+", b"", data)

    def classify(self, change: ChangeUnit) -> Iterable[Evidence]:
        if (
            change.added_bytes
            and change.deleted_bytes
            and self._normalized(change.added_bytes) == self._normalized(change.deleted_bytes)
        ):
            yield evidence(
                self,
                Category.CLEANUP_WHITESPACE_ONLY,
                MatchStrength.EXACT,
                "only whitespace changed",
            )
