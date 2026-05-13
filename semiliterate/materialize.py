"""Materialization helpers for semiliterate builds."""

from __future__ import annotations

"""md
# Materialization

`build_docs` is the top-level orchestration function for the standalone
package. It loads config, scans the source tree, and materializes included
files into the output directory.

## Responsibilities

- combine explicit config with defaults
- exclude the output directory from future scans
- copy, symlink, or skip included files based on `include_mode`
"""

import os
from pathlib import Path
import shutil
from typing import Dict, List, Optional

from semiliterate.config import load_config, normalize_config
from semiliterate.scanner import BuildPath, SimpleScanner


def _materialize_include(
    source_path: str,
    destination_path: str,
    include_mode: str,
    dry_run: bool = False,
) -> None:
    destination_parent = os.path.dirname(destination_path)
    if not dry_run:
        os.makedirs(destination_parent, exist_ok=True)

    if include_mode == "skip":
        return
    if include_mode == "symlink":
        if dry_run:
            return
        if os.path.lexists(destination_path):
            os.remove(destination_path)
        os.symlink(os.path.abspath(source_path), destination_path)
        return
    if include_mode == "copy":
        if dry_run:
            return
        shutil.copy2(source_path, destination_path)
        return
    raise ValueError("Unsupported include mode: {0}".format(include_mode))


def build_docs(
    source: str = ".",
    out: str = ".build-docs",
    config: Optional[Dict] = None,
    config_path: Optional[str] = None,
    include_mode: str = "copy",
    dirty: bool = False,
    last_build_time: float = None,
    dry_run: bool = False,
) -> List[BuildPath]:
    """Scan, extract, and materialize a documentation tree."""
    loaded_config = load_config(config_path)
    if config:
        loaded_config.update(config)
    loaded_config = normalize_config(loaded_config)

    source_root = Path(source).resolve()
    output_root = Path(out).resolve()
    ignore_paths = list(loaded_config.get("ignore_paths", []))
    ignore_paths.append(str(output_root))

    scanner = SimpleScanner(
        build_dir=out,
        root_path=source,
        folders=loaded_config.get("folders", ["*"]),
        include=loaded_config.get("include", []),
        ignore=loaded_config.get("ignore", []),
        ignore_hidden=loaded_config.get("ignore_hidden", True),
        ignore_paths=ignore_paths,
        semiliterate=loaded_config.get("semiliterate", []),
    )

    do_copy = bool(loaded_config.get("copy", False))
    paths = scanner.build_docs(
        dirty=dirty,
        last_build_time=last_build_time,
        do_copy=do_copy,
        dry_run=dry_run,
    )
    for path in paths:
        if path.output_root != ".":
            continue
        destination_path = str(output_root / path.output_relpath)
        _materialize_include(
            source_path=path.input_path,
            destination_path=destination_path,
            include_mode=include_mode,
            dry_run=dry_run,
        )
    return paths
