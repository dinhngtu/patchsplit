from __future__ import annotations

from enum import IntEnum, StrEnum


class Category(StrEnum):
    """Canonical component names emitted by filters and manifests.

    Add a member here before using a new category in a filter. Values are
    stable external identifiers; renaming a member is harmless, changing its
    value is a manifest migration.
    """

    # Imported implementations and low-level backends.
    VENDOR_BROTLI = "vendor.brotli"
    VENDOR_FAST_LZMA2 = "vendor.fast-lzma2"
    VENDOR_LZ_FAMILY = "vendor.lz-family"
    VENDOR_ZSTD = "vendor.zstd"
    HASH_BACKENDS = "hash.backends"

    # Codec plumbing, core properties, and archive integration.
    CODEC_UPSTREAM_ZSTD_DECODER = "codec.upstream-zstd-decoder"
    CODEC_MT_SUPPORT = "codec.mt-support"
    CODEC_THREAD_PROPERTIES = "codec.thread-properties"
    CODEC_ADAPTERS = "codec.adapters"
    CORE_METHOD_PROPERTIES = "core.method-properties"
    ARCHIVE_METHOD_PRESERVATION = "archive.method-preservation"
    ARCHIVE_FORMATS = "archive.formats"

    # Shared platform behavior and command parsing.
    COMMON_PLATFORM = "common.platform"
    PLATFORM_TIME_CONVERSION = "platform.time-conversion"
    PARSING_COMMAND_LINE_QUOTING = "parsing.command-line-quoting"

    # Build descriptions consume the implementation categories above.
    BUILD_INTEGRATION = "build.integration"
    BUILD_BUNDLES = "build.bundles"

    # Product identity and workflows precede their UI integrations.
    ZS_BRANDING = "branding.zs"
    WORKFLOW_OPEN_TARGET_FOLDER = "workflow.open-target-folder"
    WORKFLOW_VOLUME_NAMING = "workflow.volume-naming"

    # User-interface changes, from shared settings to individual features.
    UI_MISC = "ui.misc"
    UI_SETTINGS = "ui.settings"
    UI_LOWERCASE_HASHES = "ui.lowercase-hashes"
    UI_HISTORY_SETTINGS = "ui.history-settings"
    UI_OPEN_TARGET_FOLDER = "ui.open-target-folder"
    UI_VOLUME_NAMING = "ui.volume-naming"
    UI_METHOD_PERSISTENCE = "ui.method-persistence"
    UI_COMPRESSION_LEVELS = "ui.compression-levels"
    UI_EXTRA_CODECS = "ui.extra-codecs"
    UI_EXTRA_HASHES = "ui.extra-hashes"
    UI_COMMAND_LINE_QUOTING = "ui.command-line-quoting"
    UI_CONSOLE_VERSION_REFACTOR = "ui.console-version-refactor"
    UI_CONSOLE_VERSION_HELP = "ui.console-version-help"
    UI_CONSOLE_VERSION_COMMAND = "ui.console-version-command"
    UI_DARK_MODE = "ui.dark-mode"
    UI_KEYBOARD_NAVIGATION = "ui.keyboard-navigation"
    UI_SAFETY_CLEANUPS = "ui.safety-cleanups"

    # Review-only categories are intentionally last.
    MIXED = "mixed"
    UNRESOLVED = "unresolved"
    CLEANUP_WHITESPACE_ONLY = "cleanup.whitespace-only"


# StrEnum preserves declaration order, which is the canonical patch-series order.
PATCH_SERIES_ORDER: list[Category] = list(Category)


class MatchStrength(IntEnum):
    """How independently persuasive one filter match is.

    This is intentionally ordinal, not a probability or tunable score.
    """

    FALLBACK = 10
    WEAK = 20
    STRONG = 30
    EXACT = 40
