from __future__ import annotations

import http.client
import json
from pathlib import Path

import pytest

from ankicli.app.errors import BackendOperationUnsupportedError, NoteNotFoundError
from ankicli.backends.ankiconnect import AnkiConnectBackend
from tests.proof import proves


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self.payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb


class _FakeConnection:
    def __init__(self, responses: dict[str, dict]) -> None:
        self._responses = responses
        self._action = ""

    def request(self, method: str, path: str, body: bytes, headers: dict[str, str]) -> None:
        del method, path, headers
        payload = json.loads(body.decode())
        self._action = payload["action"]

    def getresponse(self) -> _FakeResponse:
        return _FakeResponse(self._responses[self._action])

    def close(self) -> None:
        return None


def _install_http_connection(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[str, dict],
) -> None:
    def fake_connection(host: str, port: int, timeout: int) -> _FakeConnection:  # noqa: ARG001
        return _FakeConnection(responses)

    monkeypatch.setattr(http.client, "HTTPConnection", fake_connection)


@pytest.mark.unit
def test_backend_capabilities_reports_available_when_version_responds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_http_connection(monkeypatch, {"version": {"result": 5, "error": None}})

    capabilities = AnkiConnectBackend().backend_capabilities()

    assert capabilities.backend == "ankiconnect"
    assert capabilities.available is True
    assert capabilities.supports_live_desktop is True
    assert capabilities.supported_operations["note.delete"] is False
    assert capabilities.supported_operations["note.add"] is True
    assert capabilities.supported_operations["deck.create"] is True
    assert capabilities.supported_operations["deck.delete"] is True
    assert capabilities.supported_operations["media.attach"] is True
    assert capabilities.supported_operations["media.list"] is False
    assert capabilities.supported_operations["auth.status"] is False
    assert capabilities.supported_operations["sync.run"] is False


@pytest.mark.unit
@proves("backend.capabilities", "failure")
@proves("backend.info", "failure")
def test_backend_capabilities_reports_unavailable_on_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_connection(host: str, port: int, timeout: int):  # noqa: ARG001
        raise OSError("connection refused")

    monkeypatch.setattr(http.client, "HTTPConnection", fake_connection)

    capabilities = AnkiConnectBackend().backend_capabilities()

    assert capabilities.available is False
    assert capabilities.supported_operations["tag.rename"] is False


@pytest.mark.unit
@proves("deck.list", "backend_unit")
def test_list_decks_parses_deck_names_and_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(
        monkeypatch,
        {
            "deckNamesAndIds": {"result": {"Default": 1, "Spanish": 2}, "error": None},
            "modelNamesAndIds": {"result": {"Basic": 10}, "error": None},
            "modelFieldNames": {"result": ["Front", "Back"], "error": None},
            "modelTemplates": {"result": {"Card 1": {"Front": "{{Front}}"}}, "error": None},
        },
    )

    result = AnkiConnectBackend().list_decks(Path("."))

    assert result == [{"id": 1, "name": "Default"}, {"id": 2, "name": "Spanish"}]


