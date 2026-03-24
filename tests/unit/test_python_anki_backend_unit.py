from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from ankicli.app.credentials import SyncCredential
from ankicli.app.errors import (
    AuthInvalidError,
    CardNotFoundError,
    CollectionNotFoundError,
    DeckNotFoundError,
    MediaNotFoundError,
    ModelNotFoundError,
    NoteNotFoundError,
    SyncConflictError,
    TagNotFoundError,
    ValidationError,
)
from ankicli.backends.python_anki import PythonAnkiBackend
from tests.proof import proves


class _FakeNote:
    def __init__(self) -> None:
        self.id = 101
        self.flush_count = 0
        self._fields = {
            "Front": "hello",
            "Back": "world",
        }
        self.tags = ["tag1", "tag2"]

    def items(self):
        return self._fields.items()

    def __setitem__(self, key: str, value: str) -> None:
        self._fields[key] = value

    def flush(self) -> None:
        self.flush_count += 1

    def note_type(self):
        return {"name": "Basic"}

    def cards(self):
        return [SimpleNamespace(id=201)]


class _FakeMediaNote:
    def __init__(self) -> None:
        self.id = 102
        self.tags: list[str] = []

    def items(self):
        return {
            "Front": '<img src="used.png">',
            "Back": "[sound:used.mp3]",
        }.items()


class _FakeCard:
    def __init__(self) -> None:
        self.nid = 101
        self.did = 55

    def template(self):
        return {"name": "Card 1"}


