"""Services used by the CLI."""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

from ankicli.app.credentials import (
    CredentialStore,
    default_credential_store,
    probe_default_credential_store,
)
from ankicli.app.errors import (
    AuthRequiredError,
    BackendOperationUnsupportedError,
    BackupNotFoundError,
    BackupRestoreUnsafeError,
    CollectionRequiredError,
    NotImplementedYetError,
    UnsafeOperationError,
    ValidationError,
)
from ankicli.app.profiles import ProfileResolver, default_anki2_root
from ankicli.backends.base import BaseBackend
from ankicli.runtime import probe_anki_runtime


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


def _default_credential_store() -> CredentialStore:
    return default_credential_store()


def _default_profile_resolver() -> ProfileResolver:
    return ProfileResolver()


def _with_auto_backup_metadata(result: dict, backup: dict) -> dict:
    payload = dict(result)
    payload["auto_backup_created"] = backup["created"]
    payload["auto_backup_name"] = backup["name"]
    payload["auto_backup_path"] = backup["path"]
    return payload


def _persist_rotated_sync_endpoint(
    *,
    credential_store: CredentialStore,
    backend_name: str,
    credential,
    result: dict,
) -> dict:
    payload = dict(result)
    endpoint = payload.get("new_endpoint")
    if not endpoint or endpoint == credential.endpoint:
        return payload
    credential_store.write(
        backend_name=backend_name,
        credential=type(credential)(hkey=credential.hkey, endpoint=endpoint),
    )
    return payload


