"""Tests for semiliterate extraction primitives."""

from io import TextIOWrapper
import os
from pathlib import Path
from unittest.mock import MagicMock

from semiliterate.extractor import (
    ExtractionPattern,
    LazyFile,
    Semiliterate,
    StreamExtract,
)


def assert_contents_equal(path: Path, expected_contents):
    with open(path, "r", encoding="utf-8") as file_object:
        actual_contents = file_object.read().splitlines()
    assert actual_contents == expected_contents


def test_extraction_pattern_setup_filename():
    pattern = ExtractionPattern()
    pattern.setup("//md file=new_name.snippet")
    assert pattern.get_filename() == "new_name.snippet"


def test_extraction_pattern_setup_trim():
    pattern = ExtractionPattern()
    pattern.setup("//md trim=2")
    assert pattern.replace_line("1234") == "34"
    assert pattern.replace_line("1") == ""


def test_extraction_pattern_setup_content():
    pattern = ExtractionPattern()
    pattern.setup("//md content='(hello)'")
    assert pattern.replace_line("hello world") == "hello"


def test_extraction_pattern_setup_stop():
    pattern = ExtractionPattern()
    pattern.setup("//md stop='.*(world)'")
    assert pattern.stop.pattern == ".*(world)"


def test_lazy_file_write(tmp_path):
    lazy_file = LazyFile(directory=str(tmp_path), name="test.md")
    lazy_file.write("test line")
    lazy_file.write("second_line")
    output = lazy_file.close()
    assert output == str(tmp_path / "test.md")
    assert_contents_equal(tmp_path / "test.md", ["test line", "second_line"])


def test_stream_extract_basic(tmp_path):
    input_stream = MagicMock(spec=TextIOWrapper)
    input_stream.__iter__.return_value = iter(
        ["Line 1", "START", "Extracted Text", "STOP", "Line 2"]
    )
    output_path = tmp_path / "output.md"
    output_stream = LazyFile(directory=str(tmp_path), name="output.md")
    extractor = StreamExtract(
        input_stream=input_stream,
        output_stream=output_stream,
        patterns=[ExtractionPattern(start=r"START", stop=r"STOP")],
    )

    output_files = extractor.extract()

    assert output_files == [str(output_path)]
    assert_contents_equal(output_path, ["Extracted Text"])


def test_stream_extract_inline_filename(tmp_path):
    input_stream = MagicMock(spec=TextIOWrapper)
    input_stream.__iter__.return_value = iter(
        [
            '// md file="alt.md"',
            "// copied",
            "// end md",
        ]
    )
    output_stream = LazyFile(directory=str(tmp_path), name="output.md")
    extractor = StreamExtract(
        input_stream=input_stream,
        output_stream=output_stream,
        patterns=[
            ExtractionPattern(
                start=r"^\s*\/\/+\W?md\b",
                stop=r"^\s*\/\/\send\smd\s*$",
                replace=[r"^\s*\/\/\s?(.*\n?)$", r"^.*$"],
            )
        ],
    )

    output_files = extractor.extract()

    assert output_files == [str(tmp_path / "alt.md")]
    assert_contents_equal(tmp_path / "alt.md", ["copied"])


def test_semiliterate_filename_match_with_destination():
    semiliterate = Semiliterate(pattern=r"(.*)\.txt", destination=r"\1_output.md")
    assert semiliterate.filename_match("example.txt") == "example_output.md"


def test_semiliterate_try_extraction_successful(tmp_path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    (source_dir / "example.txt").write_text("Sample content", encoding="utf-8")

    semiliterate = Semiliterate(pattern=r".*\.txt")
    result = semiliterate.try_extraction(
        from_directory=str(source_dir),
        from_file="example.txt",
        destination_directory=str(output_dir),
    )

    assert result == [str(output_dir / "example.md")]
    assert (output_dir / "example.md").read_text(encoding="utf-8") == "Sample content\n"


def test_semiliterate_dry_run_does_not_write(tmp_path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    (source_dir / "example.txt").write_text("Sample content", encoding="utf-8")

    semiliterate = Semiliterate(pattern=r".*\.txt")
    result = semiliterate.try_extraction(
        from_directory=str(source_dir),
        from_file="example.txt",
        destination_directory=str(output_dir),
        dry_run=True,
    )

    assert result == [str(output_dir / "example.md")]
    assert not (output_dir / "example.md").exists()
