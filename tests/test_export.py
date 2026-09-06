from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import pygit2

from patchsplit.categories import PATCH_SERIES_ORDER, Category, MatchStrength
from patchsplit.export import _ordered_labels, write_patch_series
from patchsplit.filters import FilterSet
from patchsplit.filters.base import ChangeFilter, evidence
from patchsplit.inventory import build_inventory


class PurposeFilter(ChangeFilter):
    name = "test-purpose"

    def classify(self, change):
        text = change.searchable_text
        if "alpha" in text:
            yield evidence(
                self,
                Category.UI_HISTORY_SETTINGS,
                MatchStrength.EXACT,
                "alpha test change",
            )
        if "beta" in text:
            yield evidence(
                self,
                Category.UI_LOWERCASE_HASHES,
                MatchStrength.EXACT,
                "beta test change",
            )


class PatchExportTests(unittest.TestCase):
    def test_patch_order_contains_every_category_once(self) -> None:
        self.assertEqual(PATCH_SERIES_ORDER, list(Category))

    def test_labels_follow_category_declaration_order(self) -> None:
        labels = [
            Category.UNRESOLVED,
            Category.VENDOR_ZSTD,
            Category.MIXED,
            Category.CLEANUP_WHITESPACE_ONLY,
            Category.BUILD_BUNDLES,
        ]
        self.assertEqual(
            _ordered_labels(labels),
            [category for category in Category if category in labels],
        )

    def test_exported_series_applies_to_base_and_reconstructs_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = pygit2.init_repository(root, bare=False)
            # Keep the fixture byte-exact regardless of the machine's global
            # Git checkout settings (notably core.autocrlf=true on Windows).
            repo.config["core.autocrlf"] = "false"
            repo.config["user.name"] = "Test Committer"
            repo.config["user.email"] = "committer@example.invalid"
            source = root / "sample.txt"
            source.write_bytes(b"top\nold alpha\nmiddle\nold beta\nbottom\n")
            repo.index.add("sample.txt")
            repo.index.write()
            tree = repo.index.write_tree()
            signature = pygit2.Signature("Test", "test@example.invalid")
            commit = repo.create_commit("HEAD", signature, signature, "base", tree, [])

            target = b"top\nnew alpha\nmiddle\nnew beta\nbottom\n"
            source.write_bytes(target)
            repo.index.add("sample.txt")
            repo.index.write()

            inventory = build_inventory(
                root,
                filters=FilterSet((PurposeFilter(),)),
            )
            output = root / "patches"
            patches = write_patch_series(inventory, output)

            self.assertEqual(len(patches), 2)
            self.assertEqual(
                (output / "series").read_text(encoding="utf-8").splitlines(),
                [patch.name for patch in patches],
            )
            self.assertTrue(
                patches[0]
                .read_text(encoding="utf-8")
                .startswith("From " + "0" * 40 + " Mon Sep 17 00:00:00 2001\n")
            )
            self.assertIn(
                "Subject: [PATCH 01/02] ui.lowercase-hashes\n",
                patches[0].read_text(encoding="utf-8"),
            )

            repo.reset(commit, pygit2.GIT_RESET_HARD)  # type: ignore
            for patch in patches:
                subprocess.run(
                    ["git", "am", str(patch)],
                    cwd=root,
                    check=True,
                    capture_output=True,
                )

            self.assertEqual(source.read_bytes(), target)

    def test_case_only_replacement_is_split_into_delete_then_add(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = pygit2.init_repository(root, bare=False)
            repo.config["core.autocrlf"] = "false"
            repo.config["user.name"] = "Test Committer"
            repo.config["user.email"] = "committer@example.invalid"
            old_path = root / "Xxh64Reg.cpp"
            old_path.write_bytes(b"alpha old implementation\n")
            repo.index.add("Xxh64Reg.cpp")
            repo.index.write()
            tree = repo.index.write_tree()
            signature = pygit2.Signature("Test", "test@example.invalid")
            commit = repo.create_commit("HEAD", signature, signature, "base", tree, [])

            old_path.unlink()
            new_path = root / "XXH64Reg.cpp"
            new_path.write_bytes(b"alpha new implementation\n")
            repo.index.remove("Xxh64Reg.cpp")
            repo.index.add("XXH64Reg.cpp")
            repo.index.write()

            inventory = build_inventory(root, filters=FilterSet((PurposeFilter(),)))
            output = root / "patches"
            patches = write_patch_series(inventory, output)

            self.assertEqual(len(patches), 2)
            self.assertIn("case-delete", patches[0].name)
            self.assertIn(
                "deleted file mode 100644",
                patches[0].read_text(encoding="utf-8"),
            )
            self.assertIn(
                "new file mode 100644",
                patches[1].read_text(encoding="utf-8"),
            )

            repo.reset(commit, pygit2.GIT_RESET_HARD)  # type: ignore
            for patch in patches:
                subprocess.run(
                    ["git", "am", str(patch)],
                    cwd=root,
                    check=True,
                    capture_output=True,
                )

            tracked_paths = set(
                subprocess.run(
                    ["git", "ls-files"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.splitlines()
            )
            self.assertIn("XXH64Reg.cpp", tracked_paths)
            self.assertNotIn("Xxh64Reg.cpp", tracked_paths)
            self.assertEqual(new_path.read_bytes(), b"alpha new implementation\n")


if __name__ == "__main__":
    unittest.main()
