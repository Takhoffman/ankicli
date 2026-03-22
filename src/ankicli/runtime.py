"""CLI runtime helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ankicli.backends.python_anki import PythonAnkiBackend


@dataclass(slots=True)
class Settings:
    collection: str | None
    backend_name: str
    json_output: bool


def get_backend(backend_name: str):
    if backend_name == "python-anki":
        return PythonAnkiBackend()
    raise ValueError(f"Unsupported backend: {backend_name}")

