from __future__ import annotations

import json
import os

import pytest

from tests.proof import proves


def _require_live_ankiconnect(runner) -> dict:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "info"])
    if result.exit_code != 0:
        pytest.skip(
            "AnkiConnect backend info failed; ensure Anki Desktop and AnkiConnect are running",
        )
    payload = json.loads(result.stdout)
    capabilities = payload["data"]["capabilities"]
    if not capabilities["available"]:
        pytest.skip("AnkiConnect is unavailable; start Anki Desktop with the AnkiConnect add-on")
    return payload


def _require_env(name: str, message: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(message)
    return value


@pytest.mark.backend_ankiconnect_real
def test_backend_info_live_ankiconnect(runner) -> None:
    payload = _require_live_ankiconnect(runner)

    assert payload["ok"] is True
    assert payload["data"]["name"] == "ankiconnect"
    assert payload["data"]["capabilities"]["supports_live_desktop"] is True


@pytest.mark.backend_ankiconnect_real
@proves("collection.info", "real_ankiconnect")
def test_collection_info_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "collection", "info"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["collection_name"] == "AnkiConnect"


@pytest.mark.backend_ankiconnect_real
def test_backend_test_connection_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "backend",
            "test-connection",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["name"] == "ankiconnect"
    assert payload["data"]["ok"] is True


@pytest.mark.backend_ankiconnect_real
def test_collection_stats_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "collection", "stats"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert "note_count" in payload["data"]
    assert "card_count" in payload["data"]


@pytest.mark.backend_ankiconnect_real
def test_deck_get_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    deck_name = _require_env(
        "ANKICLI_REAL_DECK",
        "set ANKICLI_REAL_DECK to run live AnkiConnect deck get checks",
    )

    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "deck", "get", "--name", deck_name],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["name"] == deck_name


@pytest.mark.backend_ankiconnect_real
def test_deck_stats_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    deck_name = _require_env(
        "ANKICLI_REAL_DECK",
        "set ANKICLI_REAL_DECK to run live AnkiConnect deck stats checks",
    )

    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "deck", "stats", "--name", deck_name],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["name"] == deck_name
    assert "note_count" in payload["data"]
    assert "card_count" in payload["data"]


@pytest.mark.backend_ankiconnect_real
def test_model_fields_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    model_name = _require_env(
        "ANKICLI_REAL_MODEL",
        "set ANKICLI_REAL_MODEL to run live AnkiConnect model fields checks",
    )

    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "model", "fields", "--name", model_name],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["name"] == model_name
    assert "fields" in payload["data"]


@pytest.mark.backend_ankiconnect_real
def test_model_templates_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    model_name = _require_env(
        "ANKICLI_REAL_MODEL",
        "set ANKICLI_REAL_MODEL to run live AnkiConnect model templates checks",
    )

    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "model", "templates", "--name", model_name],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["name"] == model_name
    assert "templates" in payload["data"]


@pytest.mark.backend_ankiconnect_real
def test_model_validate_note_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    model_name = _require_env(
        "ANKICLI_REAL_MODEL",
        "set ANKICLI_REAL_MODEL to run live AnkiConnect model validate checks",
    )

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "model",
            "validate-note",
            "--model",
            model_name,
            "--field",
            "Front=hello",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["model"] == model_name


@pytest.mark.backend_ankiconnect_real
def test_search_notes_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "search", "notes", "--query", ""],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert "items" in payload["data"]


@pytest.mark.backend_ankiconnect_real
def test_search_count_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "search",
            "count",
            "--kind",
            "notes",
            "--query",
            "",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["kind"] == "notes"
    assert "total" in payload["data"]


@pytest.mark.backend_ankiconnect_real
def test_search_preview_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "search",
            "preview",
            "--kind",
            "notes",
            "--query",
            "",
            "--limit",
            "5",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["kind"] == "notes"
    assert "items" in payload["data"]


