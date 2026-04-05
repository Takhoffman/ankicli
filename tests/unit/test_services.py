from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from ankicli.app.credentials import SyncCredential
from ankicli.app.errors import (
    AuthRequiredError,
    BackendOperationUnsupportedError,
    BackupRestoreUnsafeError,
    CollectionRequiredError,
    UnsafeOperationError,
    ValidationError,
)
from ankicli.app.models import BackendCapabilities
from ankicli.app.profiles import ProfileResolver
from ankicli.app.services import (
    AuthService,
    BackendService,
    BackupService,
    CardService,
    CatalogService,
    CollectionService,
    DeckService,
    DoctorService,
    ExportService,
    ImportService,
    MediaService,
    NoteService,
    SearchService,
    SyncService,
    TagService,
)
from ankicli.backends.python_anki import PythonAnkiBackend
from ankicli.runtime import (
    SUPPORTED_ANKI_VERSION,
    configure_anki_source_path,
    probe_anki_runtime,
)
from tests.proof import proves


@pytest.mark.unit
def test_doctor_env_report_has_expected_keys() -> None:
    report = DoctorService().env_report()

    assert "python_version" in report
    assert "platform" in report
    assert "anki_source_path" in report
    assert "anki_source_import_path" in report
    assert "anki_import_available" in report
    assert "anki_module_path" in report
    assert "anki_version" in report
    assert "default_anki2_root" in report
    assert "supported_runtime" in report
    assert "runtime_failure_reason" in report
    assert "credential_storage_backend" in report
    assert "credential_storage_available" in report
    assert "credential_storage_fallback" in report


@pytest.mark.unit
def test_python_anki_backend_reports_capabilities() -> None:
    capabilities = PythonAnkiBackend().backend_capabilities()

    assert capabilities.backend == "python-anki"
    assert capabilities.supports_live_desktop is False
    assert "note.delete" in capabilities.supported_operations
    assert capabilities.supported_operations["note.delete"] is capabilities.available
    assert capabilities.supported_runtime_version == SUPPORTED_ANKI_VERSION


@pytest.mark.unit
@proves("doctor.backend", "failure")
def test_doctor_backend_report_summarizes_operation_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "backend_capabilities",
        lambda: BackendCapabilities(
            backend="python-anki",
            available=True,
            supports_collection_reads=True,
            supports_collection_writes=True,
            supports_live_desktop=False,
            runtime_mode="packaged",
            supported_runtime=True,
            supported_operations={
                "collection.info": True,
                "note.delete": True,
                "tag.rename": False,
            },
        ),
    )

    report = DoctorService().backend_report(backend)

    assert report["name"] == "python-anki"
    assert report["available"] is True
    assert report["runtime_mode"] == "packaged"
    assert report["supported_runtime"] is True
    assert report["supported_operation_count"] == 2
    assert report["unsupported_operation_count"] == 1


@pytest.mark.unit
@proves("doctor.capabilities", "failure")
def test_doctor_capabilities_report_adds_operation_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "backend_capabilities",
        lambda: BackendCapabilities(
            backend="python-anki",
            available=True,
            supports_collection_reads=True,
            supports_collection_writes=True,
            supports_live_desktop=False,
            runtime_mode="packaged",
            supported_runtime=True,
            supported_operations={"collection.info": True, "tag.rename": False},
        ),
    )

    report = DoctorService().capabilities_report(backend)

    assert report["supported_operation_count"] == 1
    assert report["unsupported_operation_count"] == 1
    assert report["supported_operations"]["tag.rename"] is False


@pytest.mark.unit
@proves("backend.test-connection", "failure")
def test_backend_test_connection_uses_backend_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "backend_capabilities",
        lambda: BackendCapabilities(
            backend="python-anki",
            available=False,
            supports_collection_reads=True,
            supports_collection_writes=True,
            supports_live_desktop=False,
            runtime_failure_reason="missing_runtime",
            supported_operations={"collection.info": True},
        ),
    )

    result = BackendService(backend).test_connection()

    assert result == {
        "name": "python-anki",
        "ok": False,
        "available": False,
        "notes": [],
    }


@pytest.mark.unit
def test_probe_anki_runtime_reports_missing_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANKI_SOURCE_PATH", raising=False)
    monkeypatch.setattr(
        "ankicli.runtime._import_anki_module",
        lambda: (_ for _ in ()).throw(ImportError("missing anki")),
    )

    probe = probe_anki_runtime()

    assert probe.import_available is False
    assert probe.runtime_mode == "packaged"
    assert probe.supported_runtime is False
    assert probe.failure_reason == "missing_runtime"


@pytest.mark.unit
def test_probe_anki_runtime_reports_supported_packaged_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_anki = SimpleNamespace(
        __file__="/tmp/site-packages/anki/__init__.py",
        __version__=SUPPORTED_ANKI_VERSION,
    )
    fake_collection_module = SimpleNamespace(Collection=object)
    monkeypatch.delenv("ANKI_SOURCE_PATH", raising=False)

    def fake_import_module(name: str):
        if name == "anki":
            return fake_anki
        if name == "anki.collection":
            return fake_collection_module
        raise ImportError(name)

    monkeypatch.setattr("ankicli.runtime.importlib.import_module", fake_import_module)

    probe = probe_anki_runtime()

    assert probe.import_available is True
    assert probe.runtime_mode == "packaged"
    assert probe.version == SUPPORTED_ANKI_VERSION
    assert probe.collection_import_available is True
    assert probe.supported_runtime is True
    assert probe.failure_reason is None


@pytest.mark.unit
def test_probe_anki_runtime_reports_version_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_anki = SimpleNamespace(__file__="/tmp/site-packages/anki/__init__.py", __version__="24.11")
    fake_collection_module = SimpleNamespace(Collection=object)
    monkeypatch.delenv("ANKI_SOURCE_PATH", raising=False)

    def fake_import_module(name: str):
        if name == "anki":
            return fake_anki
        if name == "anki.collection":
            return fake_collection_module
        raise ImportError(name)

    monkeypatch.setattr("ankicli.runtime.importlib.import_module", fake_import_module)

    probe = probe_anki_runtime()

    assert probe.import_available is True
    assert probe.supported_runtime is False
    assert probe.failure_reason == "version_mismatch"