class _FakeCollection:
    def __init__(self, path: str) -> None:
        self.path = path
        self.closed = False
        self._deck_items = [
            SimpleNamespace(id=1, name="Default"),
            SimpleNamespace(id=2, name="Spanish"),
            SimpleNamespace(id=3, name="Spanish::Verbs"),
        ]
        self._created_decks: list[str] = []
        self._renamed_decks: list[tuple[int, str]] = []
        self._removed_decks: list[int] = []
        self.decks = SimpleNamespace(
            all_names_and_ids=self.all_deck_names_and_ids,
            id=self.create_deck,
            rename=self.rename_deck,
            remove=self.remove_deck,
        )
        self.models = SimpleNamespace(
            all_names_and_ids=lambda: [
                SimpleNamespace(id=10, name="Basic"),
                SimpleNamespace(id=11, name="Cloze"),
            ],
            by_name=lambda name: {
                "Basic": {
                    "id": 10,
                    "name": "Basic",
                    "flds": [{"name": "Front"}, {"name": "Back"}],
                    "tmpls": [{"name": "Card 1"}],
                },
                "Cloze": {
                    "id": 11,
                    "name": "Cloze",
                    "flds": [{"name": "Text"}, {"name": "Extra"}],
                    "tmpls": [{"name": "Cloze"}],
                },
            }.get(name),
            get=lambda model_id: {
                10: {
                    "id": 10,
                    "name": "Basic",
                    "flds": [{"name": "Front"}, {"name": "Back"}],
                    "tmpls": [{"name": "Card 1"}],
                },
                11: {
                    "id": 11,
                    "name": "Cloze",
                    "flds": [{"name": "Text"}, {"name": "Extra"}],
                    "tmpls": [{"name": "Cloze"}],
                },
            }.get(model_id),
        )
        self._note_ids = [101, 102, 103, 104]
        self._card_ids = [201, 202, 203, 204]
        self._notes = {
            101: _FakeNote(),
            102: _FakeMediaNote(),
        }
        self._cards = {
            201: _FakeCard(),
        }
        self._moved_cards: list[tuple[list[int], int]] = []
        self._added_note = None
        self._deleted_note_ids: list[int] = []
        self._suspended_card_ids: list[int] = []
        self._unsuspended_card_ids: list[int] = []
        self._bulk_added_tags: list[tuple[list[int], str]] = []
        self._bulk_removed_tags: list[tuple[list[int], str]] = []
        self._renamed_tags: list[tuple[str, str]] = []
        self._deleted_tags: list[str] = []
        self._reparented_tags: list[tuple[list[str], str]] = []
        self.tags = SimpleNamespace(
            all=lambda: ["tag2", "tag1"],
            bulk_add=self.bulk_add_tags,
            bulk_remove=self.bulk_remove_tags,
            rename=self.rename_tag,
            remove=self.remove_tags,
            reparent=self.reparent_tags,
        )
        self._sync_login_args = None
        self._sync_status_result = SimpleNamespace(required=1, new_endpoint="https://sync-2")
        self._sync_collection_result = SimpleNamespace(
            required=1,
            host_number=7,
            server_message="server ok",
            server_media_usn=12,
            new_endpoint="https://sync-3",
        )
        self._full_sync_calls: list[tuple[bool, int | None]] = []

    def name(self) -> str:
        return Path(self.path).stem

    def note_count(self) -> int:
        return 11

    def card_count(self) -> int:
        return 22

    def close(self) -> None:
        self.closed = True

    def find_notes(self, query: str) -> list[int]:
        assert query in {"deck:Default", ""}
        return self._note_ids

    def find_cards(self, query: str) -> list[int]:
        assert query == "deck:Default"
        return self._card_ids

    def get_note(self, note_id: int):
        return self._notes.get(note_id)

    def get_card(self, card_id: int):
        return self._cards.get(card_id)

    def add_note(self, note, deck_id: int):
        assert deck_id == 1
        note.id = 999
        self._added_note = note

    def new_note(self, model):
        assert model["name"] in {"Basic", "Cloze"}
        return _FakeNote()

    def remove_notes(self, note_ids):
        self._deleted_note_ids.extend(int(note_id) for note_id in note_ids)

    def set_deck(self, card_ids, deck_id: int):
        self._moved_cards.append(([int(card_id) for card_id in card_ids], int(deck_id)))

    def suspend_cards(self, card_ids):
        self._suspended_card_ids.extend(int(card_id) for card_id in card_ids)

    def unsuspend_cards(self, card_ids):
        self._unsuspended_card_ids.extend(int(card_id) for card_id in card_ids)

    def bulk_add_tags(self, note_ids, tags: str):
        self._bulk_added_tags.append(([int(note_id) for note_id in note_ids], tags))

    def bulk_remove_tags(self, note_ids, tags: str):
        self._bulk_removed_tags.append(([int(note_id) for note_id in note_ids], tags))

    def rename_tag(self, old: str, new: str):
        self._renamed_tags.append((old, new))

    def remove_tags(self, tags: str):
        self._deleted_tags.append(tags)

    def reparent_tags(self, tags, new_parent: str):
        self._reparented_tags.append(([str(tag) for tag in tags], new_parent))

    def sync_login(self, username: str, password: str, endpoint: str | None):
        self._sync_login_args = (username, password, endpoint)
        return SimpleNamespace(hkey="sync-hkey", endpoint=endpoint)

    def sync_status(self, auth):
        del auth
        return self._sync_status_result

    def sync_collection(self, auth, sync_media: bool):
        del auth, sync_media
        return self._sync_collection_result

    def full_upload_or_download(self, *, auth, server_usn: int | None, upload: bool):
        del auth
        self._full_sync_calls.append((upload, server_usn))

    def all_deck_names_and_ids(self):
        return list(self._deck_items)

    def create_deck(self, name: str) -> int:
        self._created_decks.append(name)
        new_id = max(int(deck.id) for deck in self._deck_items) + 1
        self._deck_items.append(SimpleNamespace(id=new_id, name=name))
        return new_id

    def rename_deck(self, deck_or_id, new_name: str) -> None:
        deck_id = int(deck_or_id.id) if hasattr(deck_or_id, "id") else int(deck_or_id)
        self._renamed_decks.append((deck_id, new_name))
        for deck in self._deck_items:
            if int(deck.id) == deck_id:
                deck.name = new_name
                break

    def remove_deck(self, deck_ids, cards_too: bool = False) -> None:
        del cards_too
        for deck_id in deck_ids:
            self._removed_decks.append(int(deck_id))


