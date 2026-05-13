"""Source tree scanning and extraction dispatch."""

from __future__ import annotations

"""md
# Scanner

The scanner walks the source tree, filters ignored paths, forwards extractable
files to semiliterate rules, and tracks the output paths produced by a build.

## Main types

- `BuildPath`: records the source file and generated destination path
- `SimpleScanner`: scans folders, applies ignore rules, and dispatches
  extraction
"""

from dataclasses import dataclass
import fnmatch
import os
from pathlib import Path
import shutil
import stat
from typing import Dict, Iterable, List

from semiliterate.extractor import Semiliterate


def _is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


@dataclass
class BuildPath:
    """Paths processed by the scanner."""

    output_root: str
    output_relpath: str
    input_path: str


class SimpleScanner:
    """Standalone tree scanner based on the original Simple class."""

    def __init__(
        self,
        build_dir: str,
        folders: list,
        include: list,
        ignore: list,
        ignore_hidden: bool,
        ignore_paths: list,
        semiliterate: list,
        root_path: str = ".",
        **kwargs
    ):
        self.build_dir = os.path.abspath(build_dir)
        self.folders = set(folders)
        self.doc_glob = set(include)
        self.ignore_glob = set(ignore)
        self.ignore_hidden = ignore_hidden
        self.hidden_prefix = set([".", "__"])
        self.ignore_paths = set(Path(path).resolve() for path in ignore_paths)
        self.semiliterate = []
        for item in semiliterate:
            self.semiliterate.append(Semiliterate(**item))
        self.ignore_patterns: Dict[Path, List[str]] = {}
        self.root_path = Path(root_path).resolve()

    def process_mkdocsignore_files(self) -> None:
        """Process all .mkdocsignore files and update ignore_glob."""
        for mkdocsignore in self.root_path.rglob(".mkdocsignore"):
            relative_path = mkdocsignore.parent.relative_to(self.root_path)
            patterns = []
            with mkdocsignore.open(mode="r", encoding="utf-8") as txt_file:
                for line in txt_file:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)

            if not patterns:
                pattern = str(relative_path / "**")
                self.ignore_glob.add(pattern)
            else:
                for pattern in patterns:
                    if relative_path != Path("."):
                        pattern = str(relative_path / pattern)
                    self.ignore_glob.add(pattern)

    def process_ignore_folders(self) -> None:
        """Update ignore glob to include folders."""
        self.ignore_glob.update(
            ["{0}/**".format(pattern) for pattern in self.ignore_glob]
        )

    def get_files(self) -> List[str]:
        """Get a list of files to process, excluding ignored files."""
        self.process_mkdocsignore_files()
        self.process_ignore_folders()
        files = set()
        for pattern in self.folders:
            for entry in self.root_path.glob(pattern):
                if entry.is_dir():
                    files.update(
                        str(file_path.relative_to(self.root_path))
                        for file_path in entry.rglob("*")
                        if self.is_valid_file(file_path)
                    )
                elif self.is_valid_file(entry):
                    files.add(str(entry.relative_to(self.root_path)))
        return list(files)

    def is_valid_file(self, path: Path) -> bool:
        """Check if file is valid."""
        if self.is_ignored(path):
            return False
        if not path.is_file():
            return False
        return True

    def is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored."""
        rel_path = path.relative_to(self.root_path)
        resolved_path = path.resolve()
        if any(_is_relative_to(resolved_path, ignored) for ignored in self.ignore_paths):
            return True
        return any(
            fnmatch.fnmatch(str(rel_path), pattern) for pattern in self.ignore_glob
        )

    def is_doc_file(self, name: str) -> bool:
        """Check if file is a desired doc file."""

        def match_pattern(path_name: str, pattern: str) -> bool:
            if fnmatch.fnmatch(path_name, pattern):
                return True
            if any(char in pattern for char in "*?[]"):
                return False
            basename = os.path.basename(path_name)
            if pattern.startswith("."):
                return basename.endswith(pattern)
            return basename == pattern

        return any(match_pattern(name, pattern) for pattern in self.doc_glob)

    def should_extract_file(self, name: str) -> bool:
        """Check if file should be extracted."""

        def has_hidden_attribute(filepath: str) -> bool:
            try:
                return bool(
                    os.stat(filepath).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN
                )
            except (AttributeError, AssertionError):
                return False

        def has_hidden_prefix(filepath: str) -> bool:
            parts = filepath.split(os.path.sep)

            def hidden_prefix(part_name: str) -> bool:
                if part_name == ".":
                    return False
                return any(part_name.startswith(pattern) for pattern in self.hidden_prefix)

            return any(hidden_prefix(part) for part in parts)

        try:
            with open(name, "r", encoding="utf-8") as file_object:
                _ = file_object.read()
        except UnicodeDecodeError:
            return False

        if self.ignore_hidden:
            is_hidden = has_hidden_prefix(name) or has_hidden_attribute(name)
            return not is_hidden
        return True

    def build_docs(
        self,
        dirty: bool = False,
        last_build_time: float = None,
        do_copy: bool = False,
        dry_run: bool = False,
    ) -> List[BuildPath]:
        """Build documentation paths from workspace files."""
        paths = []
        files = self.get_files()
        for file_name in files:
            source_path = self.root_path / file_name
            if not os.path.isfile(source_path):
                continue
            if dirty and last_build_time and os.path.getmtime(source_path) <= last_build_time:
                continue
            from_dir = os.path.dirname(file_name)
            name = os.path.basename(file_name)
            build_prefix = os.path.normpath(os.path.join(self.build_dir, from_dir))

            doc_paths = self.get_doc_file(
                from_dir,
                name,
                build_prefix,
                do_copy=do_copy,
                dry_run=dry_run,
            )
            if doc_paths:
                paths.append(
                    BuildPath(
                        output_root=".",
                        output_relpath=file_name,
                        input_path=str(source_path),
                    )
                )
                continue

            extracted_paths = self.try_extract(
                from_dir,
                name,
                build_prefix,
                dry_run=dry_run,
            )
            for path in extracted_paths:
                paths.append(
                    BuildPath(
                        output_root=self.build_dir,
                        output_relpath=os.path.relpath(path, self.build_dir),
                        input_path=str(source_path),
                    )
                )
        return paths

    def try_extract(
        self,
        from_dir: str,
        name: str,
        to_dir: str,
        dry_run: bool = False,
    ) -> List[str]:
        """Extract content from file into destination."""
        path = self.root_path / from_dir / name if from_dir else self.root_path / name
        if not self.should_extract_file(str(path)):
            return []
        for item in self.semiliterate:
            source_dir = str(path.parent)
            paths = item.try_extraction(source_dir, name, to_dir, dry_run=dry_run)
            if paths:
                return paths
        return []

    def get_doc_file(
        self,
        from_dir: str,
        name: str,
        to_dir: str,
        do_copy: bool,
        dry_run: bool = False,
    ) -> List[str]:
        """Copy file with the same name to a new directory."""
        original = str(self.root_path / from_dir / name) if from_dir else str(self.root_path / name)
        if not self.is_doc_file(os.path.join(from_dir, name)):
            return []
        if do_copy and not dry_run:
            destination = os.path.join(to_dir, name)
            os.makedirs(to_dir, exist_ok=True)
            shutil.copy2(original, destination)
        return [original]