@pytest.mark.unit
def test_probe_anki_runtime_reports_missing_collection_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_anki = SimpleNamespace(
        __file__="/tmp/site-packages/anki/__init__.py",
        __version__=SUPPORTED_ANKI_VERSION,
    )
    monkeypatch.delenv("ANKI_SOURCE_PATH", raising=False)

    def fake_import_module(name: str):
        if name == "anki":
            return fake_anki
        raise ImportError(name)

    monkeypatch.setattr("ankicli.runtime.importlib.import_module", fake_import_module)

    probe = probe_anki_runtime()

    assert probe.import_available is True
    assert probe.collection_import_available is False
    assert probe.supported_runtime is False
    assert probe.failure_reason == "collection_api_unavailable"


@pytest.mark.unit
def test_probe_anki_runtime_marks_override_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path / "anki"
    (source_root / "pylib").mkdir(parents=True)
    fake_anki = SimpleNamespace(
        __file__=str(source_root / "pylib" / "anki" / "__init__.py"),
        __version__=SUPPORTED_ANKI_VERSION,
    )
    fake_collection_module = SimpleNamespace(Collection=object)
    monkeypatch.setenv("ANKI_SOURCE_PATH", str(source_root))

    def fake_import_module(name: str):
        if name == "anki":
            return fake_anki
        if name == "anki.collection":
            return fake_collection_module
        raise ImportError(name)

    monkeypatch.setattr("ankicli.runtime.importlib.import_module", fake_import_module)

    probe = probe_anki_runtime()

    assert probe.runtime_mode == "override"
    assert probe.override_active is True
    assert probe.source_import_path == str((source_root / "pylib").resolve())


@pytest.mark.unit
def test_backend_operation_unsupported_is_structured_for_ankiconnect() -> None:
    backend = PythonAnkiBackend()
    backend.name = "ankiconnect"  # type: ignore[attr-defined]
    monkeypatch_message = "note.delete is not supported by the ankiconnect backend"
    monkeypatch_details = {"backend": "ankiconnect", "operation": "note.delete"}

    def fail_delete(path, *, note_id, dry_run):  # noqa: ARG001
        raise BackendOperationUnsupportedError(
            monkeypatch_message,
            details=monkeypatch_details,
        )

    backend.delete_note = fail_delete  # type: ignore[method-assign]

    with pytest.raises(BackendOperationUnsupportedError) as excinfo:
        NoteService(backend).delete(None, note_id=101, dry_run=True, yes=False)

    assert excinfo.value.details == monkeypatch_details


class _FakeCredentialStore:
    def __init__(
        self,
        credential: SyncCredential | None = None,
        *,
        backend_label: str = "keyring",
        fallback: bool = False,
    ) -> None:
        self.credential = credential
        self.backend_label = backend_label
        self.fallback = fallback
        self.writes: list[tuple[str, SyncCredential]] = []
        self.clears: list[str] = []

    def read(self, *, backend_name: str) -> SyncCredential | None:
        del backend_name
        return self.credential

    def write(self, *, backend_name: str, credential: SyncCredential) -> None:
        self.writes.append((backend_name, credential))
        self.credential = credential

    def clear(self, *, backend_name: str) -> bool:
        self.clears.append(backend_name)
        deleted = self.credential is not None
        self.credential = None
        return deleted

    def info(self):
        return SimpleNamespace(
            backend=self.backend_label,
            available=True,
            fallback=self.fallback,
            path=None,
            reason=None,
        )


@pytest.mark.unit
@proves("auth.status", "unit")
def test_auth_status_reports_stored_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    store = _FakeCredentialStore(SyncCredential(hkey="abc", endpoint="https://sync"))
    monkeypatch.setattr(
        backend,
        "auth_status",
        lambda path, credential: {
            "authenticated": credential is not None,
            "endpoint": credential.endpoint if credential else None,
        },
    )

    result = AuthService(backend, credential_store=store).status("/tmp/test.anki2")

    assert result == {
        "authenticated": True,
        "endpoint": "https://sync",
        "credential_backend": "keyring",
    }


@pytest.mark.unit
@proves("auth.login", "unit", "safety")
def test_auth_login_persists_sync_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    store = _FakeCredentialStore()
    collection_path = "/tmp/test.anki2"
    monkeypatch.setattr(
        backend,
        "login",
        lambda path, username, password, endpoint: SyncCredential(
            hkey=f"{username}:{password}",
            endpoint=endpoint,
        ),
    )

    result = AuthService(backend, credential_store=store).login(
        collection_path,
        username="user",
        password="secret",
        endpoint="https://sync",
    )

    assert result["authenticated"] is True
    assert result["credential_backend"] == "keyring"
    assert store.writes == [
        (
            "python-anki",
            SyncCredential(hkey="user:secret", endpoint="https://sync"),
        ),
    ]


@pytest.mark.unit
@proves("auth.logout", "unit", "safety")
def test_auth_logout_deletes_stored_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    store = _FakeCredentialStore(SyncCredential(hkey="abc"))
    monkeypatch.setattr(backend, "logout", lambda path: {"backend": "python-anki"})

    result = AuthService(backend, credential_store=store).logout(None)

    assert result["deleted"] is True
    assert result["credential_backend"] == "keyring"
    assert store.clears == ["python-anki"]


@pytest.mark.unit
@proves("sync.status", "unit", "failure")
def test_sync_status_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    store = _FakeCredentialStore()
    monkeypatch.setattr(
        backend,
        "backend_capabilities",
        lambda: BackendCapabilities(
            backend="python-anki",
            available=True,
            supports_collection_reads=True,
            supports_collection_writes=True,
            supports_live_desktop=False,
            supported_operations={"sync.status": True},
        ),
    )

    with pytest.raises(AuthRequiredError):
        SyncService(backend, credential_store=store).status("/tmp/test.anki2")


@pytest.mark.unit
@proves("sync.run", "unit")
def test_sync_run_delegates_with_stored_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    store = _FakeCredentialStore(SyncCredential(hkey="abc"))
    monkeypatch.setattr(
        backend,
        "backend_capabilities",
        lambda: BackendCapabilities(
            backend="python-anki",
            available=True,
            supports_collection_reads=True,
            supports_collection_writes=True,
            supports_live_desktop=False,
            supported_operations={"sync.run": True},
        ),
    )
    monkeypatch.setattr(
        backend,
        "sync_run",
        lambda path, credential: {
            "performed": True,
            "direction": "bidirectional",
            "hkey": credential.hkey,
        },
    )

    result = SyncService(
        backend,
        credential_store=store,
        auto_backup_enabled=False,
    ).run("/tmp/test.anki2")

    assert result == {
        "performed": True,
        "direction": "bidirectional",
        "hkey": "abc",
        "auto_backup_created": False,
        "auto_backup_name": None,
        "auto_backup_path": None,
    }


