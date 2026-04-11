from __future__ import annotations

import http.client
import json
from pathlib import Path

import pytest

from ankicli.app.errors import (
    BackendOperationUnsupportedError,
    NoteNotFoundError,
    ValidationError,
)
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
    assert capabilities.supported_operations["note.delete"] is True
    assert capabilities.supported_operations["note.add"] is True
    assert capabilities.supported_operations["deck.create"] is True
    assert capabilities.supported_operations["deck.rename"] is True
    assert capabilities.supported_operations["deck.delete"] is True
    assert capabilities.supported_operations["deck.reparent"] is True
    assert capabilities.supported_operations["media.attach"] is True
    assert capabilities.supported_operations["media.list"] is True
    assert capabilities.supported_operations["media.check"] is True
    assert capabilities.supported_operations["media.resolve_path"] is True
    assert capabilities.supported_operations["tag.rename"] is True
    assert capabilities.supported_operations["tag.delete"] is True
    assert capabilities.supported_operations["tag.reparent"] is True
    assert capabilities.supported_operations["auth.status"] is False
    assert capabilities.supported_operations["sync.run"] is False


@pytest.mark.unit
def test_backend_defaults_to_ankiconnect_api_version_6() -> None:
    backend = AnkiConnectBackend()

    assert backend.version == 6


@pytest.mark.unit
def test_backend_uses_env_override_for_ankiconnect_api_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANKICONNECT_API_VERSION", "5")

    backend = AnkiConnectBackend()

    assert backend.version == 5


@pytest.mark.unit
def test_backend_ignores_invalid_env_override_for_ankiconnect_api_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANKICONNECT_API_VERSION", "not-a-number")

    backend = AnkiConnectBackend()

    assert backend.version == 6


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
    assert capabilities.supported_operations["tag.rename"] is True
    assert capabilities.supported_operations["sync.run"] is False


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
def test_media_list_reads_names_from_media_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    media_dir = tmp_path / "collection.media"
    media_dir.mkdir()
    (media_dir / "a.txt").write_text("aa")
    (media_dir / "b.txt").write_text("b")

    backend = AnkiConnectBackend()

    def fake_invoke(action: str, params: dict | None = None):
        del params
        if action == "getMediaDirPath":
            return str(media_dir)
        if action == "getMediaFilesNames":
            return ["a.txt", "b.txt"]
        raise AssertionError(action)

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.list_media(Path("."))

    assert result == [
        {"name": "a.txt", "path": str((media_dir / "a.txt").resolve()), "size": 2},
        {"name": "b.txt", "path": str((media_dir / "b.txt").resolve()), "size": 1},
    ]


@pytest.mark.unit
def test_media_check_computes_reference_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    media_dir = tmp_path / "collection.media"
    media_dir.mkdir()
    (media_dir / "used.png").write_text("u")
    (media_dir / "orphan.txt").write_text("o")

    backend = AnkiConnectBackend()

    def fake_invoke(action: str, params: dict | None = None):
        if action == "getMediaDirPath":
            return str(media_dir)
        if action == "getMediaFilesNames":
            return ["used.png", "orphan.txt"]
        if action == "findNotes":
            return [101]
        if action == "notesInfo":
            return [
                {
                    "noteId": 101,
                    "fields": {
                        "Front": {"value": '<img src="used.png">', "order": 0},
                        "Back": {"value": "[sound:missing.mp3]", "order": 1},
                    },
                },
            ]
        raise AssertionError((action, params))

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.check_media(Path("."))

    assert result["media_dir"] == str(media_dir.resolve())
    assert result["file_count"] == 2
    assert result["referenced_count"] == 2
    assert result["orphaned_count"] == 1
    assert result["missing_count"] == 1


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
    backend = AnkiConnectBackend()
    calls: list[tuple[str, dict | None]] = []

    def fake_invoke(action: str, params: dict | None = None):
        calls.append((action, params))
        if action == "deckNamesAndIds":
            return {"Japanese": 99}
        if action == "findCards":
            return []
        if action == "deleteDecks":
            return None
        raise AssertionError((action, params))

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.delete_deck(Path("."), name="Japanese", dry_run=False)

    assert result["id"] == 99
    assert result["card_count"] == 0
    assert ("deleteDecks", {"decks": ["Japanese"], "cardsToo": True}) in calls


@pytest.mark.unit
def test_delete_deck_dry_run_validates_name_without_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = AnkiConnectBackend()

    def fake_invoke(action: str, params: dict | None = None):
        del params
        if action == "deckNamesAndIds":
            return {"Japanese": 99}
        if action == "findCards":
            return [201]
        if action == "getDecks":
            return {"Japanese": [201]}
        raise AssertionError(action)

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.delete_deck(Path("."), name="Japanese", dry_run=True)

    assert result["id"] == 99
    assert result["card_count"] == 1
    assert result["dry_run"] is True


@pytest.mark.unit
def test_delete_deck_rejects_non_empty_live_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = AnkiConnectBackend()

    def fake_invoke(action: str, params: dict | None = None):
        del params
        if action == "deckNamesAndIds":
            return {"Japanese": 99}
        if action == "findCards":
            return [201]
        if action == "getDecks":
            return {"Japanese": [201]}
        raise AssertionError(action)

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    with pytest.raises(ValidationError):
        backend.delete_deck(Path("."), name="Japanese", dry_run=False)


