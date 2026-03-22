"""Python-Anki backend."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from ankicli.app.errors import BackendUnavailableError
from ankicli.app.models import BackendCapabilities
from ankicli.backends.base import BaseBackend


class PythonAnkiBackend(BaseBackend):
    name = "python-anki"

    def backend_capabilities(self) -> BackendCapabilities:
        available = importlib.util.find_spec("anki") is not None
        notes = []
        if not available:
            notes.append("Python package 'anki' is not installed in the current environment.")
        return BackendCapabilities(
            backend=self.name,
            available=available,
            supports_collection_reads=available,
            supports_collection_writes=available,
            supports_live_desktop=False,
            notes=notes,
        )

    def _require_available(self) -> None:
        if not self.backend_capabilities().available:
            raise BackendUnavailableError("Python-Anki backend is unavailable in this environment")

    def get_collection_info(self, collection_path: Path) -> dict:
        self._require_available()
        return {
            "collection_path": str(collection_path),
            "implemented": False,
            "counts": None,
        }

    def list_decks(self, collection_path: Path) -> list[dict]:
        self._require_available()
        return []

    def list_models(self, collection_path: Path) -> list[dict]:
        self._require_available()
        return []