@pytest.mark.unit
def test_collection_info_rejects_missing_file(tmp_path: Path) -> None:
    backend = PythonAnkiBackend()
    collection_path = tmp_path / "missing.anki2"

    with pytest.raises(CollectionNotFoundError):
        backend.get_collection_info(collection_path)


@pytest.mark.unit
def test_collection_info_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.get_collection_info(collection_path)

    assert result == {
        "collection_path": str(collection_path.resolve()),
        "collection_name": "collection",
        "exists": True,
        "backend_available": True,
        "note_count": 11,
        "card_count": 22,
        "deck_count": 3,
        "model_count": 2,
    }
    assert fake_collection.closed is True


@pytest.mark.unit
@proves("auth.status", "backend_unit")
def test_auth_status_reports_credential_presence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()

    result = backend.auth_status(None, credential=SyncCredential(hkey="abc", endpoint="https://sync"))

    assert result == {
        "authenticated": True,
        "credential_backend": "macos-keychain",
        "credential_present": True,
        "backend_available": True,
        "supports_sync": True,
        "endpoint": "https://sync",
    }


@pytest.mark.unit
@proves("auth.logout", "backend_unit")
def test_logout_reports_backend_name() -> None:
    backend = PythonAnkiBackend()

    result = backend.logout(None)

    assert result == {"backend": "python-anki"}


@pytest.mark.unit
@proves("auth.login", "backend_unit")
def test_login_uses_sync_login_and_returns_sync_credential(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.login(
        collection_path,
        username="user",
        password="secret",
        endpoint="https://sync",
    )

    assert result == SyncCredential(hkey="sync-hkey", endpoint="https://sync")
    assert fake_collection._sync_login_args == ("user", "secret", "https://sync")


@pytest.mark.unit
@proves("sync.status", "backend_unit")
def test_sync_status_normalizes_required_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)
    original_import_module = importlib.import_module
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: SimpleNamespace(SyncAuth=lambda hkey: SimpleNamespace(hkey=hkey))
        if name == "anki.sync"
        else original_import_module(name),
    )

    result = backend.sync_status(collection_path, credential=SyncCredential(hkey="abc"))

    assert result == {
        "required": "normal_sync",
        "required_bool": True,
        "performed": False,
        "direction": None,
        "changes": {},
        "warnings": [],
        "conflicts": [],
        "new_endpoint": "https://sync-2",
    }


@pytest.mark.unit
@proves("sync.run", "backend_unit", "failure")
def test_sync_run_raises_conflict_on_full_sync_requirement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    fake_collection._sync_status_result = SimpleNamespace(required=2, new_endpoint=None)
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)
    original_import_module = importlib.import_module
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: SimpleNamespace(SyncAuth=lambda hkey: SimpleNamespace(hkey=hkey))
        if name == "anki.sync"
        else original_import_module(name),
    )

    with pytest.raises(SyncConflictError):
        backend.sync_run(collection_path, credential=SyncCredential(hkey="abc"))


@pytest.mark.unit
@proves("backup.create", "backend_unit")
def test_create_backup_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    backup_dir = tmp_path / "backups"
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    calls: list[tuple[str, bool, bool]] = []

    def create_backup(*, backup_folder: str, force: bool, wait_for_completion: bool) -> bool:
        calls.append((backup_folder, force, wait_for_completion))
        return True

    fake_collection.create_backup = create_backup  # type: ignore[attr-defined]
    fake_collection.await_backup_completion = lambda: calls.append(("await", False, False))  # type: ignore[attr-defined]
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.create_backup(collection_path, backup_folder=backup_dir, force=True)

    assert result == {"created": True}
    assert calls[0] == (str(backup_dir), True, True)
    assert calls[1] == ("await", False, False)