@pytest.mark.unit
@proves("sync.run", "unit", "failure")
def test_sync_run_requires_credentials_before_auto_backup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = PythonAnkiBackend()
    store = _FakeCredentialStore()
    calls: list[str] = []
    monkeypatch.setattr(
        backend,
        "backend_capabilities",
        lambda: BackendCapabilities(
            backend="python-anki",
            available=True,
            supports_collection_reads=True,
            supports_collection_writes=True,
            supports_live_desktop=False,
            supported_operations={"sync.run": True},
        ),
    )
    service = SyncService(backend, credential_store=store)
    monkeypatch.setattr(
        service.backup_service,
        "auto_backup",
        lambda path, enabled, dry_run: calls.append(str(path))
        or {"created": True, "name": "b", "path": "/tmp/b"},
    )

    with pytest.raises(AuthRequiredError):
        service.run("/tmp/test.anki2")

    assert calls == []


@pytest.mark.unit
@proves("sync.status", "unit")
def test_sync_status_persists_rotated_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    store = _FakeCredentialStore(SyncCredential(hkey="abc", endpoint="https://sync-1"))
    monkeypatch.setattr(
        backend,
        "backend_capabilities",
        lambda: BackendCapabilities(
            backend="python-anki",
            available=True,
            supports_collection_reads=True,
            supports_collection_writes=True,
            supports_live_desktop=False,
            supported_operations={"sync.status": True},
        ),
    )
    monkeypatch.setattr(
        backend,
        "sync_status",
        lambda path, credential: {
            "required": "normal_sync",
            "required_bool": True,
            "performed": False,
            "direction": None,
            "changes": {},
            "warnings": [],
            "conflicts": [],
            "new_endpoint": "https://sync-2",
        },
    )

    result = SyncService(backend, credential_store=store).status("/tmp/test.anki2")

    assert result["new_endpoint"] == "https://sync-2"
    assert store.writes == [
        ("python-anki", SyncCredential(hkey="abc", endpoint="https://sync-2")),
    ]


@pytest.mark.unit
@proves("backup.list", "unit")
def test_backup_list_normalizes_backups(tmp_path: Path) -> None:
    root = tmp_path / "Anki2"
    profile_dir = root / "User 1"
    backup_dir = profile_dir / "backups"
    backup_dir.mkdir(parents=True)
    collection_path = profile_dir / "collection.anki2"
    collection_path.write_text("fixture")
    backup_path = backup_dir / "backup-2026-03-24-12.00.00.colpkg"
    backup_path.write_text("backup")
    backend = PythonAnkiBackend()

    result = BackupService(
        backend,
        resolver=ProfileResolver(data_root=root),
    ).list(str(collection_path))

    assert result["items"][0]["name"] == backup_path.name
    assert result["items"][0]["kind"] == "anki-native"


@pytest.mark.unit
@proves("backup.create", "unit", "safety")
def test_backup_create_detects_new_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "Anki2"
    profile_dir = root / "User 1"
    backup_dir = profile_dir / "backups"
    backup_dir.mkdir(parents=True)
    collection_path = profile_dir / "collection.anki2"
    collection_path.write_text("fixture")
    backend = PythonAnkiBackend()

    def fake_create_backup(path, *, backup_folder, force):  # noqa: ARG001
        (backup_folder / "backup-2026-03-24-12.00.00.colpkg").write_text("backup")
        return {"created": True}

    monkeypatch.setattr(backend, "create_backup", fake_create_backup)

    result = BackupService(
        backend,
        resolver=ProfileResolver(data_root=root),
    ).create(str(collection_path))

    assert result["created"] is True
    assert result["name"] == "backup-2026-03-24-12.00.00.colpkg"


@pytest.mark.unit
@proves("backup.create", "unit", "safety")
def test_backup_create_detects_overwritten_existing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "Anki2"
    profile_dir = root / "User 1"
    backup_dir = profile_dir / "backups"
    backup_dir.mkdir(parents=True)
    collection_path = profile_dir / "collection.anki2"
    collection_path.write_text("fixture")
    backup_path = backup_dir / "backup-2026-03-24-12.00.00.colpkg"
    backup_path.write_text("before")
    os.utime(backup_path, (1_700_000_000, 1_700_000_000))
    backend = PythonAnkiBackend()

    def fake_create_backup(path, *, backup_folder, force):  # noqa: ARG001
        target = backup_folder / "backup-2026-03-24-12.00.00.colpkg"
        target.write_text("after")
        os.utime(target, (1_800_000_000, 1_800_000_000))
        return {"created": True}

    monkeypatch.setattr(backend, "create_backup", fake_create_backup)

    result = BackupService(
        backend,
        resolver=ProfileResolver(data_root=root),
    ).create(str(collection_path))

    assert result["created"] is True
    assert result["name"] == "backup-2026-03-24-12.00.00.colpkg"


@pytest.mark.unit
@proves("backup.restore", "unit", "failure", "safety")
def test_backup_restore_blocks_when_lock_detected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "Anki2"
    profile_dir = root / "User 1"
    backup_dir = profile_dir / "backups"
    backup_dir.mkdir(parents=True)
    collection_path = profile_dir / "collection.anki2"
    collection_path.write_text("fixture")
    wal_path = profile_dir / "collection.anki2-wal"
    wal_path.write_text("lock")
    backup_path = backup_dir / "backup-2026-03-24-12.00.00.colpkg"
    backup_path.write_text("backup")
    backend = PythonAnkiBackend()

    with pytest.raises(BackupRestoreUnsafeError):
        BackupService(
            backend,
            resolver=ProfileResolver(data_root=root),
        ).restore(str(collection_path), name=backup_path.name, path=None, yes=True)


