from __future__ import annotations

from enum import IntEnum, StrEnum


class Category(StrEnum):
    """Canonical component names emitted by filters and manifests.

    Add a member here before using a new category in a filter. Values are
    stable external identifiers; renaming a member is harmless, changing its
    value is a manifest migration.
    """

    VENDOR_ZSTD = "vendor.zstd"
    VENDOR_BROTLI = "vendor.brotli"
    VENDOR_LZ_FAMILY = "vendor.lz-family"
    VENDOR_FAST_LZMA2 = "vendor.fast-lzma2"

    CODEC_MT_SUPPORT = "codec.mt-support"
    CODEC_ADAPTERS = "codec.adapters"
    CODEC_THREAD_PROPERTIES = "codec.thread-properties"
    HASH_BACKENDS = "hash.backends"
    ARCHIVE_FORMATS = "archive.formats"
    ARCHIVE_METHOD_PRESERVATION = "archive.method-preservation"
    CORE_METHOD_PROPERTIES = "core.method-properties"
    COMMON_PLATFORM = "common.platform"
    PLATFORM_TIME_CONVERSION = "platform.time-conversion"
    BUILD_BUNDLES = "build.bundles"
    BUILD_INTEGRATION = "build.integration"

    UI_MISC = "ui.misc"
    UI_DARK_MODE = "ui.dark-mode"
    UI_HISTORY_SETTINGS = "ui.history-settings"
    UI_LOWERCASE_HASHES = "ui.lowercase-hashes"
    UI_EXTRA_HASHES = "ui.extra-hashes"
    UI_COMPRESSION_LEVELS = "ui.compression-levels"
    UI_EXTRA_CODECS = "ui.extra-codecs"
    UI_METHOD_PERSISTENCE = "ui.method-persistence"
    UI_ZS_BRANDING = "ui.zs-branding"
    UI_OPEN_TARGET_FOLDER = "ui.open-target-folder"
    UI_VOLUME_NAMING = "ui.volume-naming"
    UI_COMMAND_LINE_QUOTING = "ui.command-line-quoting"
    UI_KEYBOARD_NAVIGATION = "ui.keyboard-navigation"
    UI_SAFETY_CLEANUPS = "ui.safety-cleanups"
    UI_CONSOLE_VERSION_HELP = "ui.console-version-help"
    UI_CONSOLE_VERSION_COMMAND = "ui.console-version-command"
    UI_CONSOLE_VERSION_REFACTOR = "ui.console-version-refactor"

    WORKFLOW_OPEN_TARGET_FOLDER = "workflow.open-target-folder"
    WORKFLOW_VOLUME_NAMING = "workflow.volume-naming"
    PARSING_COMMAND_LINE_QUOTING = "parsing.command-line-quoting"
    CLEANUP_WHITESPACE_ONLY = "cleanup.whitespace-only"


class MatchStrength(IntEnum):
    """How independently persuasive one filter match is.

    This is intentionally ordinal, not a probability or tunable score.
    """

    FALLBACK = 10
    WEAK = 20
    STRONG = 30
    EXACT = 40
