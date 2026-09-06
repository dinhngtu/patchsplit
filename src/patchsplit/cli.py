from __future__ import annotations

import argparse

from .categories import Category
from .export import write_patch_series
from .filters import FilterSet, builtin_filters, load_filter_module
from .inventory import build_inventory
from .output import write_inventory


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="patchsplit",
        description="Inventory a patch file with composable purpose filters.",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="print canonical category values and exit",
    )
    parser.add_argument("-C", "--repository", default=".", help="repository worktree")
    parser.add_argument("--base", default="HEAD", help="base revision (default: HEAD)")
    parser.add_argument("--output", help="JSONL output; stdout when omitted")
    parser.add_argument(
        "--patch-dir",
        help="write an ordered, apply-able patch series to this directory",
    )
    parser.add_argument(
        "--patch",
        "--patch-file",
        dest="patch_file",
        metavar="PATCH_FILE",
        help="apply this patch to a temporary index initialized from --base",
    )
    parser.add_argument(
        "--path-prefix",
        action="append",
        default=[],
        help="only emit units below this path prefix; repeatable",
    )
    parser.add_argument(
        "--filter-module",
        action="append",
        default=[],
        help="additional Python module exposing get_filters() or FILTERS",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.list_categories:
        for category in Category:
            print(category.value)
        return 0
    if args.patch_file is None:
        parser.error("--patch is required")

    filters = list(builtin_filters())
    for module_name in args.filter_module:
        filters.extend(load_filter_module(module_name))

    inventory = build_inventory(
        args.repository,
        base=args.base,
        filters=FilterSet(tuple(filters)),
        path_prefixes=tuple(args.path_prefix),
        patch_file=args.patch_file,
    )
    exported = ()
    if args.output is not None:
        write_inventory(inventory, args.output)
    if args.patch_dir is not None:
        exported = write_patch_series(inventory, args.patch_dir)

    destination = args.output or ("not written" if args.patch_dir else "stdout")
    print(
        f"paths={inventory.path_count}/{inventory.source_path_count} "
        f"units={len(inventory.items)} "
        f"mixed={inventory.mixed_count} unresolved={inventory.unresolved_count} "
        f"patches={len(exported)} patch_dir={args.patch_dir or '-'} "
        f"output={destination}",
        file=__import__("sys").stderr,
    )
    for owner, count in inventory.owner_counts().most_common():
        print(f"{count:5}  {owner}", file=__import__("sys").stderr)
    return 0
