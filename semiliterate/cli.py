"""Command line interface for semiliterate."""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from semiliterate.materialize import build_docs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="semiliterate")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--source", default=".")
    build_parser.add_argument("--out", default=".build-docs")
    build_parser.add_argument("--config")
    build_parser.add_argument(
        "--include-mode",
        choices=["copy", "symlink", "skip"],
        default="copy",
    )
    build_parser.add_argument("--dry-run", action="store_true")
    build_parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: Optional[list] = None) -> int:
    """Run the semiliterate CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "build":
        parser.print_help()
        return 1

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
    )

    paths = build_docs(
        source=args.source,
        out=args.out,
        config_path=args.config,
        include_mode=args.include_mode,
        dry_run=args.dry_run,
    )

    if args.verbose:
        for path in paths:
            logging.info("%s -> %s/%s", path.input_path, path.output_root, path.output_relpath)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
