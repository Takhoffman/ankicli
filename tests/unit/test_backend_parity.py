from __future__ import annotations

import http.client
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ankicli.app.services import CatalogService, ExportService, ImportService, NoteService
from ankicli.backends.ankiconnect import AnkiConnectBackend
from ankicli.backends.python_anki import PythonAnkiBackend
from tests.proof import proves


class _FakeNote:
    def __init__(self) -> None:
        self.id = 101
        self.flush_count = 0
        self._fields = {"Front": "hello", "Back": "world"}
        self.tags = ["tag1"]

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
        self.decks = SimpleNamespace(
            all_names_and_ids=lambda: [
                SimpleNamespace(id=1, name="Default"),
                SimpleNamespace(id=2, name="Spanish"),
            ],
        )
        self.models = SimpleNamespace(
            all_names_and_ids=lambda: [SimpleNamespace(id=10, name="Basic")],
            by_name=lambda name: {
                "Basic": {
                    "id": 10,
                    "name": "Basic",
                    "flds": [{"name": "Front"}, {"name": "Back"}],
                    "tmpls": [{"name": "Card 1"}],
                },
            }.get(name),
            get=lambda model_id: {
                10: {
                    "id": 10,
                    "name": "Basic",
                    "flds": [{"name": "Front"}, {"name": "Back"}],
                    "tmpls": [{"name": "Card 1"}],
                },
            }.get(model_id),
        )
        self.tags = SimpleNamespace(
            all=lambda: ["tag1"],
            bulk_add=lambda note_ids, tags: None,
            bulk_remove=lambda note_ids, tags: None,
        )
        self._note = _FakeNote()
        self._card = _FakeCard()

    def name(self) -> str:
        return Path(self.path).stem

    def note_count(self) -> int:
        return 1

    def card_count(self) -> int:
        return 1

    def close(self) -> None:
        self.closed = True

    def find_notes(self, query: str) -> list[int]:
        assert query in {"", 'deck:"Default"'}
        return [101]

    def find_cards(self, query: str) -> list[int]:
        assert query in {"", 'deck:"Default"'}
        return [201]

    def get_note(self, note_id: int):
        return self._note if note_id == 101 else None

    def get_card(self, card_id: int):
        return self._card if card_id == 201 else None

    def add_note(self, note, deck_id: int):
        note.id = 999

    def new_note(self, model):
        return _FakeNote()

    def suspend_cards(self, card_ids):
        return None

    def unsuspend_cards(self, card_ids):
        return None

    def bulk_add_tags(self, note_ids, tags: str):
        return None

    def bulk_remove_tags(self, note_ids, tags: str):
        return None

    def set_deck(self, card_ids, deck_id: int):
        return None


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self.payload


class _FakeConnection:
    def __init__(self, responses: dict[str, dict]) -> None:
        self._responses = responses
        self._action = ""

    def request(self, method: str, path: str, body: bytes, headers: dict[str, str]) -> None:
        del method, path, headers
        self._action = json.loads(body.decode())["action"]

    def getresponse(self) -> _FakeResponse:
        return _FakeResponse(self._responses[self._action])

    def close(self) -> None:
        return None


def _install_python_backend(
    monkeypatch: pytest.MonkeyPatch,
    collection_path: Path,
) -> PythonAnkiBackend:
    collection_path.write_text("fixture")
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "anki" else None,
    )
    backend = PythonAnkiBackend()
    fake_collection = _FakeCollection(str(collection_path))
    monkeypatch.setattr(backend, "_load_collection_type", lambda: lambda path: fake_collection)
    return backend