@pytest.mark.backend_ankiconnect_real
def test_note_get_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    note_id = _require_env(
        "ANKICLI_REAL_NOTE_ID",
        "set ANKICLI_REAL_NOTE_ID to run live AnkiConnect note get checks",
    )

    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "note", "get", "--id", note_id],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["id"] == int(note_id)


@pytest.mark.backend_ankiconnect_real
def test_note_fields_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    note_id = _require_env(
        "ANKICLI_REAL_NOTE_ID",
        "set ANKICLI_REAL_NOTE_ID to run live AnkiConnect note fields checks",
    )

    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "note", "fields", "--id", note_id],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["id"] == int(note_id)
    assert "fields" in payload["data"]


@pytest.mark.backend_ankiconnect_real
def test_card_get_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    card_id = _require_env(
        "ANKICLI_REAL_CARD_ID",
        "set ANKICLI_REAL_CARD_ID to run live AnkiConnect card get checks",
    )

    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "card", "get", "--id", card_id],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["id"] == int(card_id)


@pytest.mark.backend_ankiconnect_real
def test_note_add_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    deck_name = _require_env(
        "ANKICLI_REAL_DECK",
        "set ANKICLI_REAL_DECK to run live AnkiConnect note add checks",
    )
    model_name = _require_env(
        "ANKICLI_REAL_MODEL",
        "set ANKICLI_REAL_MODEL to run live AnkiConnect note add checks",
    )

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "note",
            "add",
            "--deck",
            deck_name,
            "--model",
            model_name,
            "--field",
            "Front=AnkiConnect live dry run",
            "--field",
            "Back=ok",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["dry_run"] is True


@pytest.mark.backend_ankiconnect_real
def test_note_move_deck_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    note_id = _require_env(
        "ANKICLI_REAL_NOTE_ID",
        "set ANKICLI_REAL_NOTE_ID to run live AnkiConnect note move-deck checks",
    )
    deck_name = _require_env(
        "ANKICLI_REAL_DECK",
        "set ANKICLI_REAL_DECK to run live AnkiConnect note move-deck checks",
    )

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "note",
            "move-deck",
            "--id",
            note_id,
            "--deck",
            deck_name,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["id"] == int(note_id)
    assert payload["data"]["deck"] == deck_name


@pytest.mark.backend_ankiconnect_real
def test_import_notes_stdin_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    deck_name = _require_env(
        "ANKICLI_REAL_DECK",
        "set ANKICLI_REAL_DECK to run live AnkiConnect import notes checks",
    )
    model_name = _require_env(
        "ANKICLI_REAL_MODEL",
        "set ANKICLI_REAL_MODEL to run live AnkiConnect import notes checks",
    )

    payload = json.dumps(
        {
            "items": [
                {
                    "deck": deck_name,
                    "model": model_name,
                    "fields": {"Front": "AnkiConnect import dry run", "Back": "ok"},
                    "tags": [],
                },
            ],
        },
    )
    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "import", "notes", "--stdin-json", "--dry-run"],
        input=payload,
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["data"]["dry_run"] is True
    assert response["data"]["count"] == 1
    assert response["data"]["source"] == "stdin"


@pytest.mark.backend_ankiconnect_real
def test_import_patch_stdin_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    note_id = _require_env(
        "ANKICLI_REAL_NOTE_ID",
        "set ANKICLI_REAL_NOTE_ID to run live AnkiConnect import patch checks",
    )

    payload = json.dumps({"items": [{"id": int(note_id), "fields": {"Front": "patched"}}]})
    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "import", "patch", "--stdin-json", "--dry-run"],
        input=payload,
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["data"]["dry_run"] is True
    assert response["data"]["count"] == 1
    assert response["data"]["source"] == "stdin"


@pytest.mark.backend_ankiconnect_real
def test_card_suspend_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    card_id = _require_env(
        "ANKICLI_REAL_CARD_ID",
        "set ANKICLI_REAL_CARD_ID to run live AnkiConnect card suspend checks",
    )

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "card",
            "suspend",
            "--id",
            card_id,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["data"]["id"] == int(card_id)
    assert response["data"]["suspended"] is True
    assert response["data"]["dry_run"] is True