class DoctorService:
    """Environment and capability diagnostics."""

    def env_report(self) -> dict:
        probe = probe_anki_runtime()
        credential_store = probe_default_credential_store()
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "default_anki2_root": str(default_anki2_root().expanduser().resolve()),
            "anki_source_path": probe.source_path,
            "anki_source_import_path": probe.source_import_path,
            "anki_import_available": probe.import_available,
            "anki_module_path": probe.module_path,
            "anki_version": probe.version,
            "supported_runtime_version": probe.supported_runtime_version,
            "anki_runtime_mode": probe.runtime_mode,
            "anki_runtime_override_active": probe.override_active,
            "supported_runtime": probe.supported_runtime,
            "runtime_failure_reason": probe.failure_reason,
            "credential_storage_backend": credential_store.backend,
            "credential_storage_available": credential_store.available,
            "credential_storage_fallback": credential_store.fallback,
            "credential_storage_path": credential_store.path,
            "credential_storage_reason": credential_store.reason,
            "ankiconnect_url": os.environ.get("ANKICONNECT_URL", "http://127.0.0.1:8765"),
        }

    def backend_report(self, backend: BaseBackend) -> dict:
        capabilities = backend.backend_capabilities()
        credential_store = probe_default_credential_store()
        supported_count = sum(
            1 for supported in capabilities.supported_operations.values() if supported
        )
        supported_workflow_count = sum(
            1 for supported in capabilities.supported_workflows.values() if supported
        )
        return {
            "name": backend.name,
            "available": capabilities.available,
            "supports_live_desktop": capabilities.supports_live_desktop,
            "runtime_mode": capabilities.runtime_mode,
            "runtime_override_active": capabilities.runtime_override_active,
            "runtime_module_path": capabilities.runtime_module_path,
            "runtime_version": capabilities.runtime_version,
            "supported_runtime_version": capabilities.supported_runtime_version,
            "supported_runtime": capabilities.supported_runtime,
            "runtime_failure_reason": capabilities.runtime_failure_reason,
            "supported_operation_count": supported_count,
            "unsupported_operation_count": len(capabilities.supported_operations) - supported_count,
            "supported_workflow_count": supported_workflow_count,
            "unsupported_workflow_count": len(capabilities.supported_workflows)
            - supported_workflow_count,
            "ankiconnect_url": os.environ.get("ANKICONNECT_URL", "http://127.0.0.1:8765")
            if backend.name == "ankiconnect"
            else None,
            "default_anki2_root": str(default_anki2_root().expanduser().resolve())
            if backend.name == "python-anki"
            else None,
            "anki_source_path": os.environ.get("ANKI_SOURCE_PATH")
            if backend.name == "python-anki"
            else None,
            "credential_storage_backend": credential_store.backend
            if backend.name == "python-anki"
            else None,
            "credential_storage_available": credential_store.available
            if backend.name == "python-anki"
            else None,
            "credential_storage_fallback": credential_store.fallback
            if backend.name == "python-anki"
            else None,
            "credential_storage_path": credential_store.path
            if backend.name == "python-anki"
            else None,
            "credential_storage_reason": credential_store.reason
            if backend.name == "python-anki"
            else None,
            "notes": capabilities.notes,
        }

    def capabilities_report(self, backend: BaseBackend) -> dict:
        capabilities = backend.backend_capabilities().model_dump()
        supported = capabilities["supported_operations"]
        supported_workflows = capabilities["supported_workflows"]
        capabilities["supported_operation_count"] = sum(
            1 for value in supported.values() if value
        )
        capabilities["unsupported_operation_count"] = sum(
            1 for value in supported.values() if not value
        )
        capabilities["supported_workflow_count"] = sum(
            1 for value in supported_workflows.values() if value
        )
        capabilities["unsupported_workflow_count"] = sum(
            1 for value in supported_workflows.values() if not value
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


class AuthService:
    """Credential-backed sync auth operations."""

    def __init__(self, backend: BaseBackend, *, credential_store: CredentialStore | None = None):
        self.backend = backend
        self.credential_store = credential_store or _default_credential_store()

    def status(self, collection_path: str | None) -> dict:
        credential = self.credential_store.read(backend_name=self.backend.name)
        payload = self.backend.auth_status(
            None if collection_path is None else Path(collection_path),
            credential=credential,
        )
        payload["credential_backend"] = self.credential_store.info().backend
        return payload

    def login(
        self,
        collection_path: str | None,
        *,
        username: str,
        password: str,
        endpoint: str | None,
    ) -> dict:
        path = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="auth login",
        )
        credential = self.backend.login(
            path,
            username=username,
            password=password,
            endpoint=endpoint,
        )
        self.credential_store.write(backend_name=self.backend.name, credential=credential)
        store_info = self.credential_store.info()
        return {
            "authenticated": True,
            "credential_backend": store_info.backend,
            "credential_present": True,
            "endpoint": credential.endpoint,
        }

    def logout(self, collection_path: str | None) -> dict:
        result = self.backend.logout(None if collection_path is None else Path(collection_path))
        deleted = self.credential_store.clear(backend_name=self.backend.name)
        store_info = self.credential_store.info()
        return {
            "authenticated": False,
            "credential_backend": store_info.backend,
            "credential_present": False,
            "deleted": deleted,
            **result,
        }