@pytest.mark.unit
@proves("backup.restore", "backend_unit")
def test_restore_backup_uses_import_collection_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    backup_path = tmp_path / "backup.colpkg"
    backup_path.write_text("backup")
    media_dir = tmp_path / "collection.media"
    media_dir.mkdir()
    media_db = tmp_path / "media.db2"
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    backend_calls: list[dict[str, str]] = []
    fake_collection.close_for_full_sync = lambda: None  # type: ignore[attr-defined]
    fake_collection._backend = SimpleNamespace(  # type: ignore[attr-defined]
        import_collection_package=lambda **kwargs: backend_calls.append(kwargs),
    )
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.restore_backup(
        collection_path,
        backup_path=backup_path,
        media_folder=media_dir,
        media_db_path=media_db,
    )

    assert result["restored"] is True
    assert backend_calls[0]["col_path"] == str(collection_path)
    assert backend_calls[0]["backup_path"] == str(backup_path.resolve())


@pytest.mark.unit
def test_sync_push_uses_full_upload_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)
    original_import_module = importlib.import_module
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: SimpleNamespace(SyncAuth=lambda hkey: SimpleNamespace(hkey=hkey))
        if name == "anki.sync"
        else original_import_module(name),
    )

    result = backend.sync_push(collection_path, credential=SyncCredential(hkey="abc"))

    assert result["direction"] == "push"
    assert fake_collection._full_sync_calls == [(True, None)]


@pytest.mark.unit
def test_login_maps_auth_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))

    def fail_login(username: str, password: str, endpoint: str | None):
        del username, password, endpoint
        raise RuntimeError("auth failed")

    fake_collection.sync_login = fail_login
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(AuthInvalidError):
        backend.login(collection_path, username="user", password="bad", endpoint=None)


@pytest.mark.unit
def test_list_decks_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.list_decks(collection_path)

    assert result == [
        {"id": 1, "name": "Default"},
        {"id": 2, "name": "Spanish"},
        {"id": 3, "name": "Spanish::Verbs"},
    ]
    assert fake_collection.closed is True


@pytest.mark.unit
def test_get_deck_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.get_deck(collection_path, name="Default")

    assert result == {"id": 1, "name": "Default"}
    assert fake_collection.closed is True


