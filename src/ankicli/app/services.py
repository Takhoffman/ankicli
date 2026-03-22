"""Services used by the CLI."""

from __future__ import annotations

import importlib.util
import platform
from pathlib import Path

from ankicli.app.errors import CollectionRequiredError, NotImplementedYetError
from ankicli.backends.base import BaseBackend


class DoctorService:
    """Environment and capability diagnostics."""

    def env_report(self) -> dict:
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "anki_import_available": importlib.util.find_spec("anki") is not None,
        }


class BackendService:
    """Backend inspection helpers."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def info(self) -> dict:
        return {
            "name": self.backend.name,
            "capabilities": self.backend.backend_capabilities().model_dump(),
        }


class CollectionService:
    """Collection-related operations."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def info(self, collection_path: str | None) -> dict:
        if not collection_path:
            raise CollectionRequiredError("A collection path is required for collection info")
        return self.backend.get_collection_info(Path(collection_path))


class CatalogService:
    """Deck and model listing services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def list_decks(self, collection_path: str | None) -> dict:
        if not collection_path:
            raise CollectionRequiredError("A collection path is required for deck list")
        return {"items": self.backend.list_decks(Path(collection_path))}

    def list_models(self, collection_path: str | None) -> dict:
        if not collection_path:
            raise CollectionRequiredError("A collection path is required for model list")
        return {"items": self.backend.list_models(Path(collection_path))}


class PlaceholderMutationService:
    """Stable placeholder for commands not built yet."""

    def fail(self, command_name: str) -> None:
        raise NotImplementedYetError(f"{command_name} is not implemented yet")

