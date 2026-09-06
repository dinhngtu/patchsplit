from __future__ import annotations

import unittest

from patchsplit.atomize import suggest_line_slices
from patchsplit.categories import Category, MatchStrength
from patchsplit.filters import FilterSet, builtin_filters
from patchsplit.filters.base import ChangeFilter
from patchsplit.model import ChangeLine, ChangeUnit, Evidence
from patchsplit.resolve import resolve


def change(path: str, added: str, section: str = "") -> ChangeUnit:
    raw = added.encode()
    return ChangeUnit(
        path=path,
        status="M",
        old_blob_id="1" * 40,
        new_blob_id="2" * 40,
        old_start=1,
        old_lines=0,
        new_start=1,
        new_lines=1,
        header="@@ -1,0 +1 @@",
        section=section,
        lines=(ChangeLine("+", raw, -1, 1),),
        patch_data=raw,
    )


class UiFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.filters = FilterSet(builtin_filters())

    def classify(self, item: ChangeUnit):
        return resolve(self.filters.classify(item))

    def test_combined_history_and_hash_settings_get_their_own_owner(self) -> None:
        result = self.classify(
            change(
                "CPP/7zip/UI/FileManager/RegistryUtils.cpp",
                "WantArcHistory(); WantLowercaseHashes();",
            )
        )
        categories = {candidate.category for candidate in result.candidates}
        self.assertIn(Category.UI_HISTORY_SETTINGS, categories)
        self.assertIn(Category.UI_LOWERCASE_HASHES, categories)
        self.assertIn(Category.UI_SETTINGS, categories)
        self.assertFalse(result.mixed)
        self.assertEqual(result.owner, Category.UI_SETTINGS)

    def test_upstream_zstd_decoder_path_has_exact_ownership(self) -> None:
        result = self.classify(change("C/ZstdDec.c", "removed decoder"))
        self.assertEqual(result.owner, Category.CODEC_UPSTREAM_ZSTD_DECODER)
        self.assertEqual(result.candidates[0].strength, MatchStrength.EXACT)

    def test_similarly_named_zstd_adapter_is_not_upstream_decoder(self) -> None:
        result = self.classify(change("CPP/7zip/Compress/ZstdDecoder.cpp", "adapter change"))
        self.assertEqual(result.owner, Category.CODEC_ADAPTERS)
        self.assertNotIn(
            Category.CODEC_UPSTREAM_ZSTD_DECODER,
            {candidate.category for candidate in result.candidates},
        )

    def test_version_metadata_path_is_zs_branding(self) -> None:
        result = self.classify(change("C/7zVersion.h", '#define MY_DATE "2026-09-05"'))
        self.assertEqual(result.owner, Category.ZS_BRANDING)
        self.assertEqual(result.candidates[0].strength, MatchStrength.EXACT)

    def test_installer_product_name_is_zs_branding(self) -> None:
        result = self.classify(
            change(
                "C/Util/7zipInstall/resource.rc",
                'MY_VERSION_INFO(MY_VFT_APP, "7-Zip Installer ZS")',
            )
        )
        self.assertEqual(result.owner, Category.ZS_BRANDING)

    def test_plain_upstream_product_name_is_not_zs_branding(self) -> None:
        result = self.classify(change("C/example.c", 'const char *name = "7-Zip";'))
        self.assertNotIn(
            Category.ZS_BRANDING,
            {candidate.category for candidate in result.candidates},
        )

    def test_bundle_makefile_path_overrides_build_file_hint(self) -> None:
        result = self.classify(change("CPP/7zip/Bundles/SFXWin/makefile", r"$O\MyWindows.obj"))
        self.assertEqual(result.owner, Category.BUILD_BUNDLES)
        self.assertEqual(result.candidates[0].strength, MatchStrength.EXACT)

    def test_level_mask_owns_hunk_that_also_names_an_extra_codec(self) -> None:
        result = self.classify(
            change(
                "CPP/7zip/UI/GUI/CompressDialog.cpp",
                "if (id == kZSTD) LevelsMask = g_Levels[id];",
            )
        )
        categories = {candidate.category for candidate in result.candidates}
        self.assertIn(Category.UI_EXTRA_CODECS, categories)
        self.assertIn(Category.UI_COMPRESSION_LEVELS, categories)
        self.assertFalse(result.mixed)
        self.assertEqual(result.owner, Category.UI_COMPRESSION_LEVELS)

    def test_lizard_adapter_with_thread_api_is_mt_support(self) -> None:
        result = self.classify(
            change(
                "CPP/7zip/Compress/LizardDecoder.cpp",
                "case NCoderPropID::kNumThreads: SetNumberOfThreads(v);",
            )
        )
        self.assertEqual(result.owner, Category.CODEC_MT_SUPPORT)

    def test_generic_thread_variable_remains_weak(self) -> None:
        result = self.classify(change("CPP/example.cpp", "UInt32 numThreads;"))
        self.assertIsNone(result.owner)
        self.assertFalse(result.mixed)
        self.assertEqual(result.candidates[0].strength, MatchStrength.WEAK)

    def test_icoder_property_table_has_exact_core_property_ownership(self) -> None:
        result = self.classify(
            change(
                "CPP/7zip/ICoder.h",
                "kLdmSearchLength, // Zstd long-distance matching property",
                "namespace NCoderPropID",
            )
        )
        self.assertEqual(result.owner, Category.CORE_METHOD_PROPERTIES)
        self.assertEqual(result.candidates[0].strength, MatchStrength.EXACT)

    def test_console_hunks_have_distinct_owners(self) -> None:
        result = self.classify(
            change(
                "CPP/7zip/UI/Console/Main.cpp",
                'if (command == "--version") return 0;',
                "int Main2()",
            )
        )
        self.assertEqual(result.owner, Category.UI_CONSOLE_VERSION_COMMAND)

    def test_line_slices_separate_mixed_settings(self) -> None:
        item = ChangeUnit(
            path="CPP/7zip/UI/FileManager/RegistryUtils.cpp",
            status="M",
            old_blob_id="1" * 40,
            new_blob_id="2" * 40,
            old_start=1,
            old_lines=0,
            new_start=1,
            new_lines=2,
            header="@@ -1,0 +1,2 @@",
            section="",
            lines=(
                ChangeLine("+", b"bool WantArcHistory();\n", -1, 1),
                ChangeLine("+", b"bool WantLowercaseHashes();\n", -1, 2),
            ),
            patch_data=b"",
        )
        slices = suggest_line_slices(item, self.filters)
        self.assertEqual(len(slices), 2)
        self.assertEqual(slices[0].categories, (Category.UI_HISTORY_SETTINGS,))
        self.assertEqual(slices[1].categories, (Category.UI_LOWERCASE_HASHES,))

    def test_filter_set_rejects_ad_hoc_category_strings(self) -> None:
        class InvalidFilter(ChangeFilter):
            name = "invalid"

            def classify(self, change):
                yield Evidence("ui.typo", MatchStrength.STRONG, "test", self.name)  # type:ignore

        with self.assertRaisesRegex(TypeError, "unregistered category"):
            FilterSet((InvalidFilter(),)).classify(change("x.cpp", "x"))


if __name__ == "__main__":
    unittest.main()
