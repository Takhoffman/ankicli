"""Python-Anki backend."""

from __future__ import annotations

import importlib
import importlib.util
import re
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ankicli.app.errors import (
    AnkiCliError,
    BackendUnavailableError,
    CardNotFoundError,
    CollectionNotFoundError,
    CollectionOpenError,
    DeckNotFoundError,
    MediaNotFoundError,
    ModelNotFoundError,
    NoteNotFoundError,
    TagNotFoundError,
    ValidationError,
)
from ankicli.app.models import IMPLEMENTED_BACKEND_OPERATIONS, BackendCapabilities
from ankicli.backends.base import BaseBackend


class PythonAnkiBackend(BaseBackend):
    name = "python-anki"
    _MEDIA_REFERENCE_PATTERNS = (
        re.compile(r"\[sound:([^\]\r\n]+)\]"),
        re.compile(r"""<img\b[^>]*\bsrc=["']([^"']+)["']""", re.IGNORECASE),
    )

    def supported_operations(self) -> dict[str, bool]:
        available = importlib.util.find_spec("anki") is not None
        return {operation: available for operation in IMPLEMENTED_BACKEND_OPERATIONS}

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
            supported_operations=self.supported_operations(),
            notes=notes,
        )

    def _require_available(self) -> None:
        if not self.backend_capabilities().available:
            raise BackendUnavailableError("Python-Anki backend is unavailable in this environment")

    def _load_collection_type(self) -> type:
        self._require_available()
        module_candidates = ["anki.collection", "anki.storage"]
        for module_name in module_candidates:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue
            collection_type = getattr(module, "Collection", None)
            if collection_type is not None:
                return collection_type
        raise BackendUnavailableError(
            "Python-Anki Collection API is unavailable in this environment",
        )

    def _resolve_collection_path(self, collection_path: Path) -> Path:
        resolved_path = collection_path.expanduser().resolve()
        if not resolved_path.exists():
            raise CollectionNotFoundError(
                f"Collection path does not exist: {resolved_path}",
                details={"path": str(resolved_path)},
            )
        return resolved_path

    def _resolve_deck_id(self, collection: Any, deck_name: str) -> int:
        for deck in collection.decks.all_names_and_ids():
            if deck.name == deck_name:
                return int(deck.id)
        raise DeckNotFoundError(
            f'Deck "{deck_name}" was not found',
            details={"deck_name": deck_name},
        )

    def _get_deck_item(self, collection: Any, deck_name: str) -> Any:
        for deck in collection.decks.all_names_and_ids():
            if deck.name == deck_name:
                return deck
        raise DeckNotFoundError(
            f'Deck "{deck_name}" was not found',
            details={"deck_name": deck_name},
        )

    def _normalize_deck(self, deck: Any) -> dict:
        return {
            "id": int(deck.id),
            "name": deck.name,
        }

    def _get_decks_manager(self, collection: Any) -> Any:
        decks_manager = getattr(collection, "decks", None)
        if decks_manager is None:
            raise BackendUnavailableError(
                "Python-Anki deck API is unavailable in this environment",
            )
        return decks_manager

    def _create_deck_in_manager(self, decks_manager: Any, name: str) -> int:
        for method_name in ("id", "id_for_name", "add_normal_deck_with_name"):
            candidate = getattr(decks_manager, method_name, None)
            if not callable(candidate):
                continue
            created = candidate(name)
            if created is None:
                continue
            return int(created)
        raise BackendUnavailableError(
            "Python-Anki deck create API is unavailable in this environment",
        )

    def _rename_deck_in_manager(self, decks_manager: Any, deck: Any, new_name: str) -> None:
        rename_method = getattr(decks_manager, "rename", None)
        if not callable(rename_method):
            raise BackendUnavailableError(
                "Python-Anki deck rename API is unavailable in this environment",
            )
        for payload in (deck, int(deck.id)):
            try:
                rename_method(payload, new_name)
                return
            except TypeError:
                continue
        raise BackendUnavailableError(
            "Python-Anki deck rename API has an unsupported signature in this environment",
        )

    def _delete_deck_in_manager(self, decks_manager: Any, deck_id: int) -> None:
        for method_name in ("remove", "rem"):
            candidate = getattr(decks_manager, method_name, None)
            if not callable(candidate):
                continue
            try:
                candidate([deck_id], cards_too=False)
                return
            except TypeError:
                pass
            try:
                candidate(deck_id, cardsToo=False, childrenToo=True)
                return
            except TypeError:
                continue
        raise BackendUnavailableError(
            "Python-Anki deck delete API is unavailable in this environment",
        )

    def _resolve_model(self, collection: Any, model_name: str) -> Any:
        models = getattr(collection, "models", None)
        if models is None:
            raise ModelNotFoundError(
                f'Model "{model_name}" was not found',
                details={"model_name": model_name},
            )

        for method_name in ("by_name", "byName"):
            candidate = getattr(models, method_name, None)
            if candidate is not None:
                model = candidate(model_name)
                if model is not None:
                    return model

        model_id = None
        for model in models.all_names_and_ids():
            if model.name == model_name:
                model_id = int(model.id)
                break
        if model_id is None:
            raise ModelNotFoundError(
                f'Model "{model_name}" was not found',
                details={"model_name": model_name},
            )

        for method_name in ("get", "get_notetype", "getNotetype"):
            candidate = getattr(models, method_name, None)
            if candidate is not None:
                model = candidate(model_id)
                if model is not None:
                    return model

        raise ModelNotFoundError(
            f'Model "{model_name}" was not found',
            details={"model_name": model_name},
        )

    def _get_tags_manager(self, collection: Any) -> Any:
        tags_manager = getattr(collection, "tags", None)
        if tags_manager is None:
            raise BackendUnavailableError(
                "Python-Anki tag API is unavailable in this environment",
            )
        return tags_manager

    def _extract_model_fields(self, model: Any) -> list[str]:
        fields = []
        for field in model.get("flds", []):
            field_name = field.get("name")
            if field_name:
                fields.append(str(field_name))
        return fields

    def _extract_model_templates(self, model: Any) -> list[dict]:
        templates = []
        for template in model.get("tmpls", []):
            template_name = template.get("name")
            if not template_name:
                continue
            templates.append({"name": str(template_name)})
        return templates

    def _list_tags_from_manager(self, tags_manager: Any) -> list[str]:
        all_method = getattr(tags_manager, "all", None)
        if not callable(all_method):
            raise BackendUnavailableError(
                "Python-Anki tag list API is unavailable in this environment",
            )
        return sorted(str(tag) for tag in all_method())

    def _media_dir(self, collection_path: Path) -> Path:
        return self._resolve_collection_path(collection_path).with_suffix(".media")

    def _iter_media_files(self, media_dir: Path) -> list[Path]:
        if not media_dir.exists():
            return []
        return sorted(path for path in media_dir.rglob("*") if path.is_file())

    def _normalize_media_item(self, media_dir: Path, media_path: Path) -> dict:
        return {
            "name": media_path.relative_to(media_dir).as_posix(),
            "path": str(media_path.resolve()),
            "size": media_path.stat().st_size,
        }

    def _extract_media_references(self, field_value: Any) -> set[str]:
        references: set[str] = set()
        text = str(field_value or "")
        for pattern in self._MEDIA_REFERENCE_PATTERNS:
            for match in pattern.findall(text):
                normalized = str(match).strip()
                if normalized:
                    references.add(normalized)
        return references

    def _referenced_media_names(self, collection: Any) -> set[str]:
        references: set[str] = set()
        find_notes = getattr(collection, "find_notes", None) or getattr(
            collection,
            "findNotes",
            None,
        )
        if not callable(find_notes):
            raise BackendUnavailableError(
                "Python-Anki note search API is unavailable in this environment",
            )
        get_note = getattr(collection, "get_note", None) or getattr(collection, "getNote", None)
        if not callable(get_note):
            raise BackendUnavailableError(
                "Python-Anki note lookup API is unavailable in this environment",
            )
        for note_id in find_notes(""):
            note = get_note(int(note_id))
            if note is None or not hasattr(note, "items"):
                continue
            for _, value in note.items():
                references.update(self._extract_media_references(value))
        return references

    def _resolve_media_candidate(self, media_dir: Path, name: str) -> Path:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        candidate = (media_dir / normalized_name).resolve()
        try:
            candidate.relative_to(media_dir.resolve())
        except ValueError as exc:
            raise ValidationError(
                f'Invalid media name "{name}"',
                details={"name": name},
            ) from exc
        if not candidate.exists() or not candidate.is_file():
            raise MediaNotFoundError(
                f'Media file "{name}" was not found',
                details={"name": name, "media_dir": str(media_dir.resolve())},
            )
        return candidate

    def _resolve_media_attach_name(self, source_path: Path, name: str | None) -> str:
        normalized = (name or source_path.name).strip()
        if not normalized:
            raise ValidationError("Attached media must have a target name")
        return normalized

    def _require_existing_tags(self, tags_manager: Any, tags: list[str]) -> None:
        available_tags = {tag.lower(): tag for tag in self._list_tags_from_manager(tags_manager)}
        for tag in tags:
            if tag.lower() not in available_tags:
                raise TagNotFoundError(
                    f'Tag "{tag}" was not found',
                    details={"tag": tag},
                )

    @contextmanager
    def _open_collection(self, collection_path: Path) -> Iterator[Any]:
        resolved_path = self._resolve_collection_path(collection_path)

        collection_type = self._load_collection_type()
        collection: Any | None = None
        try:
            collection = collection_type(str(resolved_path))
            yield collection
        except AnkiCliError:
            raise
        except BackendUnavailableError:
            raise
        except Exception as exc:
            raise CollectionOpenError(
                f"Failed to open collection at {resolved_path}",
                details={
                    "path": str(resolved_path),
                    "reason": str(exc),
                    "exception_type": type(exc).__name__,
                },
            ) from exc
        finally:
            if collection is not None and hasattr(collection, "close"):
                collection.close()

    def get_collection_info(self, collection_path: Path) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            return {
                "collection_path": str(resolved_path),
                "collection_name": collection.name(),
                "exists": True,
                "backend_available": True,
                "note_count": int(collection.note_count()),
                "card_count": int(collection.card_count()),
                "deck_count": len(collection.decks.all_names_and_ids()),
                "model_count": len(collection.models.all_names_and_ids()),
            }

    def list_decks(self, collection_path: Path) -> list[dict]:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            return [self._normalize_deck(deck) for deck in collection.decks.all_names_and_ids()]

    def get_deck(self, collection_path: Path, *, name: str) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            return self._normalize_deck(self._get_deck_item(collection, name))

    def create_deck(self, collection_path: Path, *, name: str, dry_run: bool) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            existing_names = {deck.name for deck in collection.decks.all_names_and_ids()}
            if name in existing_names:
                raise ValidationError(
                    f'Deck "{name}" already exists',
                    details={"deck_name": name},
                )
            created_id = None
            if not dry_run:
                created_id = self._create_deck_in_manager(self._get_decks_manager(collection), name)
            return {
                "id": created_id,
                "name": name,
                "action": "create",
                "dry_run": dry_run,
            }

    def rename_deck(
        self,
        collection_path: Path,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
    ) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            deck = self._get_deck_item(collection, name)
            if not dry_run:
                self._rename_deck_in_manager(self._get_decks_manager(collection), deck, new_name)
            return {
                "id": int(deck.id),
                "name": name,
                "new_name": new_name,
                "action": "rename",
                "dry_run": dry_run,
            }

    def delete_deck(self, collection_path: Path, *, name: str, dry_run: bool) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            deck = self._get_deck_item(collection, name)
            if not dry_run:
                self._delete_deck_in_manager(self._get_decks_manager(collection), int(deck.id))
            return {
                "id": int(deck.id),
                "name": name,
                "action": "delete",
                "dry_run": dry_run,
            }

    def reparent_deck(
        self,
        collection_path: Path,
        *,
        name: str,
        new_parent: str,
        dry_run: bool,
    ) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            deck = self._get_deck_item(collection, name)
            if new_parent:
                self._get_deck_item(collection, new_parent)
                suffix = name.split("::")[-1]
                target_name = f"{new_parent}::{suffix}"
            else:
                target_name = name.split("::")[-1]
            if target_name == name:
                raise ValidationError(
                    "Deck reparent target must change the deck name",
                    details={"deck_name": name, "new_parent": new_parent},
                )
            if not dry_run:
                self._rename_deck_in_manager(self._get_decks_manager(collection), deck, target_name)
            return {
                "id": int(deck.id),
                "name": name,
                "new_parent": new_parent,
                "new_name": target_name,
                "action": "reparent",
                "dry_run": dry_run,
            }

    def list_models(self, collection_path: Path) -> list[dict]:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            return [
                {
                    "id": int(model.id),
                    "name": model.name,
                }
                for model in collection.models.all_names_and_ids()
            ]

    def get_model(self, collection_path: Path, *, name: str) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            model = self._resolve_model(collection, name)
            fields = self._extract_model_fields(model)
            return {
                "id": int(model.get("id")) if model.get("id") is not None else None,
                "name": str(model.get("name", "")),
                "fields": fields,
            }

    def get_model_fields(self, collection_path: Path, *, name: str) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            model = self._resolve_model(collection, name)
            return {
                "id": int(model.get("id")) if model.get("id") is not None else None,
                "name": str(model.get("name", "")),
                "fields": self._extract_model_fields(model),
            }

    def get_model_templates(self, collection_path: Path, *, name: str) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            model = self._resolve_model(collection, name)
            return {
                "id": int(model.get("id")) if model.get("id") is not None else None,
                "name": str(model.get("name", "")),
                "templates": self._extract_model_templates(model),
            }

    def list_media(self, collection_path: Path) -> list[dict]:
        media_dir = self._media_dir(collection_path)
        return [
            self._normalize_media_item(media_dir, path)
            for path in self._iter_media_files(media_dir)
        ]

    def check_media(self, collection_path: Path) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        media_dir = self._media_dir(resolved_path)
        files = self._iter_media_files(media_dir)
        with self._open_collection(resolved_path) as collection:
            referenced = self._referenced_media_names(collection)
        file_names = {path.relative_to(media_dir).as_posix() for path in files}
        orphaned = sorted(file_names - referenced)
        missing = sorted(referenced - file_names)
        return {
            "media_dir": str(media_dir.resolve()),
            "exists": media_dir.exists(),
            "file_count": len(files),
            "referenced_count": len(referenced),
            "orphaned_count": len(orphaned),
            "missing_count": len(missing),
            "warnings": [],
        }

    def attach_media(
        self,
        collection_path: Path,
        *,
        source_path: Path,
        name: str | None,
        dry_run: bool,
    ) -> dict:
        resolved_collection_path = self._resolve_collection_path(collection_path)
        resolved_source_path = source_path.expanduser().resolve()
        if not resolved_source_path.exists() or not resolved_source_path.is_file():
            raise MediaNotFoundError(
                f"Source media path does not exist: {resolved_source_path}",
                details={"path": str(resolved_source_path)},
            )
        media_dir = self._media_dir(resolved_collection_path)
        media_dir.mkdir(parents=True, exist_ok=True)
        target_name = self._resolve_media_attach_name(resolved_source_path, name)
        target_path = (media_dir / target_name).resolve()
        try:
            target_path.relative_to(media_dir.resolve())
        except ValueError as exc:
            raise ValidationError(
                f'Invalid media name "{target_name}"',
                details={"name": target_name},
            ) from exc
        if not dry_run:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resolved_source_path, target_path)
        return {
            "name": target_name,
            "source_path": str(resolved_source_path),
            "path": str(target_path),
            "size": resolved_source_path.stat().st_size,
            "action": "attach",
            "dry_run": dry_run,
        }

    def list_orphaned_media(self, collection_path: Path) -> list[dict]:
        resolved_path = self._resolve_collection_path(collection_path)
        media_dir = self._media_dir(resolved_path)
        files = self._iter_media_files(media_dir)
        with self._open_collection(resolved_path) as collection:
            referenced = self._referenced_media_names(collection)
        return [
            self._normalize_media_item(media_dir, path)
            for path in files
            if path.relative_to(media_dir).as_posix() not in referenced
        ]

    def resolve_media_path(self, collection_path: Path, *, name: str) -> dict:
        media_dir = self._media_dir(collection_path)
        candidate = self._resolve_media_candidate(media_dir, name)
        return self._normalize_media_item(media_dir, candidate)

    def list_tags(self, collection_path: Path) -> list[str]:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            return self._list_tags_from_manager(self._get_tags_manager(collection))

    def rename_tag(
        self,
        collection_path: Path,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
    ) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            tags_manager = self._get_tags_manager(collection)
            self._require_existing_tags(tags_manager, [name])
            if not dry_run:
                rename_method = getattr(tags_manager, "rename", None)
                if not callable(rename_method):
                    raise BackendUnavailableError(
                        "Python-Anki tag rename API is unavailable in this environment",
                    )
                rename_method(name, new_name)
            return {
                "name": name,
                "new_name": new_name,
                "action": "rename",
                "dry_run": dry_run,
            }

    def delete_tags(
        self,
        collection_path: Path,
        *,
        tags: list[str],
        dry_run: bool,
    ) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            tags_manager = self._get_tags_manager(collection)
            self._require_existing_tags(tags_manager, tags)
            if not dry_run:
                remove_method = getattr(tags_manager, "remove", None)
                if not callable(remove_method):
                    raise BackendUnavailableError(
                        "Python-Anki tag delete API is unavailable in this environment",
                    )
                remove_method(" ".join(tags))
            return {
                "tags": list(tags),
                "action": "delete",
                "dry_run": dry_run,
            }

    def reparent_tags(
        self,
        collection_path: Path,
        *,
        tags: list[str],
        new_parent: str,
        dry_run: bool,
    ) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            tags_manager = self._get_tags_manager(collection)
            self._require_existing_tags(tags_manager, tags)
            if new_parent:
                self._require_existing_tags(tags_manager, [new_parent])
            if not dry_run:
                reparent_method = getattr(tags_manager, "reparent", None)
                if not callable(reparent_method):
                    raise BackendUnavailableError(
                        "Python-Anki tag reparent API is unavailable in this environment",
                    )
                reparent_method(tags, new_parent)
            return {
                "tags": list(tags),
                "new_parent": new_parent,
                "action": "reparent",
                "dry_run": dry_run,
            }

    def find_notes(
        self,
        collection_path: Path,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            search_method = None
            for method_name in ("find_notes", "findNotes"):
                candidate = getattr(collection, method_name, None)
                if candidate is not None:
                    search_method = candidate
                    break
            if search_method is None:
                raise BackendUnavailableError(
                    "Python-Anki note search API is unavailable in this environment",
                )

            note_ids = [int(note_id) for note_id in search_method(query)]
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
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            search_method = None
            for method_name in ("find_cards", "findCards"):
                candidate = getattr(collection, method_name, None)
                if candidate is not None:
                    search_method = candidate
                    break
            if search_method is None:
                raise BackendUnavailableError(
                    "Python-Anki card search API is unavailable in this environment",
                )

            card_ids = [int(card_id) for card_id in search_method(query)]
            sliced_ids = card_ids[offset : offset + limit]
            return {
                "items": [{"id": card_id} for card_id in sliced_ids],
                "query": query,
                "limit": limit,
                "offset": offset,
                "total": len(card_ids),
            }

    def get_note(self, collection_path: Path, note_id: int) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            note = None
            for method_name in ("get_note", "getNote"):
                candidate = getattr(collection, method_name, None)
                if candidate is not None:
                    note = candidate(note_id)
                    break
            if note is None:
                raise NoteNotFoundError(
                    f"Note {note_id} was not found",
                    details={"note_id": note_id},
                )

            field_items = None
            for attribute_name in ("items",):
                candidate = getattr(note, attribute_name, None)
                if callable(candidate):
                    try:
                        field_items = candidate()
                        break
                    except Exception:
                        pass

            if field_items is None:
                fields_attr = getattr(note, "fields", None)
                if isinstance(fields_attr, dict):
                    field_items = fields_attr.items()
                else:
                    field_items = []

            fields = {str(name): value for name, value in field_items}
            note_type_name = ""
            note_type = getattr(note, "note_type", None)
            if callable(note_type):
                try:
                    note_type_result = note_type()
                except Exception:
                    note_type_result = None
                note_type_name = getattr(note_type_result, "get", lambda *_: "")("name", "")
            elif isinstance(note_type, dict):
                note_type_name = str(note_type.get("name", ""))

            tags = []
            tags_attr = getattr(note, "tags", None)
            if callable(tags_attr):
                try:
                    tags = [str(tag) for tag in tags_attr]
                except TypeError:
                    try:
                        tags = [str(tag) for tag in tags_attr()]
                    except Exception:
                        tags = []
            elif isinstance(tags_attr, list | tuple | set):
                tags = [str(tag) for tag in tags_attr]

            return {
                "id": int(note_id),
                "model": note_type_name,
                "fields": fields,
                "tags": tags,
            }

    def get_note_fields(self, collection_path: Path, note_id: int) -> dict:
        note = self.get_note(collection_path, note_id)
        return {
            "id": note["id"],
            "model": note["model"],
            "fields": note["fields"],
        }

    def get_card(self, collection_path: Path, card_id: int) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            card = None
            for method_name in ("get_card", "getCard"):
                candidate = getattr(collection, method_name, None)
                if candidate is not None:
                    card = candidate(card_id)
                    break
            if card is None:
                raise CardNotFoundError(
                    f"Card {card_id} was not found",
                    details={"card_id": card_id},
                )

            note_id = getattr(card, "nid", None)
            if note_id is None and hasattr(card, "note"):
                try:
                    note = card.note()
                except Exception:
                    note = None
                note_id = getattr(note, "id", None)

            deck_id = getattr(card, "did", None)
            template_name = ""
            template = getattr(card, "template", None)
            if callable(template):
                try:
                    template_result = template()
                except Exception:
                    template_result = None
                template_name = getattr(template_result, "get", lambda *_: "")("name", "")
            elif isinstance(template, dict):
                template_name = str(template.get("name", ""))

            return {
                "id": int(card_id),
                "note_id": int(note_id) if note_id is not None else None,
                "deck_id": int(deck_id) if deck_id is not None else None,
                "template": template_name,
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
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            deck_id = self._resolve_deck_id(collection, deck_name)
            model = self._resolve_model(collection, model_name)

            new_note = None
            for method_name in ("new_note", "newNote"):
                candidate = getattr(collection, method_name, None)
                if candidate is not None:
                    new_note = candidate(model)
                    break
            if new_note is None:
                raise BackendUnavailableError(
                    "Python-Anki new note API is unavailable in this environment",
                )

            for field_name, value in fields.items():
                new_note[field_name] = value

            for tag in tags:
                add_tag = getattr(new_note, "add_tag", None)
                if callable(add_tag):
                    add_tag(tag)
                else:
                    note_tags = getattr(new_note, "tags", None)
                    if isinstance(note_tags, list):
                        note_tags.append(tag)

            if not dry_run:
                add_note_method = None
                for method_name in ("add_note", "addNote"):
                    candidate = getattr(collection, method_name, None)
                    if candidate is not None:
                        add_note_method = candidate
                        break
                if add_note_method is None:
                    raise BackendUnavailableError(
                        "Python-Anki add note API is unavailable in this environment",
                    )
                add_note_method(new_note, deck_id)

            note_id = getattr(new_note, "id", None)
            if callable(note_id):
                try:
                    note_id = note_id()
                except Exception:
                    note_id = None

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
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            note = None
            for method_name in ("get_note", "getNote"):
                candidate = getattr(collection, method_name, None)
                if candidate is not None:
                    note = candidate(note_id)
                    break
            if note is None:
                raise NoteNotFoundError(
                    f"Note {note_id} was not found",
                    details={"note_id": note_id},
                )

            for field_name, value in fields.items():
                note[field_name] = value

            if not dry_run:
                flush_method = None
                for method_name in ("flush", "save"):
                    candidate = getattr(note, method_name, None)
                    if callable(candidate):
                        flush_method = candidate
                        break
                if flush_method is None:
                    raise BackendUnavailableError(
                        "Python-Anki note update API is unavailable in this environment",
                    )
                flush_method()

            note_type_name = ""
            note_type = getattr(note, "note_type", None)
            if callable(note_type):
                try:
                    note_type_result = note_type()
                except Exception:
                    note_type_result = None
                note_type_name = getattr(note_type_result, "get", lambda *_: "")("name", "")
            elif isinstance(note_type, dict):
                note_type_name = str(note_type.get("name", ""))

            tags = []
            tags_attr = getattr(note, "tags", None)
            if callable(tags_attr):
                try:
                    tags = [str(tag) for tag in tags_attr]
                except TypeError:
                    try:
                        tags = [str(tag) for tag in tags_attr()]
                    except Exception:
                        tags = []
            elif isinstance(tags_attr, list | tuple | set):
                tags = [str(tag) for tag in tags_attr]

            return {
                "id": int(note_id),
                "model": note_type_name,
                "fields": dict(fields),
                "tags": tags,
                "dry_run": dry_run,
            }

    def delete_note(
        self,
        collection_path: Path,
        *,
        note_id: int,
        dry_run: bool,
    ) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            note = None
            for method_name in ("get_note", "getNote"):
                candidate = getattr(collection, method_name, None)
                if candidate is not None:
                    note = candidate(note_id)
                    break
            if note is None:
                raise NoteNotFoundError(
                    f"Note {note_id} was not found",
                    details={"note_id": note_id},
                )

            if not dry_run:
                delete_method = None
                delete_arg = [note_id]
                for method_name, arg in (
                    ("remove_notes", [note_id]),
                    ("removeNotes", [note_id]),
                    ("remNotes", [note_id]),
                    ("remove_note", note_id),
                    ("removeNote", note_id),
                ):
                    candidate = getattr(collection, method_name, None)
                    if candidate is not None:
                        delete_method = candidate
                        delete_arg = arg
                        break
                if delete_method is None:
                    raise BackendUnavailableError(
                        "Python-Anki note delete API is unavailable in this environment",
                    )
                delete_method(delete_arg)

            return {
                "id": int(note_id),
                "deleted": not dry_run,
                "dry_run": dry_run,
            }

    def move_note_to_deck(
        self,
        collection_path: Path,
        *,
        note_id: int,
        deck_name: str,
        dry_run: bool,
    ) -> dict:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            note = None
            for method_name in ("get_note", "getNote"):
                candidate = getattr(collection, method_name, None)
                if candidate is not None:
                    note = candidate(note_id)
                    break
            if note is None:
                raise NoteNotFoundError(
                    f"Note {note_id} was not found",
                    details={"note_id": note_id},
                )

            deck_id = self._resolve_deck_id(collection, deck_name)
            card_ids: list[int] = []
            cards_method = getattr(note, "cards", None)
            if callable(cards_method):
                try:
                    card_ids = [int(card.id) for card in cards_method()]
                except Exception:
                    card_ids = []
            if not card_ids:
                for method_name in ("find_cards", "findCards"):
                    candidate = getattr(collection, method_name, None)
                    if candidate is not None:
                        try:
                            card_ids = [int(card_id) for card_id in candidate(f"nid:{note_id}")]
                        except Exception:
                            card_ids = []
                        break
            if not card_ids:
                raise BackendUnavailableError(
                    "Python-Anki note move-deck API could not resolve cards for the note",
                )

            if not dry_run:
                change_method = None
                for method_name in ("set_deck", "setDeck"):
                    candidate = getattr(collection, method_name, None)
                    if callable(candidate):
                        change_method = candidate
                        break
                if change_method is None:
                    scheduler = getattr(collection, "sched", None)
                    for method_name in ("set_deck", "setDeck"):
                        candidate = getattr(scheduler, method_name, None)
                        if callable(candidate):
                            change_method = candidate
                            break
                if change_method is None:
                    raise BackendUnavailableError(
                        "Python-Anki move deck API is unavailable in this environment",
                    )
                change_method(card_ids, deck_id)

            return {
                "id": int(note_id),
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
        return self._set_note_tags(
            collection_path,
            note_ids=note_ids,
            tags=tags,
            action="add",
            dry_run=dry_run,
        )

    def remove_tags_from_notes(
        self,
        collection_path: Path,
        *,
        note_ids: list[int],
        tags: list[str],
        dry_run: bool,
    ) -> list[dict]:
        return self._set_note_tags(
            collection_path,
            note_ids=note_ids,
            tags=tags,
            action="remove",
            dry_run=dry_run,
        )

    def _set_note_tags(
        self,
        collection_path: Path,
        *,
        note_ids: list[int],
        tags: list[str],
        action: str,
        dry_run: bool,
    ) -> list[dict]:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            normalized_ids = [int(note_id) for note_id in note_ids]
            for note_id in normalized_ids:
                note = None
                for method_name in ("get_note", "getNote"):
                    candidate = getattr(collection, method_name, None)
                    if candidate is not None:
                        note = candidate(note_id)
                        break
                if note is None:
                    raise NoteNotFoundError(
                        f"Note {note_id} was not found",
                        details={"note_id": note_id},
                    )

            if not dry_run:
                tags_manager = self._get_tags_manager(collection)
                if action == "add":
                    method = getattr(tags_manager, "bulk_add", None)
                    unavailable_message = (
                        "Python-Anki note tag add API is unavailable in this environment"
                    )
                else:
                    method = getattr(tags_manager, "bulk_remove", None)
                    unavailable_message = (
                        "Python-Anki note tag remove API is unavailable in this environment"
                    )
                if not callable(method):
                    raise BackendUnavailableError(unavailable_message)
                method(normalized_ids, " ".join(tags))

            return [
                {
                    "id": note_id,
                    "tags": list(tags),
                    "action": action,
                    "dry_run": dry_run,
                }
                for note_id in normalized_ids
            ]

    def suspend_cards(
        self,
        collection_path: Path,
        *,
        card_ids: list[int],
        dry_run: bool,
    ) -> list[dict]:
        return self._set_card_suspended_state(
            collection_path,
            card_ids=card_ids,
            suspended=True,
            dry_run=dry_run,
        )

    def unsuspend_cards(
        self,
        collection_path: Path,
        *,
        card_ids: list[int],
        dry_run: bool,
    ) -> list[dict]:
        return self._set_card_suspended_state(
            collection_path,
            card_ids=card_ids,
            suspended=False,
            dry_run=dry_run,
        )

    def _set_card_suspended_state(
        self,
        collection_path: Path,
        *,
        card_ids: list[int],
        suspended: bool,
        dry_run: bool,
    ) -> list[dict]:
        resolved_path = self._resolve_collection_path(collection_path)
        with self._open_collection(resolved_path) as collection:
            normalized_ids = [int(card_id) for card_id in card_ids]
            for card_id in normalized_ids:
                card = None
                for method_name in ("get_card", "getCard"):
                    candidate = getattr(collection, method_name, None)
                    if candidate is not None:
                        card = candidate(card_id)
                        break
                if card is None:
                    raise CardNotFoundError(
                        f"Card {card_id} was not found",
                        details={"card_id": card_id},
                    )

            if not dry_run:
                if suspended:
                    method_names = ("suspend_cards", "suspendCards")
                    unavailable_message = (
                        "Python-Anki suspend cards API is unavailable in this environment"
                    )
                else:
                    method_names = ("unsuspend_cards", "unsuspendCards")
                    unavailable_message = (
                        "Python-Anki unsuspend cards API is unavailable in this environment"
                    )

                action_method = None
                for method_name in method_names:
                    candidate = getattr(collection, method_name, None)
                    if candidate is not None:
                        action_method = candidate
                        break
                if action_method is None:
                    raise BackendUnavailableError(unavailable_message)
                action_method(normalized_ids)

            return [
                {
                    "id": card_id,
                    "suspended": suspended,
                    "dry_run": dry_run,
                }
                for card_id in normalized_ids
            ]
