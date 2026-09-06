from __future__ import annotations

import unittest

from patchsplit.categories import Category, MatchStrength
from patchsplit.model import Evidence
from patchsplit.resolve import resolve


def match(category: Category, strength: MatchStrength) -> Evidence:
    return Evidence(category, strength, "test", "test-filter")


class ResolverTests(unittest.TestCase):
    def test_single_strong_match_owns_over_fallback(self) -> None:
        result = resolve(
            (
                match(Category.UI_MISC, MatchStrength.FALLBACK),
                match(Category.UI_DARK_MODE, MatchStrength.STRONG),
            )
        )
        self.assertEqual(result.owner, Category.UI_DARK_MODE)
        self.assertFalse(result.mixed)

    def test_two_strong_categories_are_mixed(self) -> None:
        result = resolve(
            (
                match(Category.UI_EXTRA_CODECS, MatchStrength.STRONG),
                match(Category.UI_COMPRESSION_LEVELS, MatchStrength.STRONG),
            )
        )
        self.assertIsNone(result.owner)
        self.assertTrue(result.mixed)

    def test_exact_match_owns_over_strong_match(self) -> None:
        result = resolve(
            (
                match(Category.VENDOR_ZSTD, MatchStrength.EXACT),
                match(Category.BUILD_INTEGRATION, MatchStrength.STRONG),
            )
        )
        self.assertEqual(result.owner, Category.VENDOR_ZSTD)
        self.assertFalse(result.mixed)

    def test_weak_evidence_never_owns(self) -> None:
        result = resolve(
            (
                match(Category.COMMON_PLATFORM, MatchStrength.FALLBACK),
                match(Category.CODEC_THREAD_PROPERTIES, MatchStrength.WEAK),
            )
        )
        self.assertIsNone(result.owner)
        self.assertFalse(result.mixed)

    def test_lone_fallback_owns(self) -> None:
        result = resolve((match(Category.UI_MISC, MatchStrength.FALLBACK),))
        self.assertEqual(result.owner, Category.UI_MISC)
        self.assertFalse(result.mixed)


if __name__ == "__main__":
    unittest.main()