class SyncService:
    """Collection sync operations."""

    def __init__(
        self,
        backend: BaseBackend,
        *,
        credential_store: CredentialStore | None = None,
        auto_backup_enabled: bool = True,
    ):
        self.backend = backend
        self.credential_store = credential_store or _default_credential_store()
        self.backup_service = BackupService(backend)
        self.auto_backup_enabled = auto_backup_enabled

    def _ensure_supported(self, operation: str) -> None:
        capabilities = self.backend.backend_capabilities()
        if not capabilities.supported_operations.get(operation, False):
            raise BackendOperationUnsupportedError(
                f"{operation} is not supported by the {self.backend.name} backend",
                details={"backend": self.backend.name, "operation": operation},
            )

    def _credential(self):
        credential = self.credential_store.read(backend_name=self.backend.name)
        if credential is None:
            raise AuthRequiredError("Sync credentials are required before syncing")
        return credential

    def status(self, collection_path: str | None) -> dict:
        self._ensure_supported("sync.status")
        path = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="sync status",
        )
        credential = self._credential()
        return _persist_rotated_sync_endpoint(
            credential_store=self.credential_store,
            backend_name=self.backend.name,
            credential=credential,
            result=self.backend.sync_status(path, credential=credential),
        )

    def run(self, collection_path: str | None) -> dict:
        self._ensure_supported("sync.run")
        path = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="sync run",
        )
        credential = self._credential()
        backup = self.backup_service.auto_backup(
            path,
            enabled=self.auto_backup_enabled,
            dry_run=False,
        )
        return _with_auto_backup_metadata(
            _persist_rotated_sync_endpoint(
                credential_store=self.credential_store,
                backend_name=self.backend.name,
                credential=credential,
                result=self.backend.sync_run(path, credential=credential),
            ),
            backup,
        )

    def pull(self, collection_path: str | None) -> dict:
        self._ensure_supported("sync.pull")
        path = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="sync pull",
        )
        credential = self._credential()
        backup = self.backup_service.auto_backup(
            path,
            enabled=self.auto_backup_enabled,
            dry_run=False,
        )
        return _with_auto_backup_metadata(
            _persist_rotated_sync_endpoint(
                credential_store=self.credential_store,
                backend_name=self.backend.name,
                credential=credential,
                result=self.backend.sync_pull(path, credential=credential),
            ),
            backup,
        )

    def push(self, collection_path: str | None) -> dict:
        self._ensure_supported("sync.push")
        path = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="sync push",
        )
        credential = self._credential()
        backup = self.backup_service.auto_backup(
            path,
            enabled=self.auto_backup_enabled,
            dry_run=False,
        )
        return _with_auto_backup_metadata(
            _persist_rotated_sync_endpoint(
                credential_store=self.credential_store,
                backend_name=self.backend.name,
                credential=credential,
                result=self.backend.sync_push(path, credential=credential),
            ),
            backup,
        )


class ProfileService:
    """Local profile discovery services."""

    def __init__(self, backend: BaseBackend, *, resolver: ProfileResolver | None = None) -> None:
        self.backend = backend
        self.resolver = resolver or _default_profile_resolver()

    def _ensure_supported(self, operation: str) -> None:
        if self.backend.name == "ankiconnect":
            raise BackendOperationUnsupportedError(
                f"{operation} is not supported by the ankiconnect backend",
                details={"backend": self.backend.name, "operation": operation},
            )

    def list(self) -> dict:
        self._ensure_supported("profile.list")
        return {"items": [profile.to_dict() for profile in self.resolver.list_profiles()]}

    def get(self, *, name: str) -> dict:
        self._ensure_supported("profile.get")
        return self.resolver.resolve_profile(name).to_dict()

    def default(self) -> dict:
        self._ensure_supported("profile.default")
        return self.resolver.default_profile().to_dict()

    def resolve(self, *, name: str) -> dict:
        self._ensure_supported("profile.resolve")
        return self.resolver.resolve_profile(name).to_dict()


