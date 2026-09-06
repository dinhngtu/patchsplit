from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from ..categories import Category, MatchStrength
from ..model import ChangeUnit, Evidence
from .base import ChangeFilter, evidence

_HISTORY_PATTERN = (
    r"Want(?:Arc|Path|Copy|Folder)History|"
    r"(?:Arc|Path|Copy|Folder)History|"
    r"SETTINGS_WANT_(?:ARC|PATH|COPY|FOLDER)_HISTORY"
)
_LOWERCASE_HASH_PATTERN = r"WantLowercaseHashes|LowercaseHashes|LOWERCASE_HASH|lowercase\s+hash"


def _compile_patterns(spec: str | tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    patterns = (spec,) if isinstance(spec, str) else spec
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


@dataclass(frozen=True)
class UiRule:
    category: Category
    patterns: tuple[re.Pattern[str], ...]
    strength: MatchStrength
    reason: str

    def matches(self, text: str) -> bool:
        return all(pattern.search(text) for pattern in self.patterns)


class UiPurposeFilter(ChangeFilter):
    """Purpose-oriented UI classifier.

    Rules deliberately all run. A hunk can therefore be marked as mixed
    instead of being captured by the first matching codec or UI keyword.
    """

    name = "ui-purpose"
    _ui_path = re.compile(r"^CPP/7zip/UI/")

    def __init__(self) -> None:
        specs = (
            (
                Category.UI_COMPRESSION_LEVELS,
                r"Levels(?:Mask|Start|End)(?:ByMask)?",
                MatchStrength.EXACT,
                "compression-level range or mask state",
            ),
            (
                Category.UI_SETTINGS,
                (_HISTORY_PATTERN, _LOWERCASE_HASH_PATTERN),
                MatchStrength.EXACT,
                "multiple file-manager settings changed together",
            ),
            (
                Category.UI_DARK_MODE,
                r"ZIP7_DARKMODE|dmlib::|Darkmodelib|ColorMode|_clrMode",
                MatchStrength.STRONG,
                "dark-mode API, guard, or setting",
            ),
            (
                Category.UI_HISTORY_SETTINGS,
                _HISTORY_PATTERN,
                MatchStrength.STRONG,
                "history preference identifier",
            ),
            (
                Category.UI_LOWERCASE_HASHES,
                _LOWERCASE_HASH_PATTERN,
                MatchStrength.STRONG,
                "hash case preference",
            ),
            (
                Category.UI_EXTRA_HASHES,
                r"BLAKE3|BLAKE2s?p|XXH(?:3|32|64)|\bMD[24]\b|SHA3[_-](?:384|512)|kHash_(?:XXH32|MD2|MD4|BLAKE3)",
                MatchStrength.STRONG,
                "additional hash algorithm or UI command",
            ),
            (
                Category.UI_COMPRESSION_LEVELS,
                r"g_Levels|g_LevelRanges|Levels(?:Mask|Start|End)|SetLevel2|GetLevel2|IDS_METHOD_(?:FASTEST|FAST|NORMAL|MAXIMUM|ULTRA|ADV_MAX|HIGHEST|ULTIMATEFAST|ULTRAFAST|SUPERFAST)|Z7_ZSTD_(?:FAST|ULTIMATE)|Compression level",
                MatchStrength.STRONG,
                "compression-level selection machinery",
            ),
            (
                Category.UI_EXTRA_CODECS,
                r"k(?:FLZMA2|ZSTD|BROTLI|LZ4|LZ5|LIZARD(?:_M[1-4])?)\b|\bFastLzma2\b|\bBrotli\b|\bLizard\b|\bLZ[45]\b|\bzstd\b",
                MatchStrength.STRONG,
                "additional codec exposed by the UI",
            ),
            (
                Category.UI_METHOD_PERSISTENCE,
                r"LoadAndUpdateFormatByMethod|ComprMethodChanged|FindRegistryFormat|fo\.Method|GetMethodSpec",
                MatchStrength.STRONG,
                "per-method option persistence",
            ),
            (
                Category.UI_OPEN_TARGET_FOLDER,
                r"OpnTrgFold|Open target folder|BrowseToPath|FirstExtractedPath",
                MatchStrength.STRONG,
                "open-target-folder workflow",
            ),
            (
                Category.UI_VOLUME_NAMING,
                r"VolNumberAfterExt|VolPrefix|VolPostfix|DigitCount",
                MatchStrength.STRONG,
                "volume naming option",
            ),
            (
                Category.UI_COMMAND_LINE_QUOTING,
                r"GetQuotedString|SplitCommandLine|_SplitCommandLine|AddFrom\(",
                MatchStrength.STRONG,
                "command-line parsing or quoting",
            ),
            (
                Category.UI_KEYBOARD_NAVIGATION,
                r"OnKeyDown|VK_(?:LEFT|RIGHT|UP|DOWN|RETURN|BACK)|NM_KEYDOWN",
                MatchStrength.STRONG,
                "keyboard handling",
            ),
            (
                Category.UI_SAFETY_CLEANUPS,
                r"\bsnprintf\s*\(|NOSONAR",
                MatchStrength.STRONG,
                "bounded formatting cleanup",
            ),
        )
        self.rules = tuple(
            UiRule(
                category,
                _compile_patterns(pattern_spec),
                strength,
                reason,
            )
            for category, pattern_spec, strength, reason in specs
        )

    def classify(self, change: ChangeUnit) -> Iterable[Evidence]:
        if not self._ui_path.search(change.path):
            return
        text = change.searchable_text
        for rule in self.rules:
            if rule.matches(text):
                yield evidence(self, rule.category, rule.strength, rule.reason)


class ConsoleMainFilter(ChangeFilter):
    name = "console-main"
    _path = "CPP/7zip/UI/Console/Main.cpp"

    def classify(self, change: ChangeUnit) -> Iterable[Evidence]:
        if change.path != self._path:
            return
        text = change.searchable_text
        if "kHelpString" in change.section or "Show version information" in text:
            yield evidence(
                self,
                Category.UI_CONSOLE_VERSION_HELP,
                MatchStrength.EXACT,
                "version help entry",
            )
        elif "Main2" in change.section and "--version" in text:
            yield evidence(
                self,
                Category.UI_CONSOLE_VERSION_COMMAND,
                MatchStrength.EXACT,
                "version command branch",
            )
        elif "kVersionString" in text or "kCopyrightString" in text:
            yield evidence(
                self,
                Category.UI_CONSOLE_VERSION_REFACTOR,
                MatchStrength.EXACT,
                "version string construction",
            )
