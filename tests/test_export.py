from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import pygit2

from patchsplit.categories import Category, MatchStrength
from patchsplit.export import write_patch_series
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
    def test_exported_series_applies_to_base_and_reconstructs_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = pygit2.init_repository(root, bare=False)
            # Keep the fixture byte-exact regardless of the machine's global
            # Git checkout settings (notably core.autocrlf=true on Windows).
            repo.config["core.autocrlf"] = "false"
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

            repo.reset(commit, pygit2.GIT_RESET_HARD)  # type: ignore
            for patch in patches:
                subprocess.run(
                    ["git", "apply", "--check", str(patch)],
                    cwd=root,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "apply", str(patch)],
                    cwd=root,
                    check=True,
                    capture_output=True,
                )

            self.assertEqual(source.read_bytes(), target)


if __name__ == "__main__":
    unittest.main()
