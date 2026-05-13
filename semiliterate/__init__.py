"""Standalone semiliterate extraction package."""

"""md
# Package Overview

`semiliterate` exposes a small extraction toolkit for turning source trees into
reference-friendly markdown output.

## Public API

- `build_docs`: scan a source tree and materialize extracted docs
- `load_config`: load and normalize semiliterate YAML config
- `Semiliterate`: extraction engine for one configured rule set
- `SimpleScanner`: filesystem scanner and extraction dispatcher
"""

from semiliterate.config import DEFAULT_CONFIG, load_config
from semiliterate.extractor import ExtractionPattern, Semiliterate
from semiliterate.materialize import build_docs
from semiliterate.scanner import BuildPath, SimpleScanner

__all__ = [
    "BuildPath",
    "DEFAULT_CONFIG",
    "ExtractionPattern",
    "Semiliterate",
    "SimpleScanner",
    "build_docs",
    "load_config",
]