class BackupService:
    """Backup and restore services."""

    def __init__(self, backend: BaseBackend, *, resolver: ProfileResolver | None = None) -> None:
        self.backend = backend
        self.resolver = resolver or _default_profile_resolver()

    def _ensure_supported(self, operation: str) -> None:
        if self.backend.name == "ankiconnect":
            raise BackendOperationUnsupportedError(
                f"{operation} is not supported by the ankiconnect backend",
                details={"backend": self.backend.name, "operation": operation},
            )

    def _context(self, collection_path: str | None):
        path = _resolve_collection_arg(self.backend, collection_path, command_name="backup")
        return self.resolver.resolve_collection(path)

    def _list_items(self, context) -> list[dict]:
        backup_dir = context.backup_dir
        if not backup_dir.exists():
            return []
        items = []
        for entry in sorted(backup_dir.glob("*.colpkg"), reverse=True):
            stat = entry.stat()
            items.append(
                {
                    "name": entry.name,
                    "path": str(entry.resolve()),
                    "created_at": stat.st_mtime,
                    "size": stat.st_size,
                    "profile": context.name,
                    "collection_path": str(context.collection_path),
                    "kind": "anki-native",
                    "restorable": entry.is_file(),
                    "notes": [],
                }
            )
        return items

    def _item_for_path(self, context, candidate: Path) -> dict:
        if not candidate.exists() or not candidate.is_file():
            raise BackupNotFoundError(
                f"Backup path does not exist: {candidate}",
                details={"path": str(candidate)},
            )
        if candidate.suffix != ".colpkg":
            raise ValidationError("Backup path must point to a .colpkg artifact")
        stat = candidate.stat()
        return {
            "name": candidate.name,
            "path": str(candidate.resolve()),
            "created_at": stat.st_mtime,
            "size": stat.st_size,
            "profile": context.name,
            "collection_path": str(context.collection_path),
            "kind": "anki-native",
            "restorable": True,
            "notes": [],
        }

    def status(self, collection_path: str | None) -> dict:
        self._ensure_supported("backup.status")
        context = self._context(collection_path)
        return {
            "profile": context.name,
            "collection_path": str(context.collection_path),
            "backup_dir": str(context.backup_dir),
            "auto_backup_available": self.backend.name == "python-anki",
            "backup_count": len(self._list_items(context)),
            "known_profile": context.known_profile,
        }

    def list(self, collection_path: str | None) -> dict:
        self._ensure_supported("backup.list")
        context = self._context(collection_path)
        return {"items": self._list_items(context)}

    def get(
        self,
        collection_path: str | None,
        *,
        name: str | None,
        path: str | None,
    ) -> dict:
        self._ensure_supported("backup.get")
        context = self._context(collection_path)
        if bool(name) == bool(path):
            raise ValidationError("backup get requires exactly one of --name or --path")
        if path:
            candidate = Path(path).expanduser().resolve()
            return self._item_for_path(context, candidate)
        for item in self._list_items(context):
            if item["name"] == name:
                return item
        raise BackupNotFoundError(
            f'Backup "{name}" was not found',
            details={"name": name, "collection_path": str(context.collection_path)},
        )

    def create(self, collection_path: str | None) -> dict:
        self._ensure_supported("backup.create")
        context = self._context(collection_path)
        before = {
            item["path"]: (
                item["created_at"],
                item["size"],
            )
            for item in self._list_items(context)
        }
        result = self.backend.create_backup(
            context.collection_path,
            backup_folder=context.backup_dir,
            force=True,
        )
        after_items = self._list_items(context)
        created_item = next((item for item in after_items if item["path"] not in before), None)
        if created_item is None:
            created_item = next(
                (
                    item
                    for item in after_items
                    if before.get(item["path"]) != (item["created_at"], item["size"])
                ),
                None,
            )
        return {
            "created": bool(result.get("created")) and created_item is not None,
            "name": created_item["name"] if created_item else None,
            "path": created_item["path"] if created_item else None,
            "profile": context.name,
            "collection_path": str(context.collection_path),
            "kind": "anki-native",
        }

    def auto_backup(
        self,
        collection_path: Path | str,
        *,
        enabled: bool,
        dry_run: bool,
    ) -> dict:
        if self.backend.name != "python-anki" or not enabled or dry_run:
            return {"created": False, "name": None, "path": None}
        return self.create(str(collection_path))

    def restore(
        self,
        collection_path: str | None,
        *,
        name: str | None,
        path: str | None,
        yes: bool,
    ) -> dict:
        self._ensure_supported("backup.restore")
        if not yes:
            raise UnsafeOperationError("backup restore requires --yes")
        context = self._context(collection_path)
        collection_lock = CollectionService(self.backend).lock_status(str(context.collection_path))
        if collection_lock["status"] not in {"not-detected", "unknown"}:
            raise BackupRestoreUnsafeError(
                "Collection appears to be in use; refusing restore",
                details={
                    "collection_path": str(context.collection_path),
                    "lock_status": collection_lock,
                },
            )
        backup_item = self.get(str(context.collection_path), name=name, path=path)
        safety_backup = self.create(str(context.collection_path))
        result = self.backend.restore_backup(
            context.collection_path,
            backup_path=Path(backup_item["path"]),
            media_folder=context.media_dir,
            media_db_path=context.media_db_path,
        )
        payload = dict(result)
        payload["safety_backup_name"] = safety_backup["name"]
        payload["safety_backup_path"] = safety_backup["path"]
        return payload


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
        base_query = f'deck:"{name}"'
        note_result = self.backend.find_notes(path, base_query, limit=1, offset=0)
        card_result = self.backend.find_cards(path, base_query, limit=1, offset=0)
        due_result = self.backend.find_cards(path, f"{base_query} is:due", limit=1, offset=0)
        new_result = self.backend.find_cards(path, f"{base_query} is:new", limit=1, offset=0)
        learning_result = self.backend.find_cards(path, f"{base_query} is:learn", limit=1, offset=0)
        review_result = self.backend.find_cards(path, f"{base_query} is:review", limit=1, offset=0)
        return {
            "id": deck["id"],
            "name": deck["name"],
            "note_count": note_result["total"],
            "card_count": card_result["total"],
            "due_count": due_result["total"],
            "new_count": new_result["total"],
            "learning_count": learning_result["total"],
            "review_count": review_result["total"],
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
        self.backup_service = BackupService(backend)

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
        auto_backup_enabled: bool = True,
    ) -> dict:
        normalized_source = source_path.strip()
        if not normalized_source:
            raise ValidationError("--source must not be empty")
        normalized_name = name.strip() if name is not None else None
        if normalized_name == "":
            raise ValidationError("--name must not be empty")
        if not dry_run and not yes:
            raise UnsafeOperationError("media attach requires --yes or --dry-run")
        path = _resolve_collection_arg(self.backend, collection_path, command_name="media attach")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.attach_media(
                path,
                source_path=Path(normalized_source),
                name=normalized_name,
                dry_run=dry_run,
            ),
            backup,
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
        self.backup_service = BackupService(backend)

    def rename(
        self,
        collection_path: str | None,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
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
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.rename_tag(
                path,
                name=normalized_name,
                new_name=normalized_new_name,
                dry_run=dry_run,
            ),
            backup,
        )

    def delete(
        self,
        collection_path: str | None,
        *,
        tags: list[str],
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="tag delete")
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("tag delete requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.delete_tags(
                path,
                tags=normalized_tags,
                dry_run=dry_run,
            ),
            backup,
        )

    def reparent(
        self,
        collection_path: str | None,
        *,
        tags: list[str],
        new_parent: str,
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="tag reparent")
        normalized_tags = self._parse_tags(tags)
        normalized_parent = new_parent.strip()
        if any(tag == normalized_parent for tag in normalized_tags if normalized_parent):
            raise ValidationError("--to-parent must differ from the moved tag names")
        if not dry_run and not yes:
            raise UnsafeOperationError("tag reparent requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.reparent_tags(
                path,
                tags=normalized_tags,
                new_parent=normalized_parent,
                dry_run=dry_run,
            ),
            backup,
        )

    def apply(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        tags: list[str],
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="tag apply")
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("tag apply requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.add_tags_to_notes(
                path,
                note_ids=[note_id],
                tags=normalized_tags,
                dry_run=dry_run,
            )[0],
            backup,
        )

    def remove(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        tags: list[str],
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="tag remove")
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("tag remove requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.remove_tags_from_notes(
                path,
                note_ids=[note_id],
                tags=normalized_tags,
                dry_run=dry_run,
            )[0],
            backup,
        )

    def _parse_tags(self, tags: list[str]) -> list[str]:
        normalized = [tag.strip() for tag in tags if tag.strip()]
        if not normalized:
            raise ValidationError("At least one --tag value is required")
        return normalized


