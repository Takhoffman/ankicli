"""Services used by the CLI."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
from pathlib import Path

from ankicli.app.errors import (
    BackendOperationUnsupportedError,
    CollectionRequiredError,
    NotImplementedYetError,
    UnsafeOperationError,
    ValidationError,
)
from ankicli.backends.base import BaseBackend
from ankicli.runtime import configure_anki_source_path


def _resolve_collection_arg(
    backend: BaseBackend,
    collection_path: str | None,
    *,
    command_name: str,
) -> Path:
    if collection_path:
        return Path(collection_path)
    if backend.name == "ankiconnect":
        return Path(".")
    raise CollectionRequiredError(f"A collection path is required for {command_name}")


def _parse_field_assignments(assignments: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for assignment in assignments:
        if "=" not in assignment:
            raise ValidationError(f"Invalid --field assignment: {assignment}")
        name, value = assignment.split("=", 1)
        name = name.strip()
        if not name:
            raise ValidationError(f"Invalid --field assignment: {assignment}")
        parsed[name] = value
    return parsed


class DoctorService:
    """Environment and capability diagnostics."""

    def env_report(self) -> dict:
        configured_source_path = configure_anki_source_path()
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "anki_source_path": os.environ.get("ANKI_SOURCE_PATH"),
            "anki_source_import_path": configured_source_path,
            "anki_import_available": importlib.util.find_spec("anki") is not None,
            "ankiconnect_url": os.environ.get("ANKICONNECT_URL", "http://127.0.0.1:8765"),
        }

    def backend_report(self, backend: BaseBackend) -> dict:
        capabilities = backend.backend_capabilities()
        supported_count = sum(
            1 for supported in capabilities.supported_operations.values() if supported
        )
        return {
            "name": backend.name,
            "available": capabilities.available,
            "supports_live_desktop": capabilities.supports_live_desktop,
            "supported_operation_count": supported_count,
            "unsupported_operation_count": len(capabilities.supported_operations) - supported_count,
            "ankiconnect_url": os.environ.get("ANKICONNECT_URL", "http://127.0.0.1:8765")
            if backend.name == "ankiconnect"
            else None,
            "anki_source_path": os.environ.get("ANKI_SOURCE_PATH")
            if backend.name == "python-anki"
            else None,
            "notes": capabilities.notes,
        }

    def capabilities_report(self, backend: BaseBackend) -> dict:
        capabilities = backend.backend_capabilities().model_dump()
        supported = capabilities["supported_operations"]
        capabilities["supported_operation_count"] = sum(
            1 for value in supported.values() if value
        )
        capabilities["unsupported_operation_count"] = sum(
            1 for value in supported.values() if not value
        )
        return capabilities

    def collection_report(self, backend: BaseBackend, collection_path: str | None) -> dict:
        if backend.name == "ankiconnect":
            raise BackendOperationUnsupportedError(
                "doctor.collection is not supported by the ankiconnect backend",
                details={"backend": backend.name, "operation": "doctor.collection"},
            )
        collection_service = CollectionService(backend)
        stats = collection_service.stats(collection_path)
        validation = collection_service.validate(collection_path)
        lock_status = collection_service.lock_status(collection_path)
        return {
            "stats": stats,
            "validation": validation,
            "lock_status": lock_status,
        }

    def safety_report(self, backend: BaseBackend, collection_path: str | None) -> dict:
        if backend.name == "ankiconnect":
            raise BackendOperationUnsupportedError(
                "doctor.safety is not supported by the ankiconnect backend",
                details={"backend": backend.name, "operation": "doctor.safety"},
            )
        collection_service = CollectionService(backend)
        validation = collection_service.validate(collection_path)
        lock_status = collection_service.lock_status(collection_path)
        warnings = list(validation["warnings"])
        if lock_status["status"] != "not-detected":
            warnings.append(f"collection lock status is {lock_status['status']}")
        return {
            "ok": validation["ok"] and lock_status["status"] in {"not-detected", "unknown"},
            "collection_path": validation["collection_path"],
            "safe_for_writes": validation["ok"] and lock_status["status"] == "not-detected",
            "warnings": warnings,
            "errors": validation["errors"],
            "lock_status": lock_status,
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

    def test_connection(self) -> dict:
        capabilities = self.backend.backend_capabilities()
        return {
            "name": self.backend.name,
            "ok": capabilities.available,
            "available": capabilities.available,
            "notes": capabilities.notes,
        }


class CollectionService:
    """Collection-related operations."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def info(self, collection_path: str | None) -> dict:
        return self.backend.get_collection_info(
            _resolve_collection_arg(
                self.backend,
                collection_path,
                command_name="collection info",
            ),
        )

    def stats(self, collection_path: str | None) -> dict:
        info = self.info(collection_path)
        return {
            "collection_name": info["collection_name"],
            "note_count": info["note_count"],
            "card_count": info["card_count"],
            "deck_count": info["deck_count"],
            "model_count": info["model_count"],
        }

    def validate(self, collection_path: str | None) -> dict:
        path = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="collection validate",
        )
        checks: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []
        if self.backend.name == "ankiconnect":
            raise BackendOperationUnsupportedError(
                "collection.validate is not supported by the ankiconnect backend",
                details={"backend": self.backend.name, "operation": "collection.validate"},
            )

        resolved = path.expanduser().resolve()
        if resolved.exists():
            checks.append("collection path exists")
        else:
            errors.append(f"collection path does not exist: {resolved}")
        capabilities = self.backend.backend_capabilities()
        if capabilities.available:
            checks.append("backend is available")
        else:
            errors.extend(capabilities.notes or ["backend is unavailable"])
        if not errors:
            self.info(str(resolved))
            checks.append("collection opened successfully")
        return {
            "ok": not errors,
            "collection_path": str(resolved),
            "checks": checks,
            "warnings": warnings,
            "errors": errors,
        }

    def lock_status(self, collection_path: str | None) -> dict:
        path = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="collection lock-status",
        )
        if self.backend.name == "ankiconnect":
            raise BackendOperationUnsupportedError(
                "collection.lock_status is not supported by the ankiconnect backend",
                details={"backend": self.backend.name, "operation": "collection.lock_status"},
            )

        resolved = path.expanduser().resolve()
        sibling_candidates = [
            resolved.with_name(f"{resolved.name}-wal"),
            resolved.with_name(f"{resolved.name}-shm"),
        ]
        detected_files = [str(candidate) for candidate in sibling_candidates if candidate.exists()]
        status = "possibly-open" if detected_files else "not-detected"
        return {
            "collection_path": str(resolved),
            "status": status,
            "detected_files": detected_files,
            "confidence": "low" if detected_files else "best-effort",
        }