@pytest.mark.unit
@proves("backup.get", "unit")
def test_backup_get_accepts_external_backup_path(tmp_path: Path) -> None:
    root = tmp_path / "Anki2"
    profile_dir = root / "User 1"
    backup_dir = profile_dir / "backups"
    backup_dir.mkdir(parents=True)
    collection_path = profile_dir / "collection.anki2"
    collection_path.write_text("fixture")
    external_backup = tmp_path / "copied-backup.colpkg"
    external_backup.write_text("backup")

    result = BackupService(
        PythonAnkiBackend(),
        resolver=ProfileResolver(data_root=root),
    ).get(str(collection_path), name=None, path=str(external_backup))

    assert result["path"] == str(external_backup.resolve())
    assert result["name"] == external_backup.name


@pytest.mark.unit
@proves("backup.restore", "unit", "safety")
def test_backup_restore_accepts_external_backup_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "Anki2"
    profile_dir = root / "User 1"
    backup_dir = profile_dir / "backups"
    backup_dir.mkdir(parents=True)
    collection_path = profile_dir / "collection.anki2"
    collection_path.write_text("fixture")
    external_backup = tmp_path / "copied-backup.colpkg"
    external_backup.write_text("backup")
    backend = PythonAnkiBackend()

    def fake_create_backup(path, *, backup_folder, force):  # noqa: ARG001
        (backup_folder / "safety-backup.colpkg").write_text("safety")
        return {"created": True}

    monkeypatch.setattr(backend, "create_backup", fake_create_backup)
    monkeypatch.setattr(
        backend,
        "restore_backup",
        lambda collection_path, backup_path, media_folder, media_db_path: {
            "restored": True,
            "backup_path": str(backup_path),
            "collection_path": str(collection_path),
            "media_folder": str(media_folder),
            "media_db_path": str(media_db_path),
        },
    )

    result = BackupService(
        backend,
        resolver=ProfileResolver(data_root=root),
    ).restore(str(collection_path), name=None, path=str(external_backup), yes=True)

    assert result["restored"] is True
    assert result["backup_path"] == str(external_backup.resolve())
    assert result["safety_backup_name"] == "safety-backup.colpkg"
    assert result["safety_backup_path"] is not None


@pytest.mark.unit
def test_deck_create_includes_auto_backup_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    service = DeckService(backend)
    monkeypatch.setattr(
        service.backup_service,
        "auto_backup",
        lambda path, enabled, dry_run: {
            "created": True,
            "name": "b.colpkg",
            "path": "/tmp/b.colpkg",
        },
    )
    monkeypatch.setattr(
        backend,
        "create_deck",
        lambda path, name, dry_run: {"id": 1, "name": name, "dry_run": dry_run},
    )

    result = service.create(
        "/tmp/test.anki2",
        name="French",
        dry_run=False,
        yes=True,
    )

    assert result["auto_backup_created"] is True
    assert result["auto_backup_name"] == "b.colpkg"


@pytest.mark.unit
def test_note_delete_skips_auto_backup_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    service = NoteService(backend)
    monkeypatch.setattr(
        service.backup_service,
        "auto_backup",
        lambda path, enabled, dry_run: {"created": enabled, "name": None, "path": None},
    )
    monkeypatch.setattr(
        backend,
        "delete_note",
        lambda path, note_id, dry_run: {"id": note_id, "dry_run": dry_run},
    )

    result = service.delete(
        "/tmp/test.anki2",
        note_id=101,
        dry_run=False,
        yes=True,
        auto_backup_enabled=False,
    )

    assert result["auto_backup_created"] is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("method_name", "backend_method"),
    [
        ("add_tags", "add_tags_to_notes"),
        ("remove_tags", "remove_tags_from_notes"),
        ("move_deck", "move_note_to_deck"),
    ],
)
def test_note_mutations_include_auto_backup_metadata(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    backend_method: str,
) -> None:
    backend = PythonAnkiBackend()
    service = NoteService(backend)
    monkeypatch.setattr(
        service.backup_service,
        "auto_backup",
        lambda path, enabled, dry_run: {
            "created": enabled and not dry_run,
            "name": "b.colpkg" if enabled and not dry_run else None,
            "path": "/tmp/b.colpkg" if enabled and not dry_run else None,
        },
    )
    if backend_method in {"add_tags_to_notes", "remove_tags_from_notes"}:
        monkeypatch.setattr(
            backend,
            backend_method,
            lambda path, note_ids, tags, dry_run: [
                {"id": note_ids[0], "tags": tags, "dry_run": dry_run},
            ],
        )
        result = getattr(service, method_name)(
            "/tmp/test.anki2",
            note_id=101,
            tags=["tag1"],
            dry_run=False,
            yes=True,
        )
    else:
        monkeypatch.setattr(
            backend,
            backend_method,
            lambda path, note_id, deck_name, dry_run: {
                "id": note_id,
                "deck": deck_name,
                "dry_run": dry_run,
            },
        )
        result = getattr(service, method_name)(
            "/tmp/test.anki2",
            note_id=101,
            deck_name="French",
            dry_run=False,
            yes=True,
        )

    assert result["auto_backup_created"] is True
    assert result["auto_backup_name"] == "b.colpkg"
    assert result["auto_backup_path"] == "/tmp/b.colpkg"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("method_name", "backend_method"),
    [("suspend", "suspend_cards"), ("unsuspend", "unsuspend_cards")],
)
def test_card_mutations_include_auto_backup_metadata(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    backend_method: str,
) -> None:
    backend = PythonAnkiBackend()
    service = CardService(backend)
    monkeypatch.setattr(
        service.backup_service,
        "auto_backup",
        lambda path, enabled, dry_run: {
            "created": enabled and not dry_run,
            "name": "b.colpkg" if enabled and not dry_run else None,
            "path": "/tmp/b.colpkg" if enabled and not dry_run else None,
        },
    )
    monkeypatch.setattr(
        backend,
        backend_method,
        lambda path, card_ids, dry_run: [{"id": card_ids[0], "dry_run": dry_run}],
    )

    result = getattr(service, method_name)(
        "/tmp/test.anki2",
        card_id=201,
        dry_run=False,
        yes=True,
    )

    assert result["auto_backup_created"] is True
    assert result["auto_backup_name"] == "b.colpkg"
    assert result["auto_backup_path"] == "/tmp/b.colpkg"


@pytest.mark.unit
def test_collection_info_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        CollectionService(PythonAnkiBackend()).info(None)


@pytest.mark.unit
def test_ankiconnect_collection_info_allows_missing_collection_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = PythonAnkiBackend()
    backend.name = "ankiconnect"  # type: ignore[attr-defined]
    monkeypatch.setattr(
        backend,
        "get_collection_info",
        lambda path: {"collection_path": None, "collection_name": "AnkiConnect"},
    )

    result = CollectionService(backend).info(None)

    assert result["collection_name"] == "AnkiConnect"


