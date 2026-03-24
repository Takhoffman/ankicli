"""CLI runtime helpers."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from ankicli.backends.ankiconnect import AnkiConnectBackend
from ankicli.backends.python_anki import PythonAnkiBackend


@dataclass(slots=True)
class Settings:
    collection: str | None
    backend_name: str
    json_output: bool


def configure_anki_source_path() -> str | None:
    source_path = os.environ.get("ANKI_SOURCE_PATH")
    if not source_path:
        return None

    source_root = Path(source_path).expanduser().resolve()
    candidate_paths = [
        source_root / "pylib",
        source_root / "python",
        source_root,
    ]
    for candidate in candidate_paths:
        if candidate.exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)
            return candidate_str
    return str(source_root)


def get_backend(backend_name: str):
    configure_anki_source_path()
    if backend_name == "python-anki":
        return PythonAnkiBackend()
    if backend_name == "ankiconnect":
        return AnkiConnectBackend()
    raise ValueError(f"Unsupported backend: {backend_name}")