def _install_ankiconnect_backend(monkeypatch: pytest.MonkeyPatch) -> AnkiConnectBackend:
    responses = {
        "version": {"result": 6, "error": None},
        "deckNamesAndIds": {"result": {"Default": 1}, "error": None},
        "modelNamesAndIds": {"result": {"Basic": 10}, "error": None},
        "modelFieldNames": {"result": ["Front", "Back"], "error": None},
        "modelTemplates": {"result": {"Card 1": {"Front": "{{Front}}"}} , "error": None},
        "getTags": {"result": ["tag1"], "error": None},
        "findNotes": {"result": [101], "error": None},
        "findCards": {"result": [201], "error": None},
        "notesInfo": {
            "result": [
                {
                    "noteId": 101,
                    "modelName": "Basic",
                    "tags": ["tag1"],
                    "fields": {
                        "Front": {"value": "hello", "order": 0},
                        "Back": {"value": "world", "order": 1},
                    },
                },
            ],
            "error": None,
        },
        "cardsInfo": {
            "result": [
                {
                    "cardId": 201,
                    "note": 101,
                    "deckName": "Default",
                    "fieldOrder": 0,
                },
            ],
            "error": None,
        },
        "canAddNotes": {"result": [True], "error": None},
        "addTags": {"result": None, "error": None},
        "removeTags": {"result": None, "error": None},
        "suspend": {"result": True, "error": None},
        "unsuspend": {"result": True, "error": None},
        "updateNoteFields": {"result": None, "error": None},
        "changeDeck": {"result": None, "error": None},
    }

    def fake_connection(host: str, port: int, timeout: int) -> _FakeConnection:  # noqa: ARG001
        return _FakeConnection(responses)

    monkeypatch.setattr(http.client, "HTTPConnection", fake_connection)
    return AnkiConnectBackend()


@pytest.mark.unit
def test_shared_backend_capabilities_use_same_operation_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    python_backend = _install_python_backend(monkeypatch, Path("/tmp/parity-cap.anki2"))
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_ops = python_backend.backend_capabilities().supported_operations
    ankiconnect_ops = ankiconnect_backend.backend_capabilities().supported_operations

    assert set(python_ops) == set(ankiconnect_ops)


@pytest.mark.unit
@proves("collection.info", "parity")
def test_collection_info_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.get_collection_info(collection_path)
    ankiconnect_result = ankiconnect_backend.get_collection_info(Path("."))

    required_keys = {
        "collection_path",
        "collection_name",
        "exists",
        "backend_available",
        "note_count",
        "card_count",
        "deck_count",
        "model_count",
    }
    assert required_keys <= set(python_result)
    assert required_keys <= set(ankiconnect_result)


@pytest.mark.unit
@proves("note.get", "parity")
def test_note_get_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.get_note(collection_path, 101)
    ankiconnect_result = ankiconnect_backend.get_note(Path("."), 101)

    assert set(python_result) == {"id", "model", "fields", "tags"}
    assert set(ankiconnect_result) == {"id", "model", "fields", "tags"}


@pytest.mark.unit
def test_card_get_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.get_card(collection_path, 201)
    ankiconnect_result = ankiconnect_backend.get_card(Path("."), 201)

    assert set(python_result) == {"id", "note_id", "deck_id", "template"}
    assert set(ankiconnect_result) == {"id", "note_id", "deck_id", "template"}


@pytest.mark.unit
def test_note_add_dry_run_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.add_note(
        collection_path,
        deck_name="Default",
        model_name="Basic",
        fields={"Front": "hello"},
        tags=["tag1"],
        dry_run=True,
    )
    ankiconnect_result = ankiconnect_backend.add_note(
        Path("."),
        deck_name="Default",
        model_name="Basic",
        fields={"Front": "hello"},
        tags=["tag1"],
        dry_run=True,
    )

    assert set(python_result) == {"id", "deck", "model", "fields", "tags", "dry_run"}
    assert set(ankiconnect_result) == {"id", "deck", "model", "fields", "tags", "dry_run"}


@pytest.mark.unit
def test_model_get_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.get_model(collection_path, name="Basic")
    ankiconnect_result = ankiconnect_backend.get_model(Path("."), name="Basic")

    assert set(python_result) == {"id", "name", "fields"}
    assert set(ankiconnect_result) == {"id", "name", "fields"}