@pytest.mark.unit
def test_collection_stats_reuses_collection_info(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "get_collection_info",
        lambda path: {
            "collection_path": path,
            "collection_name": "Test",
            "note_count": 1,
            "card_count": 2,
            "deck_count": 3,
            "model_count": 4,
        },
    )

    result = CollectionService(backend).stats("/tmp/test.anki2")

    assert result == {
        "collection_name": "Test",
        "note_count": 1,
        "card_count": 2,
        "deck_count": 3,
        "model_count": 4,
    }


@pytest.mark.unit
def test_deck_stats_uses_existing_backend_primitives(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(backend, "get_deck", lambda path, name: {"id": 1, "name": name})
    monkeypatch.setattr(
        backend,
        "find_notes",
        lambda path, query, limit, offset: {
            "items": [],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": 7,
        },
    )
    monkeypatch.setattr(
        backend,
        "find_cards",
        lambda path, query, limit, offset: {
            "items": [],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": 11,
        },
    )

    result = CatalogService(backend).deck_stats("/tmp/test.anki2", name="Default")

    assert result == {
        "id": 1,
        "name": "Default",
        "note_count": 7,
        "card_count": 11,
        "due_count": 11,
        "new_count": 11,
        "learning_count": 11,
        "review_count": 11,
    }


@pytest.mark.unit
def test_model_validate_note_reports_missing_and_unknown_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "get_model_fields",
        lambda path, name: {"id": 10, "name": name, "fields": ["Front", "Back"]},
    )

    result = CatalogService(backend).validate_note(
        "/tmp/test.anki2",
        model_name="Basic",
        field_assignments=["Front=hello", "Extra=value"],
    )

    assert result["ok"] is False
    assert result["missing_fields"] == ["Back"]
    assert result["unknown_fields"] == ["Extra"]


