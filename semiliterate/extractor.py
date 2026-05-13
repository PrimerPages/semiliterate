"""Semiliterate extraction engine."""

from __future__ import annotations

"""md
# Extraction Engine

The extractor module is responsible for recognizing semiliterate markers in
source files and writing matching content into markdown outputs.

## Main types

- `ExtractionPattern`: compiled start, stop, and replacement rules
- `StreamExtract`: stateful line-by-line extractor for one input stream
- `Semiliterate`: configured wrapper that applies patterns to matching files
"""

from dataclasses import dataclass, field
from io import TextIOWrapper
import logging
import os
import re
from typing import List, Optional


LOG = logging.getLogger(__name__)


def _get_match(pattern: Optional[re.Pattern], line: str) -> Optional[re.Match]:
    """Return the match for the given pattern."""
    if not pattern:
        return None
    return pattern.search(line)


@dataclass
class InlineParams:
    """Inline parameters for extraction."""

    filename_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r'file=[\"\']?(\w+.\w+)[\"\']?\b')
    )
    filename: Optional[str] = None
    trim_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r'trim=[\"\']?(\d+)[\"\']?\b')
    )
    trim: int = 0
    content_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r'content=[\"\']?([^\"\']*)[\"\']?')
    )
    content: Optional[re.Pattern] = None
    stop_pattern: re.Pattern = field(
        default_factory=lambda: re.compile(r'stop=[\"\']?([^\"\']*)[\"\']?')
    )


class ExtractionPattern:
    """An extraction pattern for a file."""

    def __init__(
        self,
        start: Optional[str] = None,
        stop: Optional[str] = None,
        replace: Optional[list] = None,
    ):
        self.start = re.compile(start) if start else None
        self._stop_default = re.compile(stop) if stop else None
        self.stop = self._stop_default
        if not replace:
            replace = []
        self.replace = []
        for item in replace:
            if isinstance(item, str):
                self.replace.append(re.compile(item))
            else:
                self.replace.append((re.compile(item[0]), item[1]))

        self.inline = InlineParams()

    def setup(self, line: str) -> None:
        """Process input parameters."""
        setup_inline = InlineParams()

        file_match = _get_match(setup_inline.filename_pattern, line)
        if file_match and file_match.lastindex:
            setup_inline.filename = file_match[file_match.lastindex]

        trim_match = _get_match(setup_inline.trim_pattern, line)
        if trim_match and trim_match.lastindex:
            setup_inline.trim = int(trim_match[trim_match.lastindex])

        content_match = _get_match(setup_inline.content_pattern, line)
        if content_match and content_match.lastindex:
            regex_pattern = content_match[content_match.lastindex]
            setup_inline.content = re.compile(regex_pattern)

        self.stop = self._stop_default
        stop_match = _get_match(setup_inline.stop_pattern, line)
        if stop_match and stop_match.lastindex:
            regex_pattern = stop_match[stop_match.lastindex]
            self.stop = re.compile(regex_pattern)

        self.inline = setup_inline

    def get_filename(self) -> Optional[str]:
        """Return the filename if defined in start arguments."""
        return self.inline.filename

    def replace_line(self, line: str) -> Optional[str]:
        """Apply the specified replacements to the line and return it."""
        if self.inline.trim:
            line = line[self.inline.trim:]
        if self.inline.content:
            match_object = _get_match(self.inline.content, line)
            if match_object and match_object.lastindex:
                return match_object[match_object.lastindex]
        if not self.replace:
            return line
        for item in self.replace:
            pattern = item[0] if isinstance(item, tuple) else item
            match_object = pattern.search(line)
            if match_object:
                if isinstance(item, tuple):
                    return match_object.expand(item[1])
                if match_object.lastindex:
                    return match_object[match_object.lastindex]
                return None
        return line


class LazyFile:
    """Create the file only if a non-empty string is written."""

    def __init__(self, directory: str, name: str, enabled: bool = True):
        self.file_directory = directory
        self.file_name = name
        self.file_object = None
        self.enabled = enabled
        self._wrote = False

    def __eq__(self, other) -> bool:
        return (
            self.file_directory == other.file_directory
            and self.file_name == other.file_name
        )

    def __str__(self) -> str:
        return os.path.join(self.file_directory, self.file_name)

    def write(self, arg: Optional[str]) -> None:
        """Create and write a string line to the file, iff not none."""
        if arg is None:
            return
        self._wrote = True
        if self.file_object is None and self.enabled:
            filename = os.path.join(self.file_directory, self.file_name)
            os.makedirs(self.file_directory, exist_ok=True)
            self.file_object = open(filename, "w+", encoding="utf-8")

        def get_line(line: str) -> str:
            return line if line.endswith("\n") else line + "\n"

        if self.file_object is not None:
            self.file_object.write(get_line(arg))

    def close(self) -> Optional[str]:
        """Finish the file."""
        file_path = os.path.join(self.file_directory, self.file_name)
        if self.file_object is not None:
            LOG.debug("... extracted %s", file_path)
            self.file_object.close()
            self.file_object = None
            return file_path
        if self._wrote:
            return file_path
        return None