@pytest.mark.backend_ankiconnect_real
def test_card_unsuspend_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    card_id = _require_env(
        "ANKICLI_REAL_CARD_ID",
        "set ANKICLI_REAL_CARD_ID to run live AnkiConnect card unsuspend checks",
    )

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "card",
            "unsuspend",
            "--id",
            card_id,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["data"]["id"] == int(card_id)
    assert response["data"]["suspended"] is False
    assert response["data"]["dry_run"] is True


@pytest.mark.backend_ankiconnect_real
def test_media_check_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "media", "check"])

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert "media_dir" in response["data"]
    assert "file_count" in response["data"]


@pytest.mark.backend_ankiconnect_real
def test_media_attach_dry_run_live_ankiconnect(runner, tmp_path) -> None:
    _require_live_ankiconnect(runner)
    source_path = tmp_path / "upload.txt"
    source_path.write_text("hello")

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "media",
            "attach",
            "--source",
            str(source_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert response["data"]["name"] == "upload.txt"
    assert response["data"]["source_path"] == str(source_path)
    assert response["data"]["size"] == len("hello")
    assert response["data"]["action"] == "attach"
    assert response["data"]["dry_run"] is True


@pytest.mark.backend_ankiconnect_real
def test_media_resolve_path_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    list_result = runner.invoke(args=["--json", "--backend", "ankiconnect", "media", "list"])
    assert list_result.exit_code == 0
    list_payload = json.loads(list_result.stdout)
    if not list_payload["data"]["items"]:
        pytest.skip("No media files available to run media resolve-path check")
    media_name = list_payload["data"]["items"][0]["name"]

    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "media", "resolve-path", "--name", media_name],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert response["data"]["name"] == media_name
    assert "path" in response["data"]


@pytest.mark.backend_ankiconnect_real
def test_deck_delete_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    deck_name = _require_env(
        "ANKICLI_REAL_DECK",
        "set ANKICLI_REAL_DECK to run live AnkiConnect deck delete checks",
    )

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "deck",
            "delete",
            "--name",
            deck_name,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert response["data"]["name"] == deck_name
    assert response["data"]["action"] == "delete"
    assert response["data"]["dry_run"] is True


@pytest.mark.backend_ankiconnect_real
def test_deck_rename_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)
    deck_name = _require_env(
        "ANKICLI_REAL_DECK",
        "set ANKICLI_REAL_DECK to run live AnkiConnect deck rename checks",
    )

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "deck",
            "rename",
            "--name",
            deck_name,
            "--to",
            f"{deck_name} Temp",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert response["data"]["name"] == deck_name
    assert response["data"]["action"] == "rename"
    assert response["data"]["dry_run"] is True


@pytest.mark.backend_ankiconnect_real
def test_note_delete_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    search_result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "search", "notes", "--query", "", "--limit", "1"],
    )
    assert search_result.exit_code == 0
    search_payload = json.loads(search_result.stdout)
    if not search_payload["data"]["items"]:
        pytest.skip("No notes available to run note delete check")
    note_id = search_payload["data"]["items"][0]["id"]

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "note",
            "delete",
            "--id",
            str(note_id),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert response["data"]["id"] == note_id
    assert response["data"]["dry_run"] is True


@pytest.mark.backend_ankiconnect_real
def test_tag_rename_dry_run_live_ankiconnect(runner) -> None:
    _require_live_ankiconnect(runner)

    list_result = runner.invoke(args=["--json", "--backend", "ankiconnect", "tag", "list"])
    assert list_result.exit_code == 0
    list_payload = json.loads(list_result.stdout)
    if not list_payload["data"]["items"]:
        pytest.skip("No tags available to run tag rename check")
    tag_name = list_payload["data"]["items"][0]

    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "tag",
            "rename",
            "--name",
            tag_name,
            "--to",
            f"{tag_name}-tmp",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    response = json.loads(result.stdout)
    assert response["ok"] is True
    assert response["data"]["name"] == tag_name
    assert response["data"]["action"] == "rename"