@pytest.mark.unit
def test_model_fields_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.get_model_fields(collection_path, name="Basic")
    ankiconnect_result = ankiconnect_backend.get_model_fields(Path("."), name="Basic")

    assert set(python_result) == {"id", "name", "fields"}
    assert set(ankiconnect_result) == {"id", "name", "fields"}


@pytest.mark.unit
def test_model_templates_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.get_model_templates(collection_path, name="Basic")
    ankiconnect_result = ankiconnect_backend.get_model_templates(Path("."), name="Basic")

    assert set(python_result) == {"id", "name", "templates"}
    assert set(ankiconnect_result) == {"id", "name", "templates"}


@pytest.mark.unit
def test_deck_stats_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = CatalogService(python_backend).deck_stats(str(collection_path), name="Default")
    ankiconnect_result = CatalogService(ankiconnect_backend).deck_stats(None, name="Default")

    assert set(python_result) == {"id", "name", "note_count", "card_count"}
    assert set(ankiconnect_result) == {"id", "name", "note_count", "card_count"}


@pytest.mark.unit
def test_search_notes_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.find_notes(collection_path, "", limit=10, offset=0)
    ankiconnect_result = ankiconnect_backend.find_notes(Path("."), "", limit=10, offset=0)

    assert set(python_result) == {"items", "query", "limit", "offset", "total"}
    assert set(ankiconnect_result) == {"items", "query", "limit", "offset", "total"}


@pytest.mark.unit
def test_search_cards_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.find_cards(collection_path, "", limit=10, offset=0)
    ankiconnect_result = ankiconnect_backend.find_cards(Path("."), "", limit=10, offset=0)

    assert set(python_result) == {"items", "query", "limit", "offset", "total"}
    assert set(ankiconnect_result) == {"items", "query", "limit", "offset", "total"}


@pytest.mark.unit
def test_note_update_dry_run_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.update_note(
        collection_path,
        note_id=101,
        fields={"Back": "updated"},
        dry_run=True,
    )
    ankiconnect_result = ankiconnect_backend.update_note(
        Path("."),
        note_id=101,
        fields={"Back": "updated"},
        dry_run=True,
    )

    assert set(python_result) == {"id", "model", "fields", "tags", "dry_run"}
    assert set(ankiconnect_result) == {"id", "model", "fields", "tags", "dry_run"}


@pytest.mark.unit
def test_note_add_tags_dry_run_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.add_tags_to_notes(
        collection_path,
        note_ids=[101],
        tags=["tag2"],
        dry_run=True,
    )[0]
    ankiconnect_result = ankiconnect_backend.add_tags_to_notes(
        Path("."),
        note_ids=[101],
        tags=["tag2"],
        dry_run=True,
    )[0]

    assert set(python_result) == {"id", "tags", "action", "dry_run"}
    assert set(ankiconnect_result) == {"id", "tags", "action", "dry_run"}


@pytest.mark.unit
def test_note_remove_tags_dry_run_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.remove_tags_from_notes(
        collection_path,
        note_ids=[101],
        tags=["tag1"],
        dry_run=True,
    )[0]
    ankiconnect_result = ankiconnect_backend.remove_tags_from_notes(
        Path("."),
        note_ids=[101],
        tags=["tag1"],
        dry_run=True,
    )[0]

    assert set(python_result) == {"id", "tags", "action", "dry_run"}
    assert set(ankiconnect_result) == {"id", "tags", "action", "dry_run"}


@pytest.mark.unit
def test_note_fields_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = NoteService(python_backend).fields(str(collection_path), note_id=101)
    ankiconnect_result = NoteService(ankiconnect_backend).fields(None, note_id=101)

    assert set(python_result) == {"id", "model", "fields"}
    assert set(ankiconnect_result) == {"id", "model", "fields"}


