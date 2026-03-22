"""Backend interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ankicli.app.models import BackendCapabilities


class BaseBackend(ABC):
    name = "base"

    @abstractmethod
    def backend_capabilities(self) -> BackendCapabilities:
        raise NotImplementedError

    @abstractmethod
    def get_collection_info(self, collection_path: Path) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_decks(self, collection_path: Path) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def list_models(self, collection_path: Path) -> list[dict]:
        raise NotImplementedError

