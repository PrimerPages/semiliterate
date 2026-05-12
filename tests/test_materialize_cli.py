"""Tests for config loading, materialization, and CLI."""

import os
from pathlib import Path

import yaml

from semiliterate.cli import main
from semiliterate.config import DEFAULT_CONFIG, load_config
from semiliterate.materialize import build_docs


def test_load_config_yaml_override(tmp_path):
    config_path = tmp_path / "semiliterate.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "folders": ["src"],
                "include": ["*.md", "*.png"],
                "ignore": ["node_modules/**"],
            }
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config["folders"] == ["src"]
    assert config["include"] == ["*.md", "*.png"]
    assert config["ignore"] == ["node_modules/**"]
    assert "semiliterate" in config


def test_load_config_merges_include_extra_and_ignore_extra(tmp_path):
    config_path = tmp_path / "semiliterate.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "include_extra": ["*.csv", "*.png"],
                "ignore_extra": ["_build/**"],
            }
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config["include"] == DEFAULT_CONFIG["include"] + ["*.csv"]
    assert config["ignore"] == DEFAULT_CONFIG["ignore"] + ["_build/**"]
    assert "include_extra" not in config
    assert "ignore_extra" not in config


def test_build_docs_materializes_included_files(tmp_path):
    source_dir = tmp_path / "project"
    output_dir = tmp_path / "build"
    docs_dir = source_dir / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "index.md").write_text("# Hello\n", encoding="utf-8")

    paths = build_docs(
        source=str(source_dir),
        out=str(output_dir),
        config={"folders": ["docs"], "include": ["*.md"], "ignore": [], "semiliterate": []},
    )

    assert len(paths) == 1
    assert (output_dir / "docs" / "index.md").read_text(encoding="utf-8") == "# Hello\n"


def test_build_docs_accepts_include_extra_in_config(tmp_path):
    source_dir = tmp_path / "project"
    output_dir = tmp_path / "build"
    docs_dir = source_dir / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "notes.txt").write_text("plain text", encoding="utf-8")

    paths = build_docs(
        source=str(source_dir),
        out=str(output_dir),
        config={"folders": ["docs"], "include_extra": ["*.txt"], "ignore": [], "semiliterate": []},
    )

    assert len(paths) == 1
    assert paths[0].output_relpath == os.path.join("docs", "notes.txt")
    assert (output_dir / "docs" / "notes.txt").read_text(encoding="utf-8") == "plain text"


def test_build_docs_dry_run(tmp_path):
    source_dir = tmp_path / "project"
    output_dir = tmp_path / "build"
    source_dir.mkdir()
    (source_dir / "module.py").write_text('"""md\n# Title\n"""\n', encoding="utf-8")

    paths = build_docs(source=str(source_dir), out=str(output_dir), dry_run=True)

    assert len(paths) == 1
    assert not (output_dir / "module.md").exists()


def test_cli_build(tmp_path):
    source_dir = tmp_path / "project"
    output_dir = tmp_path / "build"
    source_dir.mkdir()
    (source_dir / "module.py").write_text('"""md\n# Title\n"""\n', encoding="utf-8")

    exit_code = main(["build", "--source", str(source_dir), "--out", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "module.md").read_text(encoding="utf-8") == "# Title\n"


def test_cli_build_with_config(tmp_path):
    source_dir = tmp_path / "project"
    output_dir = tmp_path / "build"
    source_dir.mkdir()
    (source_dir / "src").mkdir()
    (source_dir / "src" / "notes.txt").write_text("plain text", encoding="utf-8")

    config_path = tmp_path / "semiliterate.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "folders": ["src"],
                "ignore": [],
                "include_extra": ["*.txt"],
                "semiliterate": [],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "build",
            "--source",
            str(source_dir),
            "--out",
            str(output_dir),
            "--config",
            str(config_path),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "src" / "notes.txt").read_text(encoding="utf-8") == "plain text"


def test_build_docs_ignores_output_inside_source(tmp_path):
    source_dir = tmp_path / "project"
    output_dir = source_dir / "_build"
    source_dir.mkdir()
    (source_dir / "module.py").write_text('"""md\n# Title\n"""\n', encoding="utf-8")

    paths_first = build_docs(source=str(source_dir), out=str(output_dir))
    paths_second = build_docs(source=str(source_dir), out=str(output_dir))

    assert len(paths_first) == 1
    assert len(paths_second) == 1
    assert (output_dir / "module.md").read_text(encoding="utf-8") == "# Title\n"
    assert not (output_dir / "_build" / "module.md").exists()
