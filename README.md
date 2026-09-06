# patchsplit

`patchsplit` inventories an already-applied Git patch using pygit2 and assigns
candidate component categories through composable filters. It does not modify
the working tree or index.

The default source is the staged index. Stage the fork patch completely before
running the tool; intent-to-add placeholders do not contain blobs that pygit2
can classify.

## Generating and applying patches

```powershell
git -C ..\7-zip-zstd diff --binary --full-index --no-ext-diff --output=7zzs.patch 2e90379671c9..adb9ceeecd0c -- Asm C CPP
git -C ..\7zip am --abort; git -C ..\7zip reset --hard 26.03; git -C ..\7zip clean -fxd
git -C ..\7zip rm -- CPP/Common/Xxh64Reg.cpp
git -C ..\7zip apply --index --whitespace=nowarn --exclude=CPP/Common/Xxh64Reg.cpp ..\7-zip-zstd\7zzs.patch
```

The explicit `git rm` handles the case-only
`Xxh64Reg.cpp` -> `XXH64Reg.cpp` replacement on case-insensitive filesystems.
The matching deletion is excluded from `git apply` because it is already
staged; the patch still creates `CPP/Common/XXH64Reg.cpp` with its intended
contents.

## Running the tool

```powershell
uv run patchsplit -C ..\7zip
```

The first JSONL record contains run metadata. Each later record represents one
zero-context libgit2 hunk. It includes the resolved owner, every candidate and
the evidence that produced it. Mixed records also contain classifier-derived
`line_slices` that suggest finer boundaries.

`line_slices` are review aids, not directly applicable patches. A later
materializer must group them into syntax-safe feature atoms, construct
cumulative snapshots, and diff adjacent snapshots.

## Exporting an apply-able patch series

Use `--patch-dir` to materialize the classified hunks as contextual Git
patches:

```powershell
uv run patchsplit -C ..\7zip --output series.jsonl --patch-dir patches
```

The directory contains numbered `.patch` files and a `series` file specifying
their application order. Each patch is generated against the cumulative
previous stage, allowing different categories to modify the same file.
On case-insensitive filesystems, a case-only delete/add replacement is emitted
as a small deletion patch immediately before its category patch. This prevents
Git's preflight check from treating the differently-cased destination as an
existing file.

Apply the series from the target repository:

```powershell
git -C ..\7zip am --abort; git -C ..\7zip reset --hard 26.03; git -C ..\7zip clean -fxd
Get-Content ..\patchsplit\patches\series | ForEach-Object {
  $patch = Get-ChildItem (Join-Path ..\patchsplit\patches $_)
  git -C ..\7zip am $patch
  if ($LASTEXITCODE -ne 0) {throw}
}
```

Category declaration order in `categories.py` is the patch-series order;
`PATCH_SERIES_ORDER` is generated directly from the enum. Every generated patch
has a deterministic mail prologue and a numbered subject suitable for `git -C ..\7zip am`.

Mixed and unresolved hunks are preserved whole in correspondingly named
patches rather than being omitted.

## Development

Run the tests from this directory:

```powershell
uv run python -m unittest discover -s tests -v
```

The metadata field `libgit2_patch_id` compares runs made by this tool. Final
patch-series validation should compare reconstructed blob/tree IDs rather than
assuming libgit2 and the Git CLI render identical input for patch-id.

Filter authors should read [FILTERS.md](FILTERS.md). It defines the category
registry, match-strength semantics, ownership rules, review procedure and
testing expectations.

List every canonical category available to filters and manifests:

```powershell
uv run patchsplit --list-categories
```
