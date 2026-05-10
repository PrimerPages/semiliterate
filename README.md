# semiliterate

`semiliterate` is a standalone extraction engine and CLI for building markdown
documentation from semiliterate source files. It preserves the extraction
behavior from `mkdocs-simple-plugin` without depending on MkDocs.

## Install

```bash
pip install -e .
```

## CLI

```bash
semiliterate build --source . --out .build-docs
```

Options:

- `--config PATH`: load YAML config
- `--source PATH`: source tree root
- `--out PATH`: output tree
- `--include-mode copy|symlink|skip`: how included files are materialized
- `--dry-run`: scan and report without writing files
- `-v`, `--verbose`: enable info logging

## Config

The YAML config is intentionally close to the previous plugin config:

```yaml
folders:
  - src
  - examples

ignore:
  - .git/**
  - node_modules/**
  - _site/**

include:
  - "*.md"
  - "*.png"

semiliterate:
  - pattern: ".*"
    terminate: "^\\W*md-ignore"
    extract:
      - start: "^\\s*\"\"\"\\W?md\\b"
        stop: "^\\s*\"\"\"\\s*$"
```

## Python API

```python
from semiliterate import ExtractionPattern
from semiliterate import Semiliterate
from semiliterate import build_docs

build_docs(source=".", out=".build-docs")
```

Useful exports:

- `Semiliterate`
- `ExtractionPattern`
- `SimpleScanner`
- `build_docs`
- `load_config`

## Compatibility Notes

- The extraction regexes and inline parameter behavior are carried over
  directly from `mkdocs-simple-plugin`.
- `.mkdocsignore`, include matching, hidden-file handling, and destination file
  naming follow the original implementation.
- This package does not depend on MkDocs and does not include any plugin or
  site-generator integration.

## Example

Given a source file:

```python
"""md
# Title
Some docs.
"""
```

Running:

```bash
semiliterate build --source . --out .build-docs
```

creates:

```text
.build-docs/<source-file-basename>.md
```