class CatalogService:
    """Deck, model, and tag services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def list_decks(self, collection_path: str | None) -> dict:
        return {
            "items": self.backend.list_decks(
                _resolve_collection_arg(self.backend, collection_path, command_name="deck list"),
            ),
        }

    def get_deck(self, collection_path: str | None, *, name: str) -> dict:
        return self.backend.get_deck(
            _resolve_collection_arg(self.backend, collection_path, command_name="deck get"),
            name=name,
        )

    def deck_stats(self, collection_path: str | None, *, name: str) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="deck stats")
        deck = self.backend.get_deck(path, name=name)
        note_query = f'deck:"{name}"'
        note_result = self.backend.find_notes(path, note_query, limit=1, offset=0)
        card_result = self.backend.find_cards(path, note_query, limit=1, offset=0)
        return {
            "id": deck["id"],
            "name": deck["name"],
            "note_count": note_result["total"],
            "card_count": card_result["total"],
        }

    def list_models(self, collection_path: str | None) -> dict:
        return {
            "items": self.backend.list_models(
                _resolve_collection_arg(self.backend, collection_path, command_name="model list"),
            ),
        }

    def get_model(self, collection_path: str | None, *, name: str) -> dict:
        return self.backend.get_model(
            _resolve_collection_arg(self.backend, collection_path, command_name="model get"),
            name=name,
        )

    def get_model_fields(self, collection_path: str | None, *, name: str) -> dict:
        return self.backend.get_model_fields(
            _resolve_collection_arg(self.backend, collection_path, command_name="model fields"),
            name=name,
        )

    def get_model_templates(self, collection_path: str | None, *, name: str) -> dict:
        return self.backend.get_model_templates(
            _resolve_collection_arg(
                self.backend,
                collection_path,
                command_name="model templates",
            ),
            name=name,
        )

    def validate_note(
        self,
        collection_path: str | None,
        *,
        model_name: str,
        field_assignments: list[str],
    ) -> dict:
        fields = _parse_field_assignments(field_assignments)
        if not fields:
            raise ValidationError("At least one --field Name=Value assignment is required")
        model = self.get_model_fields(collection_path, name=model_name)
        known_fields = set(model["fields"])
        provided_fields = set(fields)
        missing_fields = sorted(field for field in known_fields if field not in provided_fields)
        unknown_fields = sorted(field for field in provided_fields if field not in known_fields)
        checks: list[str] = []
        errors: list[str] = []
        if not missing_fields:
            checks.append("all model fields are present")
        if not unknown_fields:
            checks.append("no unknown fields were provided")
        if missing_fields:
            errors.append(f"missing fields: {', '.join(missing_fields)}")
        if unknown_fields:
            errors.append(f"unknown fields: {', '.join(unknown_fields)}")
        return {
            "model": model_name,
            "ok": not errors,
            "fields": fields,
            "missing_fields": missing_fields,
            "unknown_fields": unknown_fields,
            "checks": checks,
            "errors": errors,
        }

    def list_tags(self, collection_path: str | None) -> dict:
        return {
            "items": self.backend.list_tags(
                _resolve_collection_arg(self.backend, collection_path, command_name="tag list"),
            ),
        }


class MediaService:
    """Media inspection services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def list(self, collection_path: str | None) -> dict:
        return {
            "items": self.backend.list_media(
                _resolve_collection_arg(self.backend, collection_path, command_name="media list"),
            ),
        }

    def check(self, collection_path: str | None) -> dict:
        return self.backend.check_media(
            _resolve_collection_arg(self.backend, collection_path, command_name="media check"),
        )

    def attach(
        self,
        collection_path: str | None,
        *,
        source_path: str,
        name: str | None,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        normalized_source = source_path.strip()
        if not normalized_source:
            raise ValidationError("--source must not be empty")
        normalized_name = name.strip() if name is not None else None
        if normalized_name == "":
            raise ValidationError("--name must not be empty")
        if not dry_run and not yes:
            raise UnsafeOperationError("media attach requires --yes or --dry-run")
        return self.backend.attach_media(
            _resolve_collection_arg(self.backend, collection_path, command_name="media attach"),
            source_path=Path(normalized_source),
            name=normalized_name,
            dry_run=dry_run,
        )

    def orphaned(self, collection_path: str | None) -> dict:
        return {
            "items": self.backend.list_orphaned_media(
                _resolve_collection_arg(
                    self.backend,
                    collection_path,
                    command_name="media orphaned",
                ),
            ),
        }

    def resolve_path(self, collection_path: str | None, *, name: str) -> dict:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        return self.backend.resolve_media_path(
            _resolve_collection_arg(
                self.backend,
                collection_path,
                command_name="media resolve-path",
            ),
            name=normalized_name,
        )


class TagService:
    """Tag services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def rename(
        self,
        collection_path: str | None,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        if not collection_path:
            path = _resolve_collection_arg(self.backend, collection_path, command_name="tag rename")
        else:
            path = Path(collection_path)
        normalized_name = name.strip()
        normalized_new_name = new_name.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        if not normalized_new_name:
            raise ValidationError("--to must not be empty")
        if normalized_name == normalized_new_name:
            raise ValidationError("--to must differ from --name")
        if not dry_run and not yes:
            raise UnsafeOperationError("tag rename requires --yes or --dry-run")
        return self.backend.rename_tag(
            path,
            name=normalized_name,
            new_name=normalized_new_name,
            dry_run=dry_run,
        )

    def delete(
        self,
        collection_path: str | None,
        *,
        tags: list[str],
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="tag delete")
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("tag delete requires --yes or --dry-run")
        return self.backend.delete_tags(
            path,
            tags=normalized_tags,
            dry_run=dry_run,
        )

    def reparent(
        self,
        collection_path: str | None,
        *,
        tags: list[str],
        new_parent: str,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="tag reparent")
        normalized_tags = self._parse_tags(tags)
        normalized_parent = new_parent.strip()
        if any(tag == normalized_parent for tag in normalized_tags if normalized_parent):
            raise ValidationError("--to-parent must differ from the moved tag names")
        if not dry_run and not yes:
            raise UnsafeOperationError("tag reparent requires --yes or --dry-run")
        return self.backend.reparent_tags(
            path,
            tags=normalized_tags,
            new_parent=normalized_parent,
            dry_run=dry_run,
        )

    def apply(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        tags: list[str],
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="tag apply")
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("tag apply requires --yes or --dry-run")
        return self.backend.add_tags_to_notes(
            path,
            note_ids=[note_id],
            tags=normalized_tags,
            dry_run=dry_run,
        )[0]

    def remove(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        tags: list[str],
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="tag remove")
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("tag remove requires --yes or --dry-run")
        return self.backend.remove_tags_from_notes(
            path,
            note_ids=[note_id],
            tags=normalized_tags,
            dry_run=dry_run,
        )[0]

    def _parse_tags(self, tags: list[str]) -> list[str]:
        normalized = [tag.strip() for tag in tags if tag.strip()]
        if not normalized:
            raise ValidationError("At least one --tag value is required")
        return normalized


class DeckService:
    """Deck lifecycle services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def create(
        self,
        collection_path: str | None,
        *,
        name: str,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="deck create")
        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        if not dry_run and not yes:
            raise UnsafeOperationError("deck create requires --yes or --dry-run")
        return self.backend.create_deck(path, name=normalized_name, dry_run=dry_run)

    def rename(
        self,
        collection_path: str | None,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="deck rename")
        normalized_name = name.strip()
        normalized_new_name = new_name.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        if not normalized_new_name:
            raise ValidationError("--to must not be empty")
        if normalized_name == normalized_new_name:
            raise ValidationError("--to must differ from --name")
        if not dry_run and not yes:
            raise UnsafeOperationError("deck rename requires --yes or --dry-run")
        return self.backend.rename_deck(
            path,
            name=normalized_name,
            new_name=normalized_new_name,
            dry_run=dry_run,
        )

    def delete(
        self,
        collection_path: str | None,
        *,
        name: str,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="deck delete")
        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        if not dry_run and not yes:
            raise UnsafeOperationError("deck delete requires --yes or --dry-run")
        return self.backend.delete_deck(path, name=normalized_name, dry_run=dry_run)

    def reparent(
        self,
        collection_path: str | None,
        *,
        name: str,
        new_parent: str,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="deck reparent")
        normalized_name = name.strip()
        normalized_parent = new_parent.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        if normalized_parent and normalized_parent == normalized_name:
            raise ValidationError("--to-parent must differ from --name")
        if not dry_run and not yes:
            raise UnsafeOperationError("deck reparent requires --yes or --dry-run")
        return self.backend.reparent_deck(
            path,
            name=normalized_name,
            new_parent=normalized_parent,
            dry_run=dry_run,
        )


class SearchService:
    """Search services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def find_notes(
        self,
        collection_path: str | None,
        *,
        query: str,
        limit: int,
        offset: int,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="search notes")
        return self.backend.find_notes(
            path,
            query,
            limit=limit,
            offset=offset,
        )

    def find_cards(
        self,
        collection_path: str | None,
        *,
        query: str,
        limit: int,
        offset: int,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="search cards")
        return self.backend.find_cards(
            path,
            query,
            limit=limit,
            offset=offset,
        )

    def count(
        self,
        collection_path: str | None,
        *,
        kind: str,
        query: str,
    ) -> dict:
        if kind == "notes":
            result = self.find_notes(collection_path, query=query, limit=1, offset=0)
        else:
            result = self.find_cards(collection_path, query=query, limit=1, offset=0)
        return {
            "kind": kind,
            "query": query,
            "total": result["total"],
        }

    def preview(
        self,
        collection_path: str | None,
        *,
        kind: str,
        query: str,
        limit: int,
        offset: int,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="search preview")
        if kind == "notes":
            result = self.backend.find_notes(path, query, limit=limit, offset=offset)
            items = [self.backend.get_note(path, int(item["id"])) for item in result["items"]]
        else:
            result = self.backend.find_cards(path, query, limit=limit, offset=offset)
            items = [self.backend.get_card(path, int(item["id"])) for item in result["items"]]
        return {
            "kind": kind,
            "items": items,
            "query": result["query"],
            "limit": result["limit"],
            "offset": result["offset"],
            "total": result["total"],
        }


class ExportService:
    """Export helpers."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def export_notes(
        self,
        collection_path: str | None,
        *,
        query: str,
        limit: int,
        offset: int,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="export notes")
        search_result = self.backend.find_notes(path, query, limit=limit, offset=offset)
        items = [
            self.backend.get_note(path, int(item["id"]))
            for item in search_result["items"]
        ]
        return {
            "items": items,
            "query": search_result["query"],
            "limit": search_result["limit"],
            "offset": search_result["offset"],
            "total": search_result["total"],
        }

    def export_cards(
        self,
        collection_path: str | None,
        *,
        query: str,
        limit: int,
        offset: int,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="export cards")
        search_result = self.backend.find_cards(path, query, limit=limit, offset=offset)
        items = [
            self.backend.get_card(path, int(item["id"]))
            for item in search_result["items"]
        ]
        return {
            "items": items,
            "query": search_result["query"],
            "limit": search_result["limit"],
            "offset": search_result["offset"],
            "total": search_result["total"],
        }


