"""AnkiConnect backend."""

from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ankicli.app.credentials import SyncCredential
from ankicli.app.errors import (
    BackendOperationUnsupportedError,
    BackendUnavailableError,
    CardNotFoundError,
    DeckNotFoundError,
    ModelNotFoundError,
    NoteNotFoundError,
    ValidationError,
)
from ankicli.app.models import IMPLEMENTED_BACKEND_OPERATIONS, BackendCapabilities
from ankicli.backends.base import BaseBackend


class AnkiConnectBackend(BaseBackend):
    name = "ankiconnect"

    def __init__(self, *, url: str | None = None, version: int = 5) -> None:
        self.url = url or os.environ.get("ANKICONNECT_URL", "http://127.0.0.1:8765")
        self.version = version

    def supported_operations(self) -> dict[str, bool]:
        supported = {operation: False for operation in IMPLEMENTED_BACKEND_OPERATIONS}
        for operation in (
            "doctor.backend",
            "doctor.capabilities",
            "backend.test_connection",
            "collection.info",
            "collection.stats",
            "deck.list",
            "deck.get",
            "deck.stats",
            "model.list",
            "model.get",
            "model.fields",
            "model.templates",
            "model.validate_note",
            "tag.list",
            "search.notes",
            "search.cards",
            "search.count",
            "search.preview",
            "export.notes",
            "export.cards",
            "import.notes",
            "import.patch",
            "note.get",
            "note.add",
            "note.update",
            "note.fields",
            "note.move_deck",
            "note.add_tags",
            "note.remove_tags",
            "card.get",
            "card.suspend",
            "card.unsuspend",
        ):
            supported[operation] = True
        return supported

    def _raise_unsupported(self, operation: str) -> None:
        raise BackendOperationUnsupportedError(
            f"{operation} is not supported by the ankiconnect backend",
            details={"backend": self.name, "operation": operation},
        )

    def backend_capabilities(self) -> BackendCapabilities:
        try:
            api_version = self._invoke("version")
        except BackendUnavailableError as exc:
            return BackendCapabilities(
                backend=self.name,
                available=False,
                supports_collection_reads=False,
                supports_collection_writes=False,
                supports_live_desktop=True,
                supported_operations=self.supported_operations(),
                notes=[str(exc)],
            )

        notes = [f"AnkiConnect API version {api_version} at {self.url}"]
        notes.append("Initial AnkiConnect slice excludes note delete.")
        notes.append("Collection-wide tag lifecycle commands are not implemented yet.")
        return BackendCapabilities(
            backend=self.name,
            available=True,
            supports_collection_reads=True,
            supports_collection_writes=True,
            supports_live_desktop=True,
            supported_operations=self.supported_operations(),
            notes=notes,
        )

    def auth_status(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("auth.status")

    def login(
        self,
        collection_path: Path | None,
        *,
        username: str,
        password: str,
        endpoint: str | None,
    ) -> SyncCredential:
        del collection_path, username, password, endpoint
        self._raise_unsupported("auth.login")

    def logout(self, collection_path: Path | None) -> dict:
        del collection_path
        self._raise_unsupported("auth.logout")

    def sync_status(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("sync.status")

    def sync_run(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("sync.run")

    def sync_pull(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("sync.pull")

    def sync_push(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("sync.push")

    def create_backup(
        self,
        collection_path: Path,
        *,
        backup_folder: Path,
        force: bool,
    ) -> dict:
        del collection_path, backup_folder, force
        self._raise_unsupported("backup.create")

    def restore_backup(
        self,
        collection_path: Path,
        *,
        backup_path: Path,
        media_folder: Path,
        media_db_path: Path,
    ) -> dict:
        del collection_path, backup_path, media_folder, media_db_path
        self._raise_unsupported("backup.restore")

    def _invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        payload = json.dumps(
            {
                "action": action,
                "version": self.version,
                "params": params or {},
            },
        ).encode()
        parsed = urlsplit(self.url)
        if parsed.scheme != "http" or not parsed.hostname:
            raise BackendUnavailableError(
                f"AnkiConnect backend URL is invalid: {self.url}",
                details={"url": self.url},
            )
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        try:
            connection = http.client.HTTPConnection(
                parsed.hostname,
                parsed.port or 80,
                timeout=5,
            )
            connection.request(
                "POST",
                path,
                body=payload,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            raw = response.read().decode()
        except OSError as exc:
            raise BackendUnavailableError(
                f"AnkiConnect backend is unavailable at {self.url}",
                details={"url": self.url, "reason": str(exc)},
            ) from exc
        finally:
            try:
                connection.close()
            except Exception:
                pass

        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BackendUnavailableError(
                "AnkiConnect returned invalid JSON",
                details={"url": self.url},
            ) from exc

        if decoded.get("error"):
            raise ValidationError(
                str(decoded["error"]),
                details={"action": action, "url": self.url},
            )
        return decoded.get("result")

    def _model_names(self) -> list[dict]:
        try:
            result = self._invoke("modelNamesAndIds")
        except ValidationError:
            names = self._invoke("modelNames")
            return [{"id": None, "name": str(name)} for name in names]
        return [{"id": int(model_id), "name": name} for name, model_id in result.items()]

    def _deck_items(self) -> list[dict]:
        result = self._invoke("deckNamesAndIds")
        return [
            {"id": int(deck_id), "name": name}
            for name, deck_id in sorted(result.items(), key=lambda item: item[0])
        ]

    def _deck_name_to_id(self) -> dict[str, int]:
        return {item["name"]: int(item["id"]) for item in self._deck_items()}

    def _model_field_names(self, name: str) -> list[str]:
        return [str(field) for field in self._invoke("modelFieldNames", {"modelName": name})]

    def get_collection_info(self, collection_path: Path) -> dict:
        del collection_path
        decks = self._deck_items()
        models = self._model_names()
        note_ids = self._invoke("findNotes", {"query": ""})
        card_ids = self._invoke("findCards", {"query": ""})
        return {
            "collection_path": None,
            "collection_name": "AnkiConnect",
            "exists": True,
            "backend_available": True,
            "note_count": len(note_ids),
            "card_count": len(card_ids),
            "deck_count": len(decks),
            "model_count": len(models),
            "ankiconnect_url": self.url,
            "ankiconnect_version": self._invoke("version"),
        }

    def list_decks(self, collection_path: Path) -> list[dict]:
        del collection_path
        return self._deck_items()

    def get_deck(self, collection_path: Path, *, name: str) -> dict:
        del collection_path
        for deck in self._deck_items():
            if deck["name"] == name:
                return deck
        raise DeckNotFoundError(f'Deck "{name}" was not found', details={"deck_name": name})

    def create_deck(self, collection_path: Path, *, name: str, dry_run: bool) -> dict:
        del collection_path, name, dry_run
        self._raise_unsupported("deck.create")

    def rename_deck(
        self,
        collection_path: Path,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
    ) -> dict:
        del collection_path, name, new_name, dry_run
        self._raise_unsupported("deck.rename")

    def delete_deck(self, collection_path: Path, *, name: str, dry_run: bool) -> dict:
        del collection_path, name, dry_run
        self._raise_unsupported("deck.delete")

    def reparent_deck(
        self,
        collection_path: Path,
        *,
        name: str,
        new_parent: str,
        dry_run: bool,
    ) -> dict:
        del collection_path, name, new_parent, dry_run
        self._raise_unsupported("deck.reparent")

    def list_models(self, collection_path: Path) -> list[dict]:
        del collection_path
        return self._model_names()

    def get_model(self, collection_path: Path, *, name: str) -> dict:
        del collection_path
        for model in self._model_names():
            if model["name"] == name:
                fields = self._model_field_names(name)
                return {
                    "id": model["id"],
                    "name": name,
                    "fields": fields,
                }
        raise ModelNotFoundError(f'Model "{name}" was not found', details={"model_name": name})

    def get_model_fields(self, collection_path: Path, *, name: str) -> dict:
        del collection_path
        for model in self._model_names():
            if model["name"] == name:
                return {
                    "id": model["id"],
                    "name": name,
                    "fields": self._model_field_names(name),
                }
        raise ModelNotFoundError(f'Model "{name}" was not found', details={"model_name": name})

    def get_model_templates(self, collection_path: Path, *, name: str) -> dict:
        del collection_path
        for model in self._model_names():
            if model["name"] == name:
                templates = self._invoke("modelTemplates", {"modelName": name})
                normalized = [{"name": str(template_name)} for template_name in templates.keys()]
                return {
                    "id": model["id"],
                    "name": name,
                    "templates": normalized,
                }
        raise ModelNotFoundError(f'Model "{name}" was not found', details={"model_name": name})

    def list_media(self, collection_path: Path) -> list[dict]:
        del collection_path
        self._raise_unsupported("media.list")

    def check_media(self, collection_path: Path) -> dict:
        del collection_path
        self._raise_unsupported("media.check")

    def list_orphaned_media(self, collection_path: Path) -> list[dict]:
        del collection_path
        self._raise_unsupported("media.orphaned")

    def attach_media(
        self,
        collection_path: Path,
        *,
        source_path: Path,
        name: str | None,
        dry_run: bool,
    ) -> dict:
        del collection_path, source_path, name, dry_run
        self._raise_unsupported("media.attach")

    def resolve_media_path(self, collection_path: Path, *, name: str) -> dict:
        del collection_path, name
        self._raise_unsupported("media.resolve_path")

    def list_tags(self, collection_path: Path) -> list[str]:
        del collection_path
        return [str(tag) for tag in self._invoke("getTags")]

    def rename_tag(
        self,
        collection_path: Path,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
    ) -> dict:
        del collection_path, name, new_name, dry_run
        self._raise_unsupported("tag.rename")

    def delete_tags(
        self,
        collection_path: Path,
        *,
        tags: list[str],
        dry_run: bool,
    ) -> dict:
        del collection_path, tags, dry_run
        self._raise_unsupported("tag.delete")

    def reparent_tags(
        self,
        collection_path: Path,
        *,
        tags: list[str],
        new_parent: str,
        dry_run: bool,
    ) -> dict:
        del collection_path, tags, new_parent, dry_run
        self._raise_unsupported("tag.reparent")

    def find_notes(
        self,
        collection_path: Path,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> dict:
        del collection_path
        note_ids = [int(note_id) for note_id in self._invoke("findNotes", {"query": query})]
        sliced_ids = note_ids[offset : offset + limit]
        return {
            "items": [{"id": note_id} for note_id in sliced_ids],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": len(note_ids),
        }

    def find_cards(
        self,
        collection_path: Path,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> dict:
        del collection_path
        card_ids = [int(card_id) for card_id in self._invoke("findCards", {"query": query})]
        sliced_ids = card_ids[offset : offset + limit]
        return {
            "items": [{"id": card_id} for card_id in sliced_ids],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": len(card_ids),
        }

    def get_note(self, collection_path: Path, note_id: int) -> dict:
        del collection_path
        notes = self._invoke("notesInfo", {"notes": [note_id]})
        if not notes:
            raise NoteNotFoundError(f"Note {note_id} was not found", details={"note_id": note_id})
        note = notes[0]
        fields = {
            str(name): str(value.get("value", ""))
            for name, value in note.get("fields", {}).items()
        }
        return {
            "id": int(note.get("noteId", note_id)),
            "model": str(note.get("modelName", "")),
            "fields": fields,
            "tags": [str(tag) for tag in note.get("tags", [])],
        }

    def get_note_fields(self, collection_path: Path, note_id: int) -> dict:
        note = self.get_note(collection_path, note_id)
        return {
            "id": note["id"],
            "model": note["model"],
            "fields": note["fields"],
        }

    def get_card(self, collection_path: Path, card_id: int) -> dict:
        del collection_path
        cards = self._invoke("cardsInfo", {"cards": [card_id]})
        if not cards:
            raise CardNotFoundError(f"Card {card_id} was not found", details={"card_id": card_id})
        card = cards[0]
        deck_id = self._deck_name_to_id().get(str(card.get("deckName", "")))
        template = card.get("template")
        if template is None and card.get("fieldOrder") is not None:
            template = f"Card {int(card['fieldOrder']) + 1}"
        return {
            "id": int(card.get("cardId", card_id)),
            "note_id": int(card.get("note")) if card.get("note") is not None else None,
            "deck_id": deck_id,
            "template": str(template or ""),
        }

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
        del collection_path
        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "tags": tags,
        }
        if dry_run:
            can_add = self._invoke("canAddNotes", {"notes": [note]})
            if not can_add or not can_add[0]:
                raise ValidationError(
                    "AnkiConnect rejected the candidate note for add",
                    details={"deck": deck_name, "model": model_name},
                )
            note_id = None
        else:
            note_id = self._invoke("addNote", {"note": note})
            if note_id is None:
                raise ValidationError(
                    "AnkiConnect failed to add the note",
                    details={"deck": deck_name, "model": model_name},
                )
        return {
            "id": int(note_id) if note_id is not None else None,
            "deck": deck_name,
            "model": model_name,
            "fields": fields,
            "tags": tags,
            "dry_run": dry_run,
        }

    def update_note(
        self,
        collection_path: Path,
        *,
        note_id: int,
        fields: dict[str, str],
        dry_run: bool,
    ) -> dict:
        del collection_path
        existing = self.get_note(Path("."), note_id)
        if not dry_run:
            self._invoke("updateNoteFields", {"note": {"id": note_id, "fields": fields}})
        return {
            "id": note_id,
            "model": existing["model"],
            "fields": dict(fields),
            "tags": existing["tags"],
            "dry_run": dry_run,
        }

    def delete_note(
        self,
        collection_path: Path,
        *,
        note_id: int,
        dry_run: bool,
    ) -> dict:
        del collection_path, note_id, dry_run
        self._raise_unsupported("note.delete")

    def move_note_to_deck(
        self,
        collection_path: Path,
        *,
        note_id: int,
        deck_name: str,
        dry_run: bool,
    ) -> dict:
        del collection_path
        note = self.get_note(Path("."), note_id)
        card_ids = [
            int(card_id)
            for card_id in self._invoke("findCards", {"query": f"nid:{note_id}"})
        ]
        deck_id = self._deck_name_to_id().get(deck_name)
        if deck_id is None:
            raise DeckNotFoundError(
                f'Deck "{deck_name}" was not found',
                details={"deck_name": deck_name},
            )
        if not dry_run:
            self._invoke("changeDeck", {"cards": card_ids, "deck": deck_name})
        return {
            "id": int(note["id"]),
            "deck": deck_name,
            "card_ids": card_ids,
            "action": "move_deck",
            "dry_run": dry_run,
        }

    def add_tags_to_notes(
        self,
        collection_path: Path,
        *,
        note_ids: list[int],
        tags: list[str],
        dry_run: bool,
    ) -> list[dict]:
        del collection_path
        normalized_ids = [int(note_id) for note_id in note_ids]
        for note_id in normalized_ids:
            self.get_note(Path("."), note_id)
        if not dry_run:
            self._invoke("addTags", {"notes": normalized_ids, "tags": " ".join(tags)})
        return [
            {"id": note_id, "tags": list(tags), "action": "add", "dry_run": dry_run}
            for note_id in normalized_ids
        ]

    def remove_tags_from_notes(
        self,
        collection_path: Path,
        *,
        note_ids: list[int],
        tags: list[str],
        dry_run: bool,
    ) -> list[dict]:
        del collection_path
        normalized_ids = [int(note_id) for note_id in note_ids]
        for note_id in normalized_ids:
            self.get_note(Path("."), note_id)
        if not dry_run:
            self._invoke("removeTags", {"notes": normalized_ids, "tags": " ".join(tags)})
        return [
            {"id": note_id, "tags": list(tags), "action": "remove", "dry_run": dry_run}
            for note_id in normalized_ids
        ]

    def suspend_cards(
        self,
        collection_path: Path,
        *,
        card_ids: list[int],
        dry_run: bool,
    ) -> list[dict]:
        del collection_path
        normalized_ids = [int(card_id) for card_id in card_ids]
        for card_id in normalized_ids:
            self.get_card(Path("."), card_id)
        if not dry_run:
            self._invoke("suspend", {"cards": normalized_ids})
        return [
            {"id": card_id, "suspended": True, "dry_run": dry_run}
            for card_id in normalized_ids
        ]

    def unsuspend_cards(
        self,
        collection_path: Path,
        *,
        card_ids: list[int],
        dry_run: bool,
    ) -> list[dict]:
        del collection_path
        normalized_ids = [int(card_id) for card_id in card_ids]
        for card_id in normalized_ids:
            self.get_card(Path("."), card_id)
        if not dry_run:
            self._invoke("unsuspend", {"cards": normalized_ids})
        return [
            {"id": card_id, "suspended": False, "dry_run": dry_run}
            for card_id in normalized_ids
        ]