@pytest.mark.unit
def test_get_deck_raises_for_missing_deck(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(DeckNotFoundError):
        backend.get_deck(collection_path, name="Missing")


@pytest.mark.unit
def test_create_deck_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.create_deck(collection_path, name="French", dry_run=False)

    assert result == {
        "id": 4,
        "name": "French",
        "action": "create",
        "dry_run": False,
    }
    assert fake_collection._created_decks == ["French"]


@pytest.mark.unit
def test_create_deck_raises_for_existing_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(ValidationError):
        backend.create_deck(collection_path, name="Default", dry_run=True)


@pytest.mark.unit
def test_rename_deck_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.rename_deck(collection_path, name="Spanish", new_name="French", dry_run=False)

    assert result == {
        "id": 2,
        "name": "Spanish",
        "new_name": "French",
        "action": "rename",
        "dry_run": False,
    }
    assert fake_collection._renamed_decks == [(2, "French")]


@pytest.mark.unit
def test_delete_deck_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.delete_deck(collection_path, name="Spanish", dry_run=False)

    assert result == {
        "id": 2,
        "name": "Spanish",
        "action": "delete",
        "dry_run": False,
    }
    assert fake_collection._removed_decks == [2]


@pytest.mark.unit
def test_reparent_deck_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.reparent_deck(
        collection_path,
        name="Spanish::Verbs",
        new_parent="Default",
        dry_run=False,
    )

    assert result == {
        "id": 3,
        "name": "Spanish::Verbs",
        "new_parent": "Default",
        "new_name": "Default::Verbs",
        "action": "reparent",
        "dry_run": False,
    }
    assert fake_collection._renamed_decks == [(3, "Default::Verbs")]


@pytest.mark.unit
def test_list_models_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.list_models(collection_path)

    assert result == [
        {"id": 10, "name": "Basic"},
        {"id": 11, "name": "Cloze"},
    ]
    assert fake_collection.closed is True


@pytest.mark.unit
def test_get_model_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.get_model(collection_path, name="Basic")

    assert result == {
        "id": 10,
        "name": "Basic",
        "fields": ["Front", "Back"],
    }
    assert fake_collection.closed is True


@pytest.mark.unit
def test_get_model_raises_for_missing_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(ModelNotFoundError):
        backend.get_model(collection_path, name="Missing")


@pytest.mark.unit
def test_get_model_fields_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.get_model_fields(collection_path, name="Basic")

    assert result == {
        "id": 10,
        "name": "Basic",
        "fields": ["Front", "Back"],
    }


@pytest.mark.unit
def test_get_model_templates_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.get_model_templates(collection_path, name="Basic")

    assert result == {
        "id": 10,
        "name": "Basic",
        "templates": [{"name": "Card 1"}],
    }


@pytest.mark.unit
def test_list_tags_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.list_tags(collection_path)

    assert result == ["tag1", "tag2"]
    assert fake_collection.closed is True


@pytest.mark.unit
def test_rename_tag_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.rename_tag(
        collection_path,
        name="tag1",
        new_name="tag3",
        dry_run=False,
    )

    assert result == {
        "name": "tag1",
        "new_name": "tag3",
        "action": "rename",
        "dry_run": False,
    }
    assert fake_collection._renamed_tags == [("tag1", "tag3")]


@pytest.mark.unit
def test_rename_tag_dry_run_skips_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.rename_tag(
        collection_path,
        name="tag1",
        new_name="tag3",
        dry_run=True,
    )

    assert result == {
        "name": "tag1",
        "new_name": "tag3",
        "action": "rename",
        "dry_run": True,
    }
    assert fake_collection._renamed_tags == []


@pytest.mark.unit
def test_rename_tag_raises_for_missing_tag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(TagNotFoundError):
        backend.rename_tag(
            collection_path,
            name="missing",
            new_name="tag3",
            dry_run=True,
        )


@pytest.mark.unit
def test_delete_tags_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.delete_tags(
        collection_path,
        tags=["tag1", "tag2"],
        dry_run=False,
    )

    assert result == {
        "tags": ["tag1", "tag2"],
        "action": "delete",
        "dry_run": False,
    }
    assert fake_collection._deleted_tags == ["tag1 tag2"]


@pytest.mark.unit
def test_delete_tags_dry_run_skips_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.delete_tags(
        collection_path,
        tags=["tag1"],
        dry_run=True,
    )

    assert result == {
        "tags": ["tag1"],
        "action": "delete",
        "dry_run": True,
    }
    assert fake_collection._deleted_tags == []


@pytest.mark.unit
def test_delete_tags_raises_for_missing_tag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(TagNotFoundError):
        backend.delete_tags(
            collection_path,
            tags=["missing"],
            dry_run=True,
        )


@pytest.mark.unit
def test_reparent_tags_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.reparent_tags(
        collection_path,
        tags=["tag1"],
        new_parent="tag2",
        dry_run=False,
    )

    assert result == {
        "tags": ["tag1"],
        "new_parent": "tag2",
        "action": "reparent",
        "dry_run": False,
    }
    assert fake_collection._reparented_tags == [(["tag1"], "tag2")]


@pytest.mark.unit
def test_reparent_tags_dry_run_skips_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.reparent_tags(
        collection_path,
        tags=["tag1"],
        new_parent="tag2",
        dry_run=True,
    )

    assert result == {
        "tags": ["tag1"],
        "new_parent": "tag2",
        "action": "reparent",
        "dry_run": True,
    }
    assert fake_collection._reparented_tags == []


@pytest.mark.unit
def test_reparent_tags_raises_for_missing_tag_or_parent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(TagNotFoundError):
        backend.reparent_tags(
            collection_path,
            tags=["missing"],
            new_parent="tag2",
            dry_run=True,
        )

    with pytest.raises(TagNotFoundError):
        backend.reparent_tags(
            collection_path,
            tags=["tag1"],
            new_parent="missing",
            dry_run=True,
        )


@pytest.mark.unit
def test_find_notes_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.find_notes(
        collection_path,
        "deck:Default",
        limit=2,
        offset=1,
    )

    assert result == {
        "items": [{"id": 102}, {"id": 103}],
        "query": "deck:Default",
        "limit": 2,
        "offset": 1,
        "total": 4,
    }
    assert fake_collection.closed is True


@pytest.mark.unit
def test_find_cards_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.find_cards(
        collection_path,
        "deck:Default",
        limit=2,
        offset=1,
    )

    assert result == {
        "items": [{"id": 202}, {"id": 203}],
        "query": "deck:Default",
        "limit": 2,
        "offset": 1,
        "total": 4,
    }
    assert fake_collection.closed is True


@pytest.mark.unit
def test_get_note_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.get_note(collection_path, 101)

    assert result == {
        "id": 101,
        "model": "Basic",
        "fields": {
            "Front": "hello",
            "Back": "world",
        },
        "tags": ["tag1", "tag2"],
    }
    assert fake_collection.closed is True


@pytest.mark.unit
def test_get_note_raises_for_missing_note(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(NoteNotFoundError):
        backend.get_note(collection_path, 999)


@pytest.mark.unit
def test_get_note_fields_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.get_note_fields(collection_path, 101)

    assert result == {
        "id": 101,
        "model": "Basic",
        "fields": {
            "Front": "hello",
            "Back": "world",
        },
    }


@pytest.mark.unit
def test_get_card_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.get_card(collection_path, 201)

    assert result == {
        "id": 201,
        "note_id": 101,
        "deck_id": 55,
        "template": "Card 1",
    }
    assert fake_collection.closed is True


@pytest.mark.unit
def test_get_card_raises_for_missing_card(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(CardNotFoundError):
        backend.get_card(collection_path, 999)


@pytest.mark.unit
def test_add_note_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.add_note(
        collection_path,
        deck_name="Default",
        model_name="Basic",
        fields={"Front": "new", "Back": "answer"},
        tags=["tag3"],
        dry_run=False,
    )

    assert result == {
        "id": 999,
        "deck": "Default",
        "model": "Basic",
        "fields": {"Front": "new", "Back": "answer"},
        "tags": ["tag3"],
        "dry_run": False,
    }
    assert fake_collection._added_note is not None
    assert fake_collection._added_note._fields["Front"] == "new"
    assert fake_collection._added_note._fields["Back"] == "answer"
    assert "tag3" in fake_collection._added_note.tags


@pytest.mark.unit
def test_add_note_dry_run_skips_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.add_note(
        collection_path,
        deck_name="Default",
        model_name="Basic",
        fields={"Front": "preview"},
        tags=[],
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert fake_collection._added_note is None


@pytest.mark.unit
def test_add_note_raises_for_missing_deck(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(DeckNotFoundError):
        backend.add_note(
            collection_path,
            deck_name="Missing",
            model_name="Basic",
            fields={"Front": "hello"},
            tags=[],
            dry_run=True,
        )


@pytest.mark.unit
def test_add_note_raises_for_missing_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(ModelNotFoundError):
        backend.add_note(
            collection_path,
            deck_name="Default",
            model_name="Missing",
            fields={"Front": "hello"},
            tags=[],
            dry_run=True,
        )


@pytest.mark.unit
def test_update_note_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.update_note(
        collection_path,
        note_id=101,
        fields={"Back": "updated"},
        dry_run=False,
    )

    assert result == {
        "id": 101,
        "model": "Basic",
        "fields": {"Back": "updated"},
        "tags": ["tag1", "tag2"],
        "dry_run": False,
    }
    assert fake_collection._notes[101]._fields["Back"] == "updated"
    assert fake_collection._notes[101].flush_count == 1
    assert fake_collection.closed is True


@pytest.mark.unit
def test_update_note_dry_run_skips_flush(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.update_note(
        collection_path,
        note_id=101,
        fields={"Front": "preview"},
        dry_run=True,
    )

    assert result == {
        "id": 101,
        "model": "Basic",
        "fields": {"Front": "preview"},
        "tags": ["tag1", "tag2"],
        "dry_run": True,
    }
    assert fake_collection._notes[101].flush_count == 0


@pytest.mark.unit
def test_update_note_raises_for_missing_note(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(NoteNotFoundError):
        backend.update_note(
            collection_path,
            note_id=999,
            fields={"Back": "updated"},
            dry_run=True,
        )


@pytest.mark.unit
def test_delete_note_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.delete_note(
        collection_path,
        note_id=101,
        dry_run=False,
    )

    assert result == {
        "id": 101,
        "deleted": True,
        "dry_run": False,
    }
    assert fake_collection._deleted_note_ids == [101]
    assert fake_collection.closed is True


@pytest.mark.unit
def test_delete_note_dry_run_skips_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.delete_note(
        collection_path,
        note_id=101,
        dry_run=True,
    )

    assert result == {
        "id": 101,
        "deleted": False,
        "dry_run": True,
    }
    assert fake_collection._deleted_note_ids == []


@pytest.mark.unit
def test_delete_note_raises_for_missing_note(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(NoteNotFoundError):
        backend.delete_note(
            collection_path,
            note_id=999,
            dry_run=True,
        )


@pytest.mark.unit
def test_move_note_to_deck_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.move_note_to_deck(
        collection_path,
        note_id=101,
        deck_name="Spanish",
        dry_run=False,
    )

    assert result == {
        "id": 101,
        "deck": "Spanish",
        "card_ids": [201],
        "action": "move_deck",
        "dry_run": False,
    }
    assert fake_collection._moved_cards == [([201], 2)]


@pytest.mark.unit
def test_move_note_to_deck_dry_run_skips_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.move_note_to_deck(
        collection_path,
        note_id=101,
        deck_name="Spanish",
        dry_run=True,
    )

    assert result == {
        "id": 101,
        "deck": "Spanish",
        "card_ids": [201],
        "action": "move_deck",
        "dry_run": True,
    }
    assert fake_collection._moved_cards == []


@pytest.mark.unit
def test_add_tags_to_notes_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.add_tags_to_notes(
        collection_path,
        note_ids=[101],
        tags=["tag3", "tag4"],
        dry_run=False,
    )

    assert result == [{"id": 101, "tags": ["tag3", "tag4"], "action": "add", "dry_run": False}]
    assert fake_collection._bulk_added_tags == [([101], "tag3 tag4")]


@pytest.mark.unit
def test_add_tags_to_notes_dry_run_skips_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.add_tags_to_notes(
        collection_path,
        note_ids=[101],
        tags=["tag3"],
        dry_run=True,
    )

    assert result == [{"id": 101, "tags": ["tag3"], "action": "add", "dry_run": True}]
    assert fake_collection._bulk_added_tags == []


@pytest.mark.unit
def test_remove_tags_from_notes_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.remove_tags_from_notes(
        collection_path,
        note_ids=[101],
        tags=["tag1"],
        dry_run=False,
    )

    assert result == [{"id": 101, "tags": ["tag1"], "action": "remove", "dry_run": False}]
    assert fake_collection._bulk_removed_tags == [([101], "tag1")]


@pytest.mark.unit
def test_note_tag_mutation_raises_for_missing_note(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(NoteNotFoundError):
        backend.add_tags_to_notes(
            collection_path,
            note_ids=[999],
            tags=["tag1"],
            dry_run=True,
        )


@pytest.mark.unit
def test_suspend_cards_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.suspend_cards(
        collection_path,
        card_ids=[201],
        dry_run=False,
    )

    assert result == [
        {
            "id": 201,
            "suspended": True,
            "dry_run": False,
        },
    ]
    assert fake_collection._suspended_card_ids == [201]
    assert fake_collection.closed is True


@pytest.mark.unit
def test_suspend_cards_dry_run_skips_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.suspend_cards(
        collection_path,
        card_ids=[201],
        dry_run=True,
    )

    assert result == [
        {
            "id": 201,
            "suspended": True,
            "dry_run": True,
        },
    ]
    assert fake_collection._suspended_card_ids == []


@pytest.mark.unit
def test_unsuspend_cards_uses_collection_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.unsuspend_cards(
        collection_path,
        card_ids=[201],
        dry_run=False,
    )

    assert result == [
        {
            "id": 201,
            "suspended": False,
            "dry_run": False,
        },
    ]
    assert fake_collection._unsuspended_card_ids == [201]
    assert fake_collection.closed is True


@pytest.mark.unit
def test_unsuspend_cards_dry_run_skips_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.unsuspend_cards(
        collection_path,
        card_ids=[201],
        dry_run=True,
    )

    assert result == [
        {
            "id": 201,
            "suspended": False,
            "dry_run": True,
        },
    ]
    assert fake_collection._unsuspended_card_ids == []


@pytest.mark.unit
def test_suspend_cards_raises_for_missing_card(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    with pytest.raises(CardNotFoundError):
        backend.suspend_cards(
            collection_path,
            card_ids=[999],
            dry_run=True,
        )


@pytest.mark.unit
def test_list_media_returns_sorted_items(tmp_path: Path) -> None:
    backend = PythonAnkiBackend()
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    media_dir = tmp_path / "collection.media"
    media_dir.mkdir()
    (media_dir / "b.txt").write_text("b")
    (media_dir / "a.txt").write_text("aa")

    result = backend.list_media(collection_path)

    assert [item["name"] for item in result] == ["a.txt", "b.txt"]
    assert result[0]["size"] == 2


@pytest.mark.unit
def test_check_media_reports_counts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    media_dir = tmp_path / "collection.media"
    media_dir.mkdir()
    (media_dir / "used.png").write_text("u")
    (media_dir / "used.mp3").write_text("s")
    (media_dir / "orphan.txt").write_text("o")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.check_media(collection_path)

    assert result["exists"] is True
    assert result["file_count"] == 3
    assert result["referenced_count"] == 2
    assert result["orphaned_count"] == 1
    assert result["missing_count"] == 0


@pytest.mark.unit
def test_list_orphaned_media_returns_only_unreferenced_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    media_dir = tmp_path / "collection.media"
    media_dir.mkdir()
    (media_dir / "used.png").write_text("u")
    (media_dir / "used.mp3").write_text("s")
    (media_dir / "orphan.txt").write_text("o")

    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)

    result = backend.list_orphaned_media(collection_path)

    assert result == [
        {
            "name": "orphan.txt",
            "path": str((media_dir / "orphan.txt").resolve()),
            "size": 1,
        },
    ]


@pytest.mark.unit
def test_resolve_media_path_raises_for_missing_media(tmp_path: Path) -> None:
    backend = PythonAnkiBackend()
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    (tmp_path / "collection.media").mkdir()

    with pytest.raises(MediaNotFoundError):
        backend.resolve_media_path(collection_path, name="missing.png")


@pytest.mark.unit
def test_attach_media_dry_run_reports_target_without_copy(tmp_path: Path) -> None:
    backend = PythonAnkiBackend()
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    source_path = tmp_path / "upload.txt"
    source_path.write_text("hello")

    result = backend.attach_media(
        collection_path,
        source_path=source_path,
        name="renamed.txt",
        dry_run=True,
    )

    assert result["name"] == "renamed.txt"
    assert result["action"] == "attach"
    assert result["dry_run"] is True
    assert not (tmp_path / "collection.media" / "renamed.txt").exists()


@pytest.mark.unit
def test_attach_media_copies_file(tmp_path: Path) -> None:
    backend = PythonAnkiBackend()
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    source_path = tmp_path / "upload.txt"
    source_path.write_text("hello")

    result = backend.attach_media(
        collection_path,
        source_path=source_path,
        name=None,
        dry_run=False,
    )

    target_path = tmp_path / "collection.media" / "upload.txt"
    assert target_path.read_text() == "hello"
    assert result["path"] == str(target_path.resolve())