class ImportService:
    """Import helpers."""

    def __init__(self, backend: BaseBackend, *, stdin_reader=None) -> None:
        self.backend = backend
        self.stdin_reader = stdin_reader or sys.stdin.read

    def _load_payload(
        self,
        *,
        input_path: str | None,
        stdin_json: bool,
        command_name: str,
        empty_message: str,
    ) -> tuple[object, str]:
        if stdin_json == bool(input_path):
            raise ValidationError(f"{command_name} requires exactly one of --input or --stdin-json")

        if stdin_json:
            raw = self.stdin_reader()
            if not raw.strip():
                raise ValidationError(empty_message)
            try:
                return json.loads(raw), "stdin"
            except json.JSONDecodeError as exc:
                raise ValidationError("Invalid JSON provided on stdin") from exc

        assert input_path is not None
        path = Path(input_path).expanduser()
        if not path.exists():
            raise ValidationError(f"Import input path does not exist: {path}")

        try:
            return json.loads(path.read_text()), str(path.resolve())
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSON in import file: {path}") from exc

    def import_notes(
        self,
        collection_path: str | None,
        *,
        input_path: str | None,
        stdin_json: bool,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        collection = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="import notes",
        )
        if not dry_run and not yes:
            raise UnsafeOperationError("import notes requires --yes or --dry-run")
        payload, source = self._load_payload(
            input_path=input_path,
            stdin_json=stdin_json,
            command_name="import notes",
            empty_message="No JSON was provided on stdin",
        )

        items = payload["items"] if isinstance(payload, dict) else payload
        if not isinstance(items, list) or not items:
            raise ValidationError(
                "Import payload must be a non-empty list or an object with an items list",
            )

        imported_items = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValidationError(f"Import item {index} must be an object")
            deck_name = item.get("deck")
            model_name = item.get("model")
            fields = item.get("fields")
            tags = item.get("tags", [])
            if not isinstance(deck_name, str) or not deck_name.strip():
                raise ValidationError(f"Import item {index} is missing a valid deck")
            if not isinstance(model_name, str) or not model_name.strip():
                raise ValidationError(f"Import item {index} is missing a valid model")
            if not isinstance(fields, dict) or not fields:
                raise ValidationError(f"Import item {index} is missing a valid fields object")
            if not isinstance(tags, list):
                raise ValidationError(f"Import item {index} tags must be a list")

            normalized_fields: dict[str, str] = {}
            for name, value in fields.items():
                if not isinstance(name, str) or not name.strip():
                    raise ValidationError(f"Import item {index} has an invalid field name")
                normalized_fields[name] = "" if value is None else str(value)

            normalized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
            imported_items.append(
                self.backend.add_note(
                    collection,
                    deck_name=deck_name.strip(),
                    model_name=model_name.strip(),
                    fields=normalized_fields,
                    tags=normalized_tags,
                    dry_run=dry_run,
                ),
            )

        return {
            "items": imported_items,
            "count": len(imported_items),
            "dry_run": dry_run,
            "source": source,
        }

    def import_patch(
        self,
        collection_path: str | None,
        *,
        input_path: str | None,
        stdin_json: bool,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        collection = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="import patch",
        )
        if not dry_run and not yes:
            raise UnsafeOperationError("import patch requires --yes or --dry-run")
        payload, source = self._load_payload(
            input_path=input_path,
            stdin_json=stdin_json,
            command_name="import patch",
            empty_message="No JSON patch payload was provided on stdin",
        )

        items = payload["items"] if isinstance(payload, dict) else payload
        if not isinstance(items, list) or not items:
            raise ValidationError(
                "Patch payload must be a non-empty list or an object with an items list",
            )

        patched_items = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValidationError(f"Patch item {index} must be an object")
            note_id = item.get("id")
            fields = item.get("fields")
            if not isinstance(note_id, int):
                raise ValidationError(f"Patch item {index} is missing a valid integer id")
            if not isinstance(fields, dict) or not fields:
                raise ValidationError(f"Patch item {index} is missing a valid fields object")

            normalized_fields: dict[str, str] = {}
            for name, value in fields.items():
                if not isinstance(name, str) or not name.strip():
                    raise ValidationError(f"Patch item {index} has an invalid field name")
                normalized_fields[name] = "" if value is None else str(value)

            patched_items.append(
                self.backend.update_note(
                    collection,
                    note_id=note_id,
                    fields=normalized_fields,
                    dry_run=dry_run,
                ),
            )

        return {
            "items": patched_items,
            "count": len(patched_items),
            "dry_run": dry_run,
            "source": source,
        }


