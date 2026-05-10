"""Tests for source scanning and build path generation."""

import os
from pathlib import Path

from semiliterate.scanner import SimpleScanner


def make_scanner(tmp_path, **overrides):
    settings = {
        "build_dir": str(tmp_path / "build"),
        "folders": ["*"],
        "ignore": [],
        "include": ["*.md"],
        "ignore_hidden": True,
        "ignore_paths": [],
        "semiliterate": [],
        "root_path": str(tmp_path),
    }
    settings.update(overrides)
    return SimpleScanner(**settings)


def test_should_extract_file_binary(tmp_path):
    scanner = make_scanner(tmp_path)
    binary_path = tmp_path / "example.bin"
    text_path = tmp_path / "example.md"
    binary_path.write_bytes(b"\x80\xff")
    text_path.write_text("Hello_word", encoding="utf-8")

    assert scanner.should_extract_file(str(binary_path)) is False
    assert scanner.should_extract_file(str(text_path)) is True


def test_ignored_mkdocsignore(tmp_path):
    scanner = make_scanner(tmp_path)
    (tmp_path / ".mkdocsignore").write_text("*foo*", encoding="utf-8")
    (tmp_path / "foo.md").write_text("", encoding="utf-8")
    (tmp_path / "hello.md").write_text("", encoding="utf-8")
    (tmp_path / "directory").mkdir()
    (tmp_path / "directory" / ".mkdocsignore").write_text("*bar*", encoding="utf-8")
    (tmp_path / "directory" / "foo.md").write_text("", encoding="utf-8")
    (tmp_path / "directory" / "bar.md").write_text("", encoding="utf-8")
    (tmp_path / "directory" / "world.md").write_text("", encoding="utf-8")

    files = scanner.get_files()

    assert "foo.md" not in files
    assert "hello.md" in files
    assert "directory/foo.md" not in files
    assert "directory/bar.md" not in files
    assert "directory/world.md" in files


def test_build_docs_extract(tmp_path):
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "module.py").write_text(
        '"""md\n# Title\n"""\n',
        encoding="utf-8",
    )

    scanner = make_scanner(
        tmp_path,
        folders=["src"],
        include=["*.md"],
        semiliterate=[
            {
                "pattern": r".*",
                "extract": [
                    {
                        "start": r'^\s*"""\W?md\b',
                        "stop": r'^\s*"""\s*$',
                    }
                ],
            }
        ],
    )

    paths = scanner.build_docs()

    assert len(paths) == 1
    assert paths[0].input_path == str(source_dir / "module.py")
    assert paths[0].output_relpath == os.path.join("src", "module.md")
    assert (tmp_path / "build" / "src" / "module.md").read_text(encoding="utf-8") == "# Title\n"


def test_build_docs_include(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "index.md").write_text("# Hello\n", encoding="utf-8")

    scanner = make_scanner(tmp_path, folders=["docs"], include=["*.md"])
    paths = scanner.build_docs()

    assert len(paths) == 1
    assert paths[0].output_root == "."
    assert paths[0].output_relpath == os.path.join("docs", "index.md")


def test_is_doc_file_does_not_match_md_jinja(tmp_path):
    scanner = make_scanner(
        tmp_path,
        include=[".md", ".pages"],
    )

    assert scanner.is_doc_file("file.md") is True
    assert scanner.is_doc_file("file.md.jinja") is False
    assert scanner.is_doc_file(".pages") is True
    assert scanner.is_doc_file("nested/.pages") is True
