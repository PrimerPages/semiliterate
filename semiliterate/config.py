"""Configuration helpers for semiliterate."""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

import yaml

MARKDOWN_FILES = [
    ".markdown",
    ".mdown",
    ".mkdn",
    ".mkd",
    ".md",
]

IMAGE_FILES = [
    "*.bmp",
    "*.tif",
    "*.tiff",
    "*.gif",
    "*.svg",
    "*.jpeg",
    "*.jpg",
    "*.jif",
    "*.jiff",
    "*.jp2",
    "*.jpx",
    "*.j2k",
    "*.j2c",
    "*.fpx",
    "*.pcd",
    "*.png",
]

HTML_FILES = [
    "*.html",
    "*.htm",
    "*.xhtml",
    "*.js"
]

DEFAULT_CONFIG = {
    "folders": ["*"],
    "ignore": [
        "*.egg-info",
        "**/__pycache__/**",
        "vendor/**",
        "venv/**",
        ".**/**",
    ],
    "include": MARKDOWN_FILES + IMAGE_FILES + HTML_FILES,
    "ignore_hidden": True,
    "copy": False,
    "semiliterate": [
        {
            "pattern": r".*",
            "terminate": r"^\W*md-ignore",
            "extract": [
                {
                    "start": r'^\s*"""\W?md\b',
                    "stop": r'^\s*"""\s*$',
                },
                {
                    "start": r"^\s*#+\W?md\b",
                    "stop": r"^\s*#\s?\/md\s*$",
                    "replace": [r"^\s*# ?(.*\n?)$", r"^.*$"],
                },
                {
                    "start": r"^\s*/\*+\W?md\b",
                    "stop": r"^\s*\*\*/\s*$",
                },
                {
                    "start": r"^\s*\/\/+\W?md\b",
                    "stop": r"^\s*\/\/\send\smd\s*$",
                    "replace": [r"^\s*\/\/\s?(.*\n?)$", r"^.*$"],
                },
                {
                    "start": r"<!--\W?md\b",
                    "stop": r"-->\s*$",
                },
            ],
        },
    ],
}


def default_config() -> Dict[str, Any]:
    """Return a deep copy of the default config."""
    return copy.deepcopy(DEFAULT_CONFIG)


def _as_list(value: Optional[Any]) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _merge_unique(base: list, extra: list) -> list:
    merged = list(base)
    for item in extra:
        if item not in merged:
            merged.append(item)
    return merged


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply derived config defaults and merge list extras."""
    normalized = copy.deepcopy(config)
    include = _as_list(normalized.get("include", []))
    ignore = _as_list(normalized.get("ignore", []))
    include_extra = _as_list(normalized.pop("include_extra", []))
    ignore_extra = _as_list(normalized.pop("ignore_extra", []))

    normalized["include"] = _merge_unique(include, include_extra)
    normalized["ignore"] = _merge_unique(ignore, ignore_extra)
    return normalized


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML and merge with defaults."""
    config = default_config()
    if not config_path:
        return config

    with open(config_path, "r", encoding="utf-8") as stream:
        loaded = yaml.safe_load(stream) or {}

    for key, value in loaded.items():
        config[key] = value
    return normalize_config(config)