class DeckService:
    """Deck lifecycle services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend
        self.backup_service = BackupService(backend)

    def create(
        self,
        collection_path: str | None,
        *,
        name: str,
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="deck create")
        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        if not dry_run and not yes:
            raise UnsafeOperationError("deck create requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.create_deck(path, name=normalized_name, dry_run=dry_run),
            backup,
        )

    def rename(
        self,
        collection_path: str | None,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
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
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.rename_deck(
                path,
                name=normalized_name,
                new_name=normalized_new_name,
                dry_run=dry_run,
            ),
            backup,
        )

    def delete(
        self,
        collection_path: str | None,
        *,
        name: str,
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="deck delete")
        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        if not dry_run and not yes:
            raise UnsafeOperationError("deck delete requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.delete_deck(path, name=normalized_name, dry_run=dry_run),
            backup,
        )

    def reparent(
        self,
        collection_path: str | None,
        *,
        name: str,
        new_parent: str,
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
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
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.reparent_deck(
                path,
                name=normalized_name,
                new_parent=normalized_parent,
                dry_run=dry_run,
            ),
            backup,
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
        self.backup_service = BackupService(backend)

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
        auto_backup_enabled: bool = True,
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

        backup = self.backup_service.auto_backup(
            collection,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            {
                "items": imported_items,
                "count": len(imported_items),
                "dry_run": dry_run,
                "source": source,
            },
            backup,
        )

    def import_patch(
        self,
        collection_path: str | None,
        *,
        input_path: str | None,
        stdin_json: bool,
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
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

        backup = self.backup_service.auto_backup(
            collection,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            {
                "items": patched_items,
                "count": len(patched_items),
                "dry_run": dry_run,
                "source": source,
            },
            backup,
        )


class NoteService:
    """Note services."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend
        self.backup_service = BackupService(backend)

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
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="note delete")
        if not dry_run and not yes:
            raise UnsafeOperationError("note delete requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.delete_note(
                path,
                note_id=note_id,
                dry_run=dry_run,
            ),
            backup,
        )

    def add_tags(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        tags: list[str],
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="note add-tags")
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("note add-tags requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.add_tags_to_notes(
                path,
                note_ids=[note_id],
                tags=normalized_tags,
                dry_run=dry_run,
            )[0],
            backup,
        )

    def remove_tags(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        tags: list[str],
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="note remove-tags",
        )
        normalized_tags = self._parse_tags(tags)
        if not dry_run and not yes:
            raise UnsafeOperationError("note remove-tags requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.remove_tags_from_notes(
                path,
                note_ids=[note_id],
                tags=normalized_tags,
                dry_run=dry_run,
            )[0],
            backup,
        )

    def move_deck(
        self,
        collection_path: str | None,
        *,
        note_id: int,
        deck_name: str,
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="note move-deck")
        normalized_deck_name = deck_name.strip()
        if not normalized_deck_name:
            raise ValidationError("--deck must not be empty")
        if not dry_run and not yes:
            raise UnsafeOperationError("note move-deck requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.move_note_to_deck(
                path,
                note_id=note_id,
                deck_name=normalized_deck_name,
                dry_run=dry_run,
            ),
            backup,
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
        self.backup_service = BackupService(backend)

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
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="card suspend")
        if not dry_run and not yes:
            raise UnsafeOperationError("card suspend requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.suspend_cards(
                path,
                card_ids=[card_id],
                dry_run=dry_run,
            )[0],
            backup,
        )

    def unsuspend(
        self,
        collection_path: str | None,
        *,
        card_id: int,
        dry_run: bool,
        yes: bool,
        auto_backup_enabled: bool = True,
    ) -> dict:
        path = _resolve_collection_arg(self.backend, collection_path, command_name="card unsuspend")
        if not dry_run and not yes:
            raise UnsafeOperationError("card unsuspend requires --yes or --dry-run")
        backup = self.backup_service.auto_backup(
            path,
            enabled=auto_backup_enabled,
            dry_run=dry_run,
        )
        return _with_auto_backup_metadata(
            self.backend.unsuspend_cards(
                path,
                card_ids=[card_id],
                dry_run=dry_run,
            )[0],
            backup,
        )


class PlaceholderMutationService:
    """Stable placeholder for commands not built yet."""

    def fail(self, command_name: str) -> None:
        raise NotImplementedYetError(f"{command_name} is not implemented yet")