@pytest.mark.unit
def test_get_note_parses_notes_info(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(
        monkeypatch,
        {
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
        },
    )

    result = AnkiConnectBackend().get_note(Path("."), 101)

    assert result == {
        "id": 101,
        "model": "Basic",
        "fields": {"Front": "hello", "Back": "world"},
        "tags": ["tag1"],
    }


@pytest.mark.unit
def test_get_note_raises_for_missing_note(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(monkeypatch, {"notesInfo": {"result": [], "error": None}})

    with pytest.raises(NoteNotFoundError):
        AnkiConnectBackend().get_note(Path("."), 999)


@pytest.mark.unit
def test_get_note_fields_parses_note_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(
        monkeypatch,
        {
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
        },
    )

    result = AnkiConnectBackend().get_note_fields(Path("."), 101)

    assert result == {
        "id": 101,
        "model": "Basic",
        "fields": {"Front": "hello", "Back": "world"},
    }


@pytest.mark.unit
def test_get_model_fields_parses_ankiconnect_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(
        monkeypatch,
        {
            "modelNamesAndIds": {"result": {"Basic": 10}, "error": None},
            "modelFieldNames": {"result": ["Front", "Back"], "error": None},
        },
    )

    result = AnkiConnectBackend().get_model_fields(Path("."), name="Basic")

    assert result == {"id": 10, "name": "Basic", "fields": ["Front", "Back"]}


@pytest.mark.unit
def test_get_model_templates_parses_ankiconnect_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(
        monkeypatch,
        {
            "modelNamesAndIds": {"result": {"Basic": 10}, "error": None},
            "modelTemplates": {"result": {"Card 1": {"Front": "{{Front}}"}}, "error": None},
        },
    )

    result = AnkiConnectBackend().get_model_templates(Path("."), name="Basic")

    assert result == {"id": 10, "name": "Basic", "templates": [{"name": "Card 1"}]}


@pytest.mark.unit
def test_media_list_still_raises_structured_unsupported_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_http_connection(monkeypatch, {"version": {"result": 5, "error": None}})
    backend = AnkiConnectBackend()

    with pytest.raises(BackendOperationUnsupportedError) as excinfo:
        backend.list_media(Path("."))

    assert excinfo.value.details == {"backend": "ankiconnect", "operation": "media.list"}


@pytest.mark.unit
def test_auth_and_sync_methods_raise_structured_unsupported_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_http_connection(monkeypatch, {"version": {"result": 5, "error": None}})
    backend = AnkiConnectBackend()

    with pytest.raises(BackendOperationUnsupportedError) as auth_excinfo:
        backend.auth_status(None, credential=None)

    assert auth_excinfo.value.details == {
        "backend": "ankiconnect",
        "operation": "auth.status",
    }

    with pytest.raises(BackendOperationUnsupportedError) as sync_excinfo:
        backend.sync_run(None, credential=None)

    assert sync_excinfo.value.details == {
        "backend": "ankiconnect",
        "operation": "sync.run",
    }


@pytest.mark.unit
def test_add_note_dry_run_uses_can_add_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(monkeypatch, {"canAddNotes": {"result": [True], "error": None}})

    result = AnkiConnectBackend().add_note(
        Path("."),
        deck_name="Default",
        model_name="Basic",
        fields={"Front": "hello"},
        tags=["tag1"],
        dry_run=True,
    )

    assert result == {
        "id": None,
        "deck": "Default",
        "model": "Basic",
        "fields": {"Front": "hello"},
        "tags": ["tag1"],
        "dry_run": True,
    }


@pytest.mark.unit
def test_create_deck_uses_ankiconnect_create_deck(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(
        monkeypatch,
        {
            "deckNamesAndIds": {"result": {"Default": 1}, "error": None},
            "createDeck": {"result": 99, "error": None},
        },
    )

    result = AnkiConnectBackend().create_deck(Path("."), name="Japanese", dry_run=False)

    assert result == {
        "id": 99,
        "name": "Japanese",
        "action": "create",
        "dry_run": False,
    }


@pytest.mark.unit
def test_create_deck_dry_run_validates_name_without_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_http_connection(
        monkeypatch,
        {
            "deckNamesAndIds": {"result": {"Default": 1}, "error": None},
        },
    )

    result = AnkiConnectBackend().create_deck(Path("."), name="Japanese", dry_run=True)

    assert result == {
        "id": None,
        "name": "Japanese",
        "action": "create",
        "dry_run": True,
    }


@pytest.mark.unit
def test_delete_deck_uses_ankiconnect_delete_decks(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(
        monkeypatch,
        {
            "deckNamesAndIds": {"result": {"Default": 1, "Japanese": 99}, "error": None},
            "deleteDecks": {"result": None, "error": None},
        },
    )

    result = AnkiConnectBackend().delete_deck(Path("."), name="Japanese", dry_run=False)

    assert result == {
        "id": 99,
        "name": "Japanese",
        "action": "delete",
        "dry_run": False,
    }


@pytest.mark.unit
def test_delete_deck_dry_run_validates_name_without_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_http_connection(
        monkeypatch,
        {
            "deckNamesAndIds": {"result": {"Default": 1, "Japanese": 99}, "error": None},
        },
    )

    result = AnkiConnectBackend().delete_deck(Path("."), name="Japanese", dry_run=True)

    assert result == {
        "id": 99,
        "name": "Japanese",
        "action": "delete",
        "dry_run": True,
    }


@pytest.mark.unit
def test_attach_media_uses_store_media_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "hello.mp3"
    source.write_bytes(b"audio-bytes")
    _install_http_connection(
        monkeypatch,
        {
            "storeMediaFile": {"result": "hello.mp3", "error": None},
        },
    )

    result = AnkiConnectBackend().attach_media(
        Path("."),
        source_path=source,
        name=None,
        dry_run=False,
    )

    assert result == {
        "name": "hello.mp3",
        "source_path": str(source.resolve()),
        "path": None,
        "size": len(b"audio-bytes"),
        "action": "attach",
        "dry_run": False,
    }


@pytest.mark.unit
def test_attach_media_dry_run_skips_store_media_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "hello.mp3"
    source.write_bytes(b"audio-bytes")
    _install_http_connection(monkeypatch, {})

    result = AnkiConnectBackend().attach_media(
        Path("."),
        source_path=source,
        name="renamed.mp3",
        dry_run=True,
    )

    assert result == {
        "name": "renamed.mp3",
        "source_path": str(source.resolve()),
        "path": None,
        "size": len(b"audio-bytes"),
        "action": "attach",
        "dry_run": True,
    }


@pytest.mark.unit
def test_delete_note_raises_backend_operation_unsupported() -> None:
    with pytest.raises(BackendOperationUnsupportedError) as excinfo:
        AnkiConnectBackend().delete_note(Path("."), note_id=101, dry_run=True)

    assert excinfo.value.details == {
        "backend": "ankiconnect",
        "operation": "note.delete",
    }


@pytest.mark.unit
def test_move_note_to_deck_uses_ankiconnect_change_deck(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_http_connection(
        monkeypatch,
        {
            "notesInfo": {
                "result": [
                    {
                        "noteId": 101,
                        "modelName": "Basic",
                        "tags": ["tag1"],
                        "fields": {"Front": {"value": "hello", "order": 0}},
                    },
                ],
                "error": None,
            },
            "findCards": {"result": [201], "error": None},
            "deckNamesAndIds": {"result": {"Default": 1, "Spanish": 2}, "error": None},
            "changeDeck": {"result": None, "error": None},
        },
    )

    result = AnkiConnectBackend().move_note_to_deck(
        Path("."),
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