@pytest.mark.unit
def test_rename_deck_moves_subtree_and_reports_descendants(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = AnkiConnectBackend()
    calls: list[tuple[str, dict | None]] = []

    def fake_invoke(action: str, params: dict | None = None):
        calls.append((action, params))
        if action == "deckNamesAndIds":
            return {"Japanese": 99, "Japanese::Anime": 100}
        if action == "findCards":
            return [201, 202]
        if action == "getDecks":
            return {"Japanese": [201], "Japanese::Anime": [202]}
        if action in {"createDeck", "changeDeck", "deleteDecks"}:
            return None
        raise AssertionError((action, params))

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.rename_deck(Path("."), name="Japanese", new_name="Immersion", dry_run=False)

    assert result["descendant_count"] == 1
    assert result["card_count"] == 2
    assert ("createDeck", {"deck": "Immersion"}) in calls
    assert ("createDeck", {"deck": "Immersion::Anime"}) in calls
    assert ("changeDeck", {"cards": [201], "deck": "Immersion"}) in calls
    assert ("changeDeck", {"cards": [202], "deck": "Immersion::Anime"}) in calls


@pytest.mark.unit
def test_reparent_deck_computes_target_name(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = AnkiConnectBackend()

    def fake_invoke(action: str, params: dict | None = None):
        del params
        if action == "deckNamesAndIds":
            return {"Japanese": 99, "Study": 1}
        if action == "findCards":
            return []
        raise AssertionError(action)

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.reparent_deck(Path("."), name="Japanese", new_parent="Study", dry_run=True)

    assert result["new_name"] == "Study::Japanese"
    assert result["new_parent"] == "Study"


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
def test_delete_note_uses_delete_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = AnkiConnectBackend()
    calls: list[tuple[str, dict | None]] = []

    def fake_invoke(action: str, params: dict | None = None):
        calls.append((action, params))
        if action == "notesInfo":
            return [{"noteId": 101, "modelName": "Basic", "fields": {}, "tags": []}]
        if action == "deleteNotes":
            return None
        raise AssertionError((action, params))

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.delete_note(Path("."), note_id=101, dry_run=False)

    assert result == {"id": 101, "deleted": True, "dry_run": False}
    assert ("deleteNotes", {"notes": [101]}) in calls


@pytest.mark.unit
def test_tag_rename_uses_replace_tags_in_all_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = AnkiConnectBackend()
    calls: list[tuple[str, dict | None]] = []

    def fake_invoke(action: str, params: dict | None = None):
        calls.append((action, params))
        if action == "getTags":
            return ["japanese", "japanese::anime"]
        if action == "findNotes":
            return [101]
        if action == "notesInfo":
            return [{"noteId": 101, "tags": ["japanese", "japanese::anime"], "fields": {}}]
        if action == "replaceTagsInAllNotes":
            return None
        raise AssertionError((action, params))

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.rename_tag(Path("."), name="japanese", new_name="immersion", dry_run=False)

    assert result["affected_tag_count"] == 2
    assert result["affected_note_count"] == 1
    assert (
        "replaceTagsInAllNotes",
        {"tag_to_replace": "japanese", "replace_with_tag": "immersion"},
    ) in calls
    assert (
        "replaceTagsInAllNotes",
        {"tag_to_replace": "japanese::anime", "replace_with_tag": "immersion::anime"},
    ) in calls


@pytest.mark.unit
def test_delete_tags_uses_remove_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = AnkiConnectBackend()
    calls: list[tuple[str, dict | None]] = []

    def fake_invoke(action: str, params: dict | None = None):
        calls.append((action, params))
        if action == "getTags":
            return ["review", "audio"]
        if action == "findNotes":
            return [101, 102]
        if action == "notesInfo":
            return [
                {"noteId": 101, "tags": ["review"], "fields": {}},
                {"noteId": 102, "tags": ["audio"], "fields": {}},
            ]
        if action == "removeTags":
            return None
        raise AssertionError((action, params))

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.delete_tags(Path("."), tags=["review"], dry_run=False)

    assert result["affected_note_count"] == 1
    assert ("removeTags", {"notes": [101], "tags": "review"}) in calls


@pytest.mark.unit
def test_reparent_tags_computes_new_hierarchy(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = AnkiConnectBackend()

    def fake_invoke(action: str, params: dict | None = None):
        if action == "getTags":
            return ["jlpt::n5", "study"]
        if action == "findNotes":
            return [101]
        if action == "notesInfo":
            return [{"noteId": 101, "tags": ["jlpt::n5"], "fields": {}}]
        if action == "replaceTagsInAllNotes":
            return None
        raise AssertionError((action, params))

    monkeypatch.setattr(backend, "_invoke", fake_invoke)

    result = backend.reparent_tags(Path("."), tags=["jlpt::n5"], new_parent="study", dry_run=True)

    assert result["tags"] == ["jlpt::n5"]
    assert result["new_parent"] == "study"
    assert result["affected_note_count"] == 1


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
