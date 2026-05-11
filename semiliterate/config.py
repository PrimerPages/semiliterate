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

DEFAULT_CONFIG = {
    "folders": ["*"],
    "ignore": [
        "*.egg-info",
        "**/__pycache__/**",
        "vendor/**",
        "venv/**",
        ".**/**",
    ],
    "include": MARKDOWN_FILES + IMAGE+FILES + [
        "*.pdf",
        "CNAME",
        "*.snippet",
        ".pages",
        ".nav.yml"
    ],
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


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML and merge with defaults."""
    config = default_config()
    if not config_path:
        return config

    with open(config_path, "r", encoding="utf-8") as stream:
        loaded = yaml.safe_load(stream) or {}

    for key, value in loaded.items():
        config[key] = value
    return config
