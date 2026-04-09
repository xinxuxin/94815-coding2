"""Small utility helpers shared across modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union


def repo_root() -> Path:
    """Return the top-level project directory."""

    return Path(__file__).resolve().parents[1]


def load_prompt(path: Union[str, Path]) -> str:
    """Load a prompt template from disk."""

    return Path(path).read_text(encoding="utf-8")


def ensure_directory(path: Union[str, Path]) -> Path:
    """Create a directory if it does not already exist."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_json(path: Union[str, Path], payload: Any) -> Path:
    """Write JSON payload to disk with stable formatting."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path