class StreamExtract:
    """Extract files to an output stream."""

    def __init__(
        self,
        input_stream: TextIOWrapper,
        output_stream: LazyFile,
        terminate: Optional[re.Pattern] = None,
        patterns: Optional[List[ExtractionPattern]] = None,
        **kwargs
    ):
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.terminate = terminate
        self.patterns = patterns

        self._default_stream = output_stream
        self._output_files = []
        self._streams = {output_stream.file_name: output_stream}

    def _try_extract_match(
        self,
        match_object: Optional[re.Match],
        emit_last: bool = True,
    ) -> bool:
        """Extract line iff there's a match."""
        if not match_object:
            return False
        if match_object.lastindex and emit_last:
            self.output_stream.write(match_object[match_object.lastindex])
        return True

    def close(self) -> List[str]:
        """Close the file and return a list of filenames written to."""
        file_path = self.output_stream.close()
        if file_path:
            self._output_files.append(file_path)
        return self._output_files

    def set_output_file(self, filename: Optional[str]) -> LazyFile:
        """Set the current output stream from filename and return the stream."""
        output_stream = self.output_stream
        if filename:
            if filename in self._streams:
                return self.set_output_stream(self._streams[filename])
            output_stream = LazyFile(
                self.output_stream.file_directory,
                filename,
                enabled=self.output_stream.enabled,
            )
            self._streams[filename] = output_stream
        return self.set_output_stream(output_stream)

    def set_output_stream(self, stream: LazyFile) -> LazyFile:
        """Set the current output stream and return the stream."""
        if self.output_stream != stream:
            self.close()
            self.output_stream = stream
        return self.output_stream

    def extract(self, **kwargs) -> List[str]:
        """Extract from file with semiliterate configuration."""
        active_pattern = None if self.patterns else ExtractionPattern()
        patterns = self.patterns if self.patterns else []
        for pattern in patterns:
            if not pattern.start:
                active_pattern = pattern

        for line in self.input_stream:
            if self._try_extract_match(
                _get_match(self.terminate, line), active_pattern
            ):
                return self.close()
            if active_pattern is None:
                for pattern in patterns:
                    start = _get_match(pattern.start, line)
                    if start:
                        active_pattern = pattern
                        active_pattern.setup(line)
                        self.set_output_file(active_pattern.get_filename())
                        self._try_extract_match(start)
                        break
                continue
            if self._try_extract_match(_get_match(active_pattern.stop, line)):
                active_pattern = None
                self.set_output_stream(self._default_stream)
                continue
            self.extract_line(line, active_pattern)
        return self.close()

    def extract_line(self, line: str, extraction_pattern: ExtractionPattern) -> None:
        """Copy line to the output stream, applying specified replacements."""
        line = extraction_pattern.replace_line(line)
        self.output_stream.write(line)


class Semiliterate:
    """Extract documentation from source files using regex settings."""

    def __init__(
        self,
        pattern: str,
        destination: Optional[str] = None,
        terminate: Optional[str] = None,
        extract: Optional[list] = None,
    ):
        self.file_filter = re.compile(pattern)
        self.destination = destination
        self.terminate = (terminate is not None) and re.compile(terminate)
        self.extractions = []
        if not extract:
            extract = []
        if isinstance(extract, dict):
            extract = [extract]
        for extract_params in extract:
            self.extractions.append(ExtractionPattern(**extract_params))

    def filename_match(self, name: str) -> Optional[str]:
        """Get the output filename for the match, otherwise return None."""
        name_match = self.file_filter.search(name)
        if name_match:
            new_name = os.path.splitext(name)[0] + ".md"
            if self.destination:
                new_name = name_match.expand(self.destination)
            return new_name
        return None

    def try_extraction(
        self,
        from_directory: str,
        from_file: str,
        destination_directory: str,
        dry_run: bool = False,
        **kwargs
    ) -> List[str]:
        """Try to extract documentation from a file."""
        to_file = self.filename_match(from_file)
        if not to_file:
            return []
        from_file_path = os.path.join(from_directory, from_file)
        try:
            with open(from_file_path, encoding="utf-8") as original_file:
                LOG.debug("Scanning %s...", from_file_path)
                extraction = StreamExtract(
                    input_stream=original_file,
                    output_stream=LazyFile(
                        destination_directory,
                        to_file,
                        enabled=not dry_run,
                    ),
                    terminate=self.terminate,
                    patterns=self.extractions,
                    **kwargs
                )
                return extraction.extract()
        except UnicodeDecodeError as error:
            LOG.debug("Skipped %s", from_file_path)
            LOG.debug("Error details: %s", str(error))
        except (OSError, IOError) as error:
            LOG.error("could not build %s\n%s", from_file_path, str(error))
        return []
