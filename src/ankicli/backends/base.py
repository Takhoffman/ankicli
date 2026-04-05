"""Backend interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ankicli.app.credentials import SyncCredential
from ankicli.app.models import BackendCapabilities


class BaseBackend(ABC):
    name = "base"

    @abstractmethod
    def backend_capabilities(self) -> BackendCapabilities:
        raise NotImplementedError

    @abstractmethod
    def auth_status(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def login(
        self,
        collection_path: Path | None,
        *,
        username: str,
        password: str,
        endpoint: str | None,
    ) -> SyncCredential:
        raise NotImplementedError

    @abstractmethod
    def logout(self, collection_path: Path | None) -> dict:
        raise NotImplementedError

    @abstractmethod
    def sync_status(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def sync_run(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def sync_pull(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def sync_push(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def create_backup(
        self,
        collection_path: Path,
        *,
        backup_folder: Path,
        force: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def restore_backup(
        self,
        collection_path: Path,
        *,
        backup_path: Path,
        media_folder: Path,
        media_db_path: Path,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_collection_info(self, collection_path: Path) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_decks(self, collection_path: Path) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_deck(self, collection_path: Path, *, name: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def create_deck(self, collection_path: Path, *, name: str, dry_run: bool) -> dict:
        raise NotImplementedError

    @abstractmethod
    def rename_deck(
        self,
        collection_path: Path,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def delete_deck(self, collection_path: Path, *, name: str, dry_run: bool) -> dict:
        raise NotImplementedError

    @abstractmethod
    def reparent_deck(
        self,
        collection_path: Path,
        *,
        name: str,
        new_parent: str,
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_models(self, collection_path: Path) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_model(self, collection_path: Path, *, name: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_model_fields(self, collection_path: Path, *, name: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_model_templates(self, collection_path: Path, *, name: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_media(self, collection_path: Path) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def check_media(self, collection_path: Path) -> dict:
        raise NotImplementedError

    @abstractmethod
    def attach_media(
        self,
        collection_path: Path,
        *,
        source_path: Path,
        name: str | None,
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_orphaned_media(self, collection_path: Path) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def resolve_media_path(self, collection_path: Path, *, name: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_tags(self, collection_path: Path) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def rename_tag(
        self,
        collection_path: Path,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def delete_tags(
        self,
        collection_path: Path,
        *,
        tags: list[str],
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def reparent_tags(
        self,
        collection_path: Path,
        *,
        tags: list[str],
        new_parent: str,
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def find_notes(
        self,
        collection_path: Path,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def find_cards(
        self,
        collection_path: Path,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_note(self, collection_path: Path, note_id: int) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_note_fields(self, collection_path: Path, note_id: int) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_card(self, collection_path: Path, card_id: int) -> dict:
        raise NotImplementedError

    def get_card_presentation(self, collection_path: Path, card_id: int) -> dict | None:
        del collection_path, card_id
        return None

    @abstractmethod
    def add_note(
        self,
        collection_path: Path,
        *,
        deck_name: str,
        model_name: str,
        fields: dict[str, str],
        tags: list[str],
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def update_note(
        self,
        collection_path: Path,
        *,
        note_id: int,
        fields: dict[str, str],
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def delete_note(
        self,
        collection_path: Path,
        *,
        note_id: int,
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def move_note_to_deck(
        self,
        collection_path: Path,
        *,
        note_id: int,
        deck_name: str,
        dry_run: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def add_tags_to_notes(
        self,
        collection_path: Path,
        *,
        note_ids: list[int],
        tags: list[str],
        dry_run: bool,
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def remove_tags_from_notes(
        self,
        collection_path: Path,
        *,
        note_ids: list[int],
        tags: list[str],
        dry_run: bool,
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def suspend_cards(
        self,
        collection_path: Path,
        *,
        card_ids: list[int],
        dry_run: bool,
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def unsuspend_cards(
        self,
        collection_path: Path,
        *,
        card_ids: list[int],
        dry_run: bool,
    ) -> list[dict]:
        raise NotImplementedError