@pytest.mark.unit
def test_note_move_deck_dry_run_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = NoteService(python_backend).move_deck(
        str(collection_path),
        note_id=101,
        deck_name="Default",
        dry_run=True,
        yes=False,
    )
    ankiconnect_result = NoteService(ankiconnect_backend).move_deck(
        None,
        note_id=101,
        deck_name="Default",
        dry_run=True,
        yes=False,
    )

    assert set(python_result) == {"id", "deck", "card_ids", "action", "dry_run"}
    assert set(ankiconnect_result) == {"id", "deck", "card_ids", "action", "dry_run"}


@pytest.mark.unit
@proves("export.notes", "parity")
def test_export_notes_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = ExportService(python_backend).export_notes(
        str(collection_path),
        query="",
        limit=10,
        offset=0,
    )
    ankiconnect_result = ExportService(ankiconnect_backend).export_notes(
        None,
        query="",
        limit=10,
        offset=0,
    )

    assert set(python_result) == {"items", "query", "limit", "offset", "total"}
    assert set(ankiconnect_result) == {"items", "query", "limit", "offset", "total"}


@pytest.mark.unit
def test_export_cards_shared_shape_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = ExportService(python_backend).export_cards(
        str(collection_path),
        query="",
        limit=10,
        offset=0,
    )
    ankiconnect_result = ExportService(ankiconnect_backend).export_cards(
        None,
        query="",
        limit=10,
        offset=0,
    )

    assert set(python_result) == {"items", "query", "limit", "offset", "total"}
    assert set(ankiconnect_result) == {"items", "query", "limit", "offset", "total"}


@pytest.mark.unit
def test_import_notes_stdin_dry_run_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)
    payload = json.dumps(
        {
            "items": [
                {
                    "deck": "Default",
                    "model": "Basic",
                    "fields": {"Front": "hello", "Back": "world"},
                    "tags": [],
                },
            ],
        },
    )

    python_result = ImportService(
        python_backend,
        stdin_reader=lambda: payload,
    ).import_notes(
        str(collection_path),
        input_path=None,
        stdin_json=True,
        dry_run=True,
        yes=False,
    )
    ankiconnect_result = ImportService(
        ankiconnect_backend,
        stdin_reader=lambda: payload,
    ).import_notes(
        None,
        input_path=None,
        stdin_json=True,
        dry_run=True,
        yes=False,
    )

    assert set(python_result) == {"items", "count", "dry_run", "source"}
    assert set(ankiconnect_result) == {"items", "count", "dry_run", "source"}


@pytest.mark.unit
@proves("import.patch", "parity")
def test_import_patch_stdin_dry_run_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)
    payload = json.dumps({"items": [{"id": 101, "fields": {"Back": "updated"}}]})

    python_result = ImportService(
        python_backend,
        stdin_reader=lambda: payload,
    ).import_patch(
        str(collection_path),
        input_path=None,
        stdin_json=True,
        dry_run=True,
        yes=False,
    )
    ankiconnect_result = ImportService(
        ankiconnect_backend,
        stdin_reader=lambda: payload,
    ).import_patch(
        None,
        input_path=None,
        stdin_json=True,
        dry_run=True,
        yes=False,
    )

    assert set(python_result) == {"items", "count", "dry_run", "source"}
    assert set(ankiconnect_result) == {"items", "count", "dry_run", "source"}


@pytest.mark.unit
def test_card_suspend_dry_run_shared_shape_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_path = tmp_path / "collection.anki2"
    python_backend = _install_python_backend(monkeypatch, collection_path)
    ankiconnect_backend = _install_ankiconnect_backend(monkeypatch)

    python_result = python_backend.suspend_cards(
        collection_path,
        card_ids=[201],
        dry_run=True,
    )[0]
    ankiconnect_result = ankiconnect_backend.suspend_cards(
        Path("."),
        card_ids=[201],
        dry_run=True,
    )[0]

    assert set(python_result) == {"id", "suspended", "dry_run"}
    assert set(ankiconnect_result) == {"id", "suspended", "dry_run"}