class NoteService:
    """Note services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def get(self, collection_path: str | None, *, note_id: int) -> dict:
        return self.backend.get_note(
            _resolve_collection_arg(self.backend, collection_path, command_name="note get"),
            note_id,
        )

    def fields(self, collection_path: str | None, *, note_id: int) -> dict:
        return self.backend.get_note_fields(
            _resolve_collection_arg(self.backend, collection_path, command_name="note fields"),
            note_id,
        )

    def add(
        self,
        collection_path: str | None,
        *,
        deck_name: str,
        model_name: str,
        field_assignments: list[str],
        tags: list[str],
        dry_run: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="note add")
        fields = _parse_field_assignments(field_assignments)
        if not fields:
            raise ValidationError("At least one --field Name=Value assignment is required")
        return self.backend.add_note(
            path,
            deck_name=deck_name,
            model_name=model_name,
            fields=fields,
            tags=tags,
            dry_run=dry_run,
        )

    def update(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        field_assignments: list[str],
        dry_run: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="note update")
        fields = _parse_field_assignments(field_assignments)
        if not fields:
            raise ValidationError("At least one --field Name=Value assignment is required")
        return self.backend.update_note(
            path,
            note_id=note_id,
            fields=fields,
            dry_run=dry_run,
        )

    def delete(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="note delete")
        if not dry_run and not yes:
            raise UnsafeOperationError("note delete requires --yes or --dry-run")
        return self.backend.delete_note(
            path,
            note_id=note_id,
            dry_run=dry_run,
        )

    def add_tags(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        tags: list[str],
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="note add-tags")
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("note add-tags requires --yes or --dry-run")
        return self.backend.add_tags_to_notes(
            path,
            note_ids=[note_id],
            tags=normalized_tags,
            dry_run=dry_run,
        )[0]

    def remove_tags(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        tags: list[str],
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="note remove-tags",
        )
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("note remove-tags requires --yes or --dry-run")
        return self.backend.remove_tags_from_notes(
            path,
            note_ids=[note_id],
            tags=normalized_tags,
            dry_run=dry_run,
        )[0]

    def move_deck(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        deck_name: str,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="note move-deck")
        normalized_deck_name = deck_name.strip()
        if not normalized_deck_name:
            raise ValidationError("--deck must not be empty")
        if not dry_run and not yes:
            raise UnsafeOperationError("note move-deck requires --yes or --dry-run")
        return self.backend.move_note_to_deck(
            path,
            note_id=note_id,
            deck_name=normalized_deck_name,
            dry_run=dry_run,
        )

    def _parse_tags(self, tags: list[str]) -> list[str]:
        normalized = [tag.strip() for tag in tags if tag.strip()]
        if not normalized:
            raise ValidationError("At least one --tag value is required")
        return normalized


class CardService:
    """Card services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def get(self, collection_path: str | None, *, card_id: int) -> dict:
        return self.backend.get_card(
            _resolve_collection_arg(self.backend, collection_path, command_name="card get"),
            card_id,
        )

    def suspend(
        self,
        collection_path: str | None,
        *,
        card_id: int,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="card suspend")
        if not dry_run and not yes:
            raise UnsafeOperationError("card suspend requires --yes or --dry-run")
        return self.backend.suspend_cards(
            path,
            card_ids=[card_id],
            dry_run=dry_run,
        )[0]

    def unsuspend(
        self,
        collection_path: str | None,
        *,
        card_id: int,
        dry_run: bool,
        yes: bool,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="card unsuspend")
        if not dry_run and not yes:
            raise UnsafeOperationError("card unsuspend requires --yes or --dry-run")
        return self.backend.unsuspend_cards(
            path,
            card_ids=[card_id],
            dry_run=dry_run,
        )[0]


class PlaceholderMutationService:
    """Stable placeholder for commands not built yet."""

    def fail(self, command_name: str) -> None:
        raise NotImplementedYetError(f"{command_name} is not implemented yet")