@pytest.mark.unit
def test_collection_validate_reports_missing_collection(tmp_path: Path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = CollectionService(PythonAnkiBackend()).validate(str(collection_path))

    assert result["ok"] is False
    assert result["collection_path"] == str(collection_path.resolve())
    assert result["errors"]
    assert "does not exist" in result["errors"][0]


@pytest.mark.unit
def test_collection_lock_status_reports_best_effort_detection(tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    wal_path = tmp_path / "collection.anki2-wal"
    wal_path.write_text("wal")

    result = CollectionService(PythonAnkiBackend()).lock_status(str(collection_path))

    assert result["status"] == "possibly-open"
    assert result["confidence"] == "low"


@pytest.mark.unit
def test_media_list_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        MediaService(PythonAnkiBackend()).list(None)


@pytest.mark.unit
def test_media_service_resolve_path_strips_name(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "resolve_media_path",
        lambda path, name: {"name": name, "path": f"/tmp/{name}", "size": 1},
    )

    result = MediaService(backend).resolve_path("/tmp/test.anki2", name=" used.png ")

    assert result["name"] == "used.png"


@pytest.mark.unit
def test_media_service_ankiconnect_unsupported_error_passthrough() -> None:
    backend = PythonAnkiBackend()
    backend.name = "ankiconnect"  # type: ignore[attr-defined]

    def fail_check(path):  # noqa: ARG001
        raise BackendOperationUnsupportedError(
            "media.check is not supported by the ankiconnect backend",
            details={"backend": "ankiconnect", "operation": "media.check"},
        )

    backend.check_media = fail_check  # type: ignore[method-assign]

    with pytest.raises(BackendOperationUnsupportedError) as excinfo:
        MediaService(backend).check(None)

    assert excinfo.value.details == {"backend": "ankiconnect", "operation": "media.check"}


@pytest.mark.unit
def test_media_attach_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        MediaService(PythonAnkiBackend()).attach(
            "/tmp/test.anki2",
            source_path="/tmp/file.txt",
            name=None,
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
@proves("tag.apply", "safety")
def test_tag_apply_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        TagService(PythonAnkiBackend()).apply(
            "/tmp/test.anki2",
            note_id=101,
            tags=["review"],
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_ankiconnect_collection_validate_is_structured_unsupported() -> None:
    backend = PythonAnkiBackend()
    backend.name = "ankiconnect"  # type: ignore[attr-defined]

    with pytest.raises(BackendOperationUnsupportedError) as excinfo:
        CollectionService(backend).validate(None)

    assert excinfo.value.details == {
        "backend": "ankiconnect",
        "operation": "collection.validate",
    }


@pytest.mark.unit
def test_doctor_collection_is_structured_unsupported_on_ankiconnect() -> None:
    backend = PythonAnkiBackend()
    backend.name = "ankiconnect"  # type: ignore[attr-defined]

    with pytest.raises(BackendOperationUnsupportedError) as excinfo:
        DoctorService().collection_report(backend, None)

    assert excinfo.value.details == {
        "backend": "ankiconnect",
        "operation": "doctor.collection",
    }


@pytest.mark.unit
def test_doctor_safety_is_structured_unsupported_on_ankiconnect() -> None:
    backend = PythonAnkiBackend()
    backend.name = "ankiconnect"  # type: ignore[attr-defined]

    with pytest.raises(BackendOperationUnsupportedError) as excinfo:
        DoctorService().safety_report(backend, None)

    assert excinfo.value.details == {
        "backend": "ankiconnect",
        "operation": "doctor.safety",
    }


@pytest.mark.unit
def test_deck_get_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        CatalogService(PythonAnkiBackend()).get_deck(None, name="Default")


@pytest.mark.unit
def test_deck_stats_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        CatalogService(PythonAnkiBackend()).deck_stats(None, name="Default")


@pytest.mark.unit
def test_deck_create_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        DeckService(PythonAnkiBackend()).create(None, name="Default", dry_run=True, yes=False)


@pytest.mark.unit
def test_deck_create_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        DeckService(PythonAnkiBackend()).create(
            "/tmp/test.anki2",
            name="Default",
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_deck_rename_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        DeckService(PythonAnkiBackend()).rename(
            "/tmp/test.anki2",
            name="Default",
            new_name="French",
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_deck_delete_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        DeckService(PythonAnkiBackend()).delete(
            "/tmp/test.anki2",
            name="Default",
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_deck_reparent_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        DeckService(PythonAnkiBackend()).reparent(
            "/tmp/test.anki2",
            name="Default",
            new_parent="Parent",
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_deck_service_validates_names() -> None:
    service = DeckService(PythonAnkiBackend())

    with pytest.raises(ValidationError):
        service.create("/tmp/test.anki2", name=" ", dry_run=True, yes=False)

    with pytest.raises(ValidationError):
        service.rename(
            "/tmp/test.anki2",
            name="Default",
            new_name="Default",
            dry_run=True,
            yes=False,
        )

    with pytest.raises(ValidationError):
        service.reparent(
            "/tmp/test.anki2",
            name="Default",
            new_parent="Default",
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_ankiconnect_deck_list_allows_missing_collection_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = PythonAnkiBackend()
    backend.name = "ankiconnect"  # type: ignore[attr-defined]
    monkeypatch.setattr(backend, "list_decks", lambda path: [{"id": 1, "name": "Default"}])

    result = CatalogService(backend).list_decks(None)

    assert result == {"items": [{"id": 1, "name": "Default"}]}


@pytest.mark.unit
def test_model_get_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        CatalogService(PythonAnkiBackend()).get_model(None, name="Basic")


@pytest.mark.unit
def test_model_fields_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        CatalogService(PythonAnkiBackend()).get_model_fields(None, name="Basic")


@pytest.mark.unit
def test_model_templates_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        CatalogService(PythonAnkiBackend()).get_model_templates(None, name="Basic")


@pytest.mark.unit
def test_model_validate_note_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        CatalogService(PythonAnkiBackend()).validate_note(
            None,
            model_name="Basic",
            field_assignments=["Front=hello"],
        )


@pytest.mark.unit
def test_note_fields_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        NoteService(PythonAnkiBackend()).fields(None, note_id=101)


@pytest.mark.unit
def test_note_move_deck_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        NoteService(PythonAnkiBackend()).move_deck(
            None,
            note_id=101,
            deck_name="Default",
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_note_move_deck_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        NoteService(PythonAnkiBackend()).move_deck(
            "/tmp/test.anki2",
            note_id=101,
            deck_name="Default",
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_tag_list_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        CatalogService(PythonAnkiBackend()).list_tags(None)


@pytest.mark.unit
def test_tag_rename_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        TagService(PythonAnkiBackend()).rename(
            None,
            name="tag1",
            new_name="tag2",
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_tag_delete_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        TagService(PythonAnkiBackend()).delete(
            None,
            tags=["tag1"],
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_configure_anki_source_path_prefers_pylib(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = tmp_path / "anki"
    pylib = source_root / "pylib"
    pylib.mkdir(parents=True)
    monkeypatch.setenv("ANKI_SOURCE_PATH", str(source_root))

    resolved = configure_anki_source_path()

    assert resolved == str(pylib.resolve())


@pytest.mark.unit
def test_configure_anki_source_path_returns_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANKI_SOURCE_PATH", raising=False)

    assert configure_anki_source_path() is None


@pytest.mark.unit
def test_note_delete_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        NoteService(PythonAnkiBackend()).delete(
            "/tmp/test.anki2",
            note_id=101,
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_note_add_tags_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        NoteService(PythonAnkiBackend()).add_tags(
            "/tmp/test.anki2",
            note_id=101,
            tags=["tag1"],
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_note_remove_tags_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        NoteService(PythonAnkiBackend()).remove_tags(
            "/tmp/test.anki2",
            note_id=101,
            tags=["tag1"],
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_note_tag_commands_require_at_least_one_tag() -> None:
    service = NoteService(PythonAnkiBackend())

    with pytest.raises(ValidationError):
        service.add_tags("/tmp/test.anki2", note_id=101, tags=[], dry_run=True, yes=False)

    with pytest.raises(ValidationError):
        service.remove_tags("/tmp/test.anki2", note_id=101, tags=[], dry_run=True, yes=False)


@pytest.mark.unit
def test_tag_rename_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        TagService(PythonAnkiBackend()).rename(
            "/tmp/test.anki2",
            name="tag1",
            new_name="tag2",
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_tag_delete_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        TagService(PythonAnkiBackend()).delete(
            "/tmp/test.anki2",
            tags=["tag1"],
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_tag_delete_requires_at_least_one_tag() -> None:
    with pytest.raises(ValidationError):
        TagService(PythonAnkiBackend()).delete(
            "/tmp/test.anki2",
            tags=[],
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_tag_reparent_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        TagService(PythonAnkiBackend()).reparent(
            None,
            tags=["tag1"],
            new_parent="tag2",
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_tag_reparent_requires_confirmation_or_dry_run() -> None:
    with pytest.raises(UnsafeOperationError):
        TagService(PythonAnkiBackend()).reparent(
            "/tmp/test.anki2",
            tags=["tag1"],
            new_parent="tag2",
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_tag_reparent_requires_at_least_one_tag() -> None:
    with pytest.raises(ValidationError):
        TagService(PythonAnkiBackend()).reparent(
            "/tmp/test.anki2",
            tags=[],
            new_parent="tag2",
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_tag_rename_rejects_empty_or_same_names() -> None:
    service = TagService(PythonAnkiBackend())

    with pytest.raises(ValidationError):
        service.rename(
            "/tmp/test.anki2",
            name=" ",
            new_name="tag2",
            dry_run=True,
            yes=False,
        )

    with pytest.raises(ValidationError):
        service.rename(
            "/tmp/test.anki2",
            name="tag1",
            new_name=" ",
            dry_run=True,
            yes=False,
        )

    with pytest.raises(ValidationError):
        service.rename(
            "/tmp/test.anki2",
            name="tag1",
            new_name="tag1",
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_tag_reparent_rejects_parent_matching_moved_tag() -> None:
    with pytest.raises(ValidationError):
        TagService(PythonAnkiBackend()).reparent(
            "/tmp/test.anki2",
            tags=["tag1"],
            new_parent="tag1",
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_export_notes_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        ExportService(PythonAnkiBackend()).export_notes(
            None,
            query="deck:Default",
            limit=10,
            offset=0,
        )


@pytest.mark.unit
def test_search_count_uses_existing_backend_primitives(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "find_notes",
        lambda path, query, limit, offset: {
            "items": [{"id": 101}],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": 7,
        },
    )

    result = SearchService(backend).count("/tmp/test.anki2", kind="notes", query="deck:Default")

    assert result == {"kind": "notes", "query": "deck:Default", "total": 7}


@pytest.mark.unit
def test_search_preview_uses_existing_backend_primitives(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "find_cards",
        lambda path, query, limit, offset: {
            "items": [{"id": 201}],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": 1,
        },
    )
    monkeypatch.setattr(
        backend,
        "get_card",
        lambda path, card_id: {
            "id": card_id,
            "note_id": 101,
            "deck_id": 1,
            "template": "Card 1",
        },
    )

    result = SearchService(backend).preview(
        "/tmp/test.anki2",
        kind="cards",
        query="deck:Default",
        limit=5,
        offset=2,
    )

    assert result == {
        "kind": "cards",
        "items": [{"id": 201, "note_id": 101, "deck_id": 1, "template": "Card 1"}],
        "query": "deck:Default",
        "limit": 5,
        "offset": 2,
        "total": 1,
    }


@pytest.mark.unit
def test_import_notes_requires_collection_path(tmp_path: Path) -> None:
    input_path = tmp_path / "notes.json"
    input_path.write_text("[]")

    with pytest.raises(CollectionRequiredError):
        ImportService(PythonAnkiBackend()).import_notes(
            None,
            input_path=str(input_path),
            stdin_json=False,
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_import_notes_requires_confirmation_or_dry_run(tmp_path: Path) -> None:
    input_path = tmp_path / "notes.json"
    input_path.write_text("[]")

    with pytest.raises(UnsafeOperationError):
        ImportService(PythonAnkiBackend()).import_notes(
            "/tmp/test.anki2",
            input_path=str(input_path),
            stdin_json=False,
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_import_notes_validates_input_file_and_json(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not json")

    service = ImportService(PythonAnkiBackend())

    with pytest.raises(ValidationError):
        service.import_notes(
            "/tmp/test.anki2",
            input_path=str(missing),
            stdin_json=False,
            dry_run=True,
            yes=False,
        )

    with pytest.raises(ValidationError):
        service.import_notes(
            "/tmp/test.anki2",
            input_path=str(invalid),
            stdin_json=False,
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_import_notes_supports_stdin_json() -> None:
    backend = PythonAnkiBackend()
    service = ImportService(
        backend,
        stdin_reader=lambda: json.dumps(
            {
                "items": [
                    {
                        "deck": "Default",
                        "model": "Basic",
                        "fields": {"Front": "hello"},
                        "tags": [],
                    },
                ],
            },
        ),
    )
    backend.add_note = lambda path, deck_name, model_name, fields, tags, dry_run: {  # type: ignore[method-assign]
        "id": 999,
        "deck": deck_name,
        "model": model_name,
        "fields": fields,
        "tags": tags,
        "dry_run": dry_run,
    }

    result = service.import_notes(
        "/tmp/test.anki2",
        input_path=None,
        stdin_json=True,
        dry_run=True,
        yes=False,
    )

    assert result["source"] == "stdin"


@pytest.mark.unit
def test_import_notes_requires_exactly_one_input_source(tmp_path: Path) -> None:
    input_path = tmp_path / "notes.json"
    input_path.write_text("[]")
    service = ImportService(PythonAnkiBackend(), stdin_reader=lambda: "[]")

    with pytest.raises(ValidationError):
        service.import_notes(
            "/tmp/test.anki2",
            input_path=None,
            stdin_json=False,
            dry_run=True,
            yes=False,
        )

    with pytest.raises(ValidationError):
        service.import_notes(
            "/tmp/test.anki2",
            input_path=str(input_path),
            stdin_json=True,
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_export_notes_uses_existing_backend_primitives(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "find_notes",
        lambda path, query, limit, offset: {
            "items": [{"id": 101}],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": 1,
        },
    )
    monkeypatch.setattr(
        backend,
        "get_note",
        lambda path, note_id: {
            "id": note_id,
            "model": "Basic",
            "fields": {"Front": "hello"},
            "tags": [],
        },
    )

    result = ExportService(backend).export_notes(
        "/tmp/test.anki2",
        query="deck:Default",
        limit=10,
        offset=0,
    )

    assert result == {
        "items": [{"id": 101, "model": "Basic", "fields": {"Front": "hello"}, "tags": []}],
        "query": "deck:Default",
        "limit": 10,
        "offset": 0,
        "total": 1,
    }


@pytest.mark.unit
def test_export_cards_requires_collection_path() -> None:
    with pytest.raises(CollectionRequiredError):
        ExportService(PythonAnkiBackend()).export_cards(
            None,
            query="deck:Default",
            limit=10,
            offset=0,
        )


@pytest.mark.unit
def test_export_cards_uses_existing_backend_primitives(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "find_cards",
        lambda path, query, limit, offset: {
            "items": [{"id": 201}],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": 1,
        },
    )
    monkeypatch.setattr(
        backend,
        "get_card",
        lambda path, card_id: {
            "id": card_id,
            "note_id": 101,
            "deck_id": 1,
            "template": "Card 1",
        },
    )

    result = ExportService(backend).export_cards(
        "/tmp/test.anki2",
        query="deck:Default",
        limit=10,
        offset=0,
    )

    assert result == {
        "items": [{"id": 201, "note_id": 101, "deck_id": 1, "template": "Card 1"}],
        "query": "deck:Default",
        "limit": 10,
        "offset": 0,
        "total": 1,
    }


@pytest.mark.unit
def test_import_notes_uses_existing_backend_add_note(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "notes.json"
    input_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "deck": "Default",
                        "model": "Basic",
                        "fields": {"Front": "hello", "Back": "world"},
                        "tags": ["tag1"],
                    },
                ],
            },
        ),
    )

    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "add_note",
        lambda path, deck_name, model_name, fields, tags, dry_run: {
            "id": 999,
            "deck": deck_name,
            "model": model_name,
            "fields": fields,
            "tags": tags,
            "dry_run": dry_run,
        },
    )

    result = ImportService(backend).import_notes(
        "/tmp/test.anki2",
        input_path=str(input_path),
        stdin_json=False,
        dry_run=True,
        yes=False,
    )

    assert result == {
        "items": [
            {
                "id": 999,
                "deck": "Default",
                "model": "Basic",
                "fields": {"Front": "hello", "Back": "world"},
                "tags": ["tag1"],
                "dry_run": True,
            },
        ],
        "count": 1,
        "dry_run": True,
        "source": str(input_path.resolve()),
        "auto_backup_created": False,
        "auto_backup_name": None,
        "auto_backup_path": None,
    }


@pytest.mark.unit
def test_import_notes_includes_auto_backup_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "notes.json"
    input_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "deck": "Default",
                        "model": "Basic",
                        "fields": {"Front": "hello"},
                        "tags": [],
                    },
                ],
            },
        ),
    )

    backend = PythonAnkiBackend()
    service = ImportService(backend)
    monkeypatch.setattr(
        service.backup_service,
        "auto_backup",
        lambda path, enabled, dry_run: {
            "created": enabled and not dry_run,
            "name": "b.colpkg" if enabled and not dry_run else None,
            "path": "/tmp/b.colpkg" if enabled and not dry_run else None,
        },
    )
    monkeypatch.setattr(
        backend,
        "add_note",
        lambda path, deck_name, model_name, fields, tags, dry_run: {
            "id": 999,
            "deck": deck_name,
            "model": model_name,
            "fields": fields,
            "tags": tags,
            "dry_run": dry_run,
        },
    )

    result = service.import_notes(
        "/tmp/test.anki2",
        input_path=str(input_path),
        stdin_json=False,
        dry_run=False,
        yes=True,
    )

    assert result["auto_backup_created"] is True
    assert result["auto_backup_name"] == "b.colpkg"
    assert result["auto_backup_path"] == "/tmp/b.colpkg"


@pytest.mark.unit
def test_import_patch_requires_collection_path(tmp_path: Path) -> None:
    input_path = tmp_path / "patches.json"
    input_path.write_text("[]")

    with pytest.raises(CollectionRequiredError):
        ImportService(PythonAnkiBackend()).import_patch(
            None,
            input_path=str(input_path),
            stdin_json=False,
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_import_patch_requires_confirmation_or_dry_run(tmp_path: Path) -> None:
    input_path = tmp_path / "patches.json"
    input_path.write_text("[]")

    with pytest.raises(UnsafeOperationError):
        ImportService(PythonAnkiBackend()).import_patch(
            "/tmp/test.anki2",
            input_path=str(input_path),
            stdin_json=False,
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_import_patch_validates_input_file_and_json(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not json")

    service = ImportService(PythonAnkiBackend())

    with pytest.raises(ValidationError):
        service.import_patch(
            "/tmp/test.anki2",
            input_path=str(missing),
            stdin_json=False,
            dry_run=True,
            yes=False,
        )

    with pytest.raises(ValidationError):
        service.import_patch(
            "/tmp/test.anki2",
            input_path=str(invalid),
            stdin_json=False,
            dry_run=True,
            yes=False,
        )


@pytest.mark.unit
def test_import_patch_uses_existing_backend_update_note(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "patches.json"
    input_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": 101,
                        "fields": {"Back": "updated"},
                    },
                ],
            },
        ),
    )

    backend = PythonAnkiBackend()
    monkeypatch.setattr(
        backend,
        "update_note",
        lambda path, note_id, fields, dry_run: {
            "id": note_id,
            "model": "Basic",
            "fields": fields,
            "tags": ["tag1"],
            "dry_run": dry_run,
        },
    )

    result = ImportService(backend).import_patch(
        "/tmp/test.anki2",
        input_path=str(input_path),
        stdin_json=False,
        dry_run=True,
        yes=False,
    )

    assert result == {
        "items": [
            {
                "id": 101,
                "model": "Basic",
                "fields": {"Back": "updated"},
                "tags": ["tag1"],
                "dry_run": True,
            },
        ],
        "count": 1,
        "dry_run": True,
        "source": str(input_path.resolve()),
        "auto_backup_created": False,
        "auto_backup_name": None,
        "auto_backup_path": None,
    }


@pytest.mark.unit
def test_import_patch_includes_auto_backup_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "patches.json"
    input_path.write_text(json.dumps({"items": [{"id": 101, "fields": {"Back": "updated"}}]}))

    backend = PythonAnkiBackend()
    service = ImportService(backend)
    monkeypatch.setattr(
        service.backup_service,
        "auto_backup",
        lambda path, enabled, dry_run: {
            "created": enabled and not dry_run,
            "name": "b.colpkg" if enabled and not dry_run else None,
            "path": "/tmp/b.colpkg" if enabled and not dry_run else None,
        },
    )
    monkeypatch.setattr(
        backend,
        "update_note",
        lambda path, note_id, fields, dry_run: {
            "id": note_id,
            "model": "Basic",
            "fields": fields,
            "tags": [],
            "dry_run": dry_run,
        },
    )

    result = service.import_patch(
        "/tmp/test.anki2",
        input_path=str(input_path),
        stdin_json=False,
        dry_run=False,
        yes=True,
    )

    assert result["auto_backup_created"] is True
    assert result["auto_backup_name"] == "b.colpkg"
    assert result["auto_backup_path"] == "/tmp/b.colpkg"


@pytest.mark.unit
def test_import_patch_supports_stdin_json() -> None:
    backend = PythonAnkiBackend()
    service = ImportService(
        backend,
        stdin_reader=lambda: json.dumps({"items": [{"id": 101, "fields": {"Back": "updated"}}]}),
    )
    backend.update_note = lambda path, note_id, fields, dry_run: {  # type: ignore[method-assign]
        "id": note_id,
        "model": "Basic",
        "fields": fields,
        "tags": [],
        "dry_run": dry_run,
    }

    result = service.import_patch(
        "/tmp/test.anki2",
        input_path=None,
        stdin_json=True,
        dry_run=True,
        yes=False,
    )

    assert result["source"] == "stdin"


@pytest.mark.unit
def test_card_suspend_requires_confirmation_or_dry_run() -> None:
    from ankicli.app.services import CardService

    with pytest.raises(UnsafeOperationError):
        CardService(PythonAnkiBackend()).suspend(
            "/tmp/test.anki2",
            card_id=201,
            dry_run=False,
            yes=False,
        )


@pytest.mark.unit
def test_card_unsuspend_requires_confirmation_or_dry_run() -> None:
    from ankicli.app.services import CardService

    with pytest.raises(UnsafeOperationError):
        CardService(PythonAnkiBackend()).unsuspend(
            "/tmp/test.anki2",
            card_id=201,
            dry_run=False,
            yes=False,
        )
