from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import pygit2

from patchsplit.diff_source import PatchApplyError
from patchsplit.inventory import build_inventory


class PatchInputTests(unittest.TestCase):
    def test_patch_is_applied_to_temporary_index_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = pygit2.init_repository(root, bare=False)
            repo.config["core.autocrlf"] = "false"
            repo.config["user.name"] = "Test Committer"
            repo.config["user.email"] = "committer@example.invalid"
            source = root / "sample.txt"
            source.write_bytes(b"before\n")
            repo.index.add("sample.txt")
            repo.index.write()
            tree = repo.index.write_tree()
            signature = pygit2.Signature("Test", "test@example.invalid")
            commit = repo.create_commit("HEAD", signature, signature, "base", tree, [])

            source.write_bytes(b"after\n")
            patch = root / "change.patch"
            patch.write_bytes(
                subprocess.run(
                    ["git", "diff", "--binary", "--full-index"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                ).stdout
            )
            repo.reset(commit, pygit2.GIT_RESET_HARD)  # type: ignore

            # Deliberately make the real index differ from both the base and
            # the patch target. Patchsplit must neither read nor replace it.
            source.write_bytes(b"real index only\n")
            repo.index.add("sample.txt")
            repo.index.write()
            source.write_bytes(b"before\n")
            real_index_tree = repo.index.write_tree()

            inventory = build_inventory(root, patch_file=patch)

            self.assertEqual(inventory.source_path_count, 1)
            self.assertEqual(inventory.items[0].change.path, "sample.txt")
            self.assertEqual(inventory.items[0].change.added_bytes, b"after\n")
            new_blob = repo[pygit2.Oid(hex=inventory.items[0].change.new_blob_id)]
            self.assertEqual(new_blob.data, b"after\n")
            self.assertEqual(source.read_bytes(), b"before\n")
            self.assertEqual(repo.index.write_tree(), real_index_tree)

    def test_failed_patch_does_not_change_real_index_or_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = pygit2.init_repository(root, bare=False)
            repo.config["core.autocrlf"] = "false"
            source = root / "sample.txt"
            source.write_bytes(b"before\n")
            repo.index.add("sample.txt")
            repo.index.write()
            tree = repo.index.write_tree()
            signature = pygit2.Signature("Test", "test@example.invalid")
            repo.create_commit("HEAD", signature, signature, "base", tree, [])
            real_index_tree = repo.index.write_tree()
            patch = root / "bad.patch"
            patch.write_text("not a patch\n", encoding="utf-8")

            with self.assertRaises(PatchApplyError):
                build_inventory(root, patch_file=patch)

            self.assertEqual(source.read_bytes(), b"before\n")
            self.assertEqual(repo.index.write_tree(), real_index_tree)


if __name__ == "__main__":
    unittest.main()
