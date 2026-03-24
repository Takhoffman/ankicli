from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from tests.integration.helpers import fixture_read_error_codes, fixture_write_error_codes
from tests.proof import proves


def _copy_fixture_with_media(
    fixture_collection_path: Path,
    tmp_path: Path,
) -> tuple[Path, Path]:
    target_collection = tmp_path / fixture_collection_path.name
    shutil.copy2(fixture_collection_path, target_collection)
    media_dir = target_collection.with_suffix(".media")
    media_dir.mkdir()
    return target_collection, media_dir


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_repo_fixture_is_built_and_deterministic(fixture_collection_path) -> None:
    assert fixture_collection_path.exists()

    connection = sqlite3.connect(fixture_collection_path)
    try:
        row = connection.execute(
            "select value from metadata where key = 'fixture_name'",
        ).fetchone()
    finally:
        connection.close()

    assert row == ("minimal",)


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
@proves("collection.info", "fixture_integration")
def test_collection_info_integration_smoke(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "collection", "info"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["collection_path"] == str(fixture_collection_path.resolve())
        assert payload["data"]["exists"] is True
        assert payload["data"]["backend_available"] is True
        assert "note_count" in payload["data"]
        assert "card_count" in payload["data"]
        assert "deck_count" in payload["data"]
        assert "model_count" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
@proves("collection.stats", "fixture_integration")
def test_collection_stats_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "collection", "stats"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert "note_count" in payload["data"]
        assert "card_count" in payload["data"]
        assert "deck_count" in payload["data"]
        assert "model_count" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_collection_validate_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "collection", "validate"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    assert payload["ok"] is True
    assert "checks" in payload["data"]
    assert "warnings" in payload["data"]
    assert "errors" in payload["data"]


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_collection_lock_status_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "collection", "lock-status"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    assert payload["ok"] is True
    assert payload["data"]["status"] in {"not-detected", "possibly-open"}
    assert payload["data"]["confidence"] in {"best-effort", "low"}


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_doctor_backend_integration_contract(runner) -> None:
    result = runner.invoke(args=["--json", "doctor", "backend"])

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    assert payload["ok"] is True
    assert "supported_operation_count" in payload["data"]


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_doctor_capabilities_integration_contract(runner) -> None:
    result = runner.invoke(args=["--json", "doctor", "capabilities"])

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    assert payload["ok"] is True
    assert "supported_operation_count" in payload["data"]
    assert "supported_operations" in payload["data"]


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_doctor_collection_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "doctor", "collection"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert "stats" in payload["data"]
        assert "validation" in payload["data"]
        assert "lock_status" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_doctor_safety_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "doctor", "safety"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert "safe_for_writes" in payload["data"]
        assert "warnings" in payload["data"]
        assert "errors" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_deck_list_integration_smoke(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "deck", "list"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert isinstance(payload["data"]["items"], list)
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
@proves("deck.get", "fixture_integration")
def test_deck_get_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "deck",
            "get",
            "--name",
            "Default",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "Default"
        assert "id" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("DECK_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_deck_stats_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "deck",
            "stats",
            "--name",
            "Default",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "Default"
        assert "note_count" in payload["data"]
        assert "card_count" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("DECK_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_deck_create_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "deck",
            "create",
            "--name",
            "French",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "French"
        assert payload["data"]["action"] == "create"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_deck_rename_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "deck",
            "rename",
            "--name",
            "Default",
            "--to",
            "French",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "Default"
        assert payload["data"]["new_name"] == "French"
        assert payload["data"]["action"] == "rename"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("DECK_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_deck_delete_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "deck",
            "delete",
            "--name",
            "Default",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "Default"
        assert payload["data"]["action"] == "delete"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("DECK_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_deck_reparent_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "deck",
            "reparent",
            "--name",
            "Default",
            "--to-parent",
            "Parent",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "Default"
        assert payload["data"]["new_parent"] == "Parent"
        assert payload["data"]["action"] == "reparent"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("DECK_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_model_list_integration_smoke(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "model", "list"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert isinstance(payload["data"]["items"], list)
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
@proves("model.get", "fixture_integration")
def test_model_get_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "model",
            "get",
            "--name",
            "Basic",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "Basic"
        assert "id" in payload["data"]
        assert "fields" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("MODEL_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_model_fields_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "model",
            "fields",
            "--name",
            "Basic",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "Basic"
        assert "fields" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("MODEL_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_model_templates_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "model",
            "templates",
            "--name",
            "Basic",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "Basic"
        assert "templates" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("MODEL_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_model_validate_note_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "model",
            "validate-note",
            "--model",
            "Basic",
            "--field",
            "Front=hello",
            "--field",
            "Back=world",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["model"] == "Basic"
        assert "missing_fields" in payload["data"]
        assert "unknown_fields" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("MODEL_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_tag_list_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "tag", "list"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert isinstance(payload["data"]["items"], list)
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_tag_rename_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "tag",
            "rename",
            "--name",
            "tag1",
            "--to",
            "tag3",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["name"] == "tag1"
        assert payload["data"]["new_name"] == "tag3"
        assert payload["data"]["action"] == "rename"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("TAG_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_tag_delete_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "tag",
            "delete",
            "--tag",
            "tag1",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["tags"] == ["tag1"]
        assert payload["data"]["action"] == "delete"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("TAG_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_tag_reparent_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "tag",
            "reparent",
            "--tag",
            "tag1",
            "--to-parent",
            "tag2",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["tags"] == ["tag1"]
        assert payload["data"]["new_parent"] == "tag2"
        assert payload["data"]["action"] == "reparent"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("TAG_NOT_FOUND")


def test_search_notes_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "search",
            "notes",
            "--query",
            "deck:Default",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert isinstance(payload["data"]["items"], list)
        assert payload["data"]["query"] == "deck:Default"
        assert "total" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


def test_search_cards_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "search",
            "cards",
            "--query",
            "deck:Default",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert isinstance(payload["data"]["items"], list)
        assert payload["data"]["query"] == "deck:Default"
        assert "total" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
@proves("search.count", "fixture_integration")
def test_search_count_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "search",
            "count",
            "--kind",
            "notes",
            "--query",
            "deck:Default",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["kind"] == "notes"
        assert payload["data"]["query"] == "deck:Default"
        assert "total" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
@proves("search.preview", "fixture_integration")
def test_search_preview_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "search",
            "preview",
            "--kind",
            "notes",
            "--query",
            "deck:Default",
            "--limit",
            "5",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["kind"] == "notes"
        assert isinstance(payload["data"]["items"], list)
        assert payload["data"]["limit"] == 5
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("NOTE_NOT_FOUND")


def test_export_notes_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "export",
            "notes",
            "--query",
            "deck:Default",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert isinstance(payload["data"]["items"], list)
        assert payload["data"]["query"] == "deck:Default"
        assert "total" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("NOTE_NOT_FOUND")


def test_export_notes_ndjson_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--collection",
            str(fixture_collection_path),
            "export",
            "notes",
            "--query",
            "deck:Default",
            "--ndjson",
        ],
    )

    if result.exit_code == 0:
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        for line in lines:
            payload = json.loads(line)
            assert "id" in payload
            assert "fields" in payload
    else:
        if result.stdout.lstrip().startswith("{"):
            payload = json.loads(result.stdout)
            assert payload["error"]["code"] in fixture_read_error_codes("NOTE_NOT_FOUND")
        else:
            assert any(
                code in result.stdout for code in fixture_read_error_codes("NOTE_NOT_FOUND")
            )


def test_export_cards_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "export",
            "cards",
            "--query",
            "deck:Default",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert isinstance(payload["data"]["items"], list)
        assert payload["data"]["query"] == "deck:Default"
        assert "total" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("CARD_NOT_FOUND")


def test_export_cards_ndjson_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--collection",
            str(fixture_collection_path),
            "export",
            "cards",
            "--query",
            "deck:Default",
            "--ndjson",
        ],
    )

    if result.exit_code == 0:
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        for line in lines:
            payload = json.loads(line)
            assert "id" in payload
            assert "template" in payload
    else:
        if result.stdout.lstrip().startswith("{"):
            payload = json.loads(result.stdout)
            assert payload["error"]["code"] in fixture_read_error_codes("CARD_NOT_FOUND")
        else:
            assert any(
                code in result.stdout for code in fixture_read_error_codes("CARD_NOT_FOUND")
            )


@proves("note.get", "fixture_integration")
def test_note_get_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "note",
            "get",
            "--id",
            "101",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 101
        assert "fields" in payload["data"]
        assert "tags" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("NOTE_NOT_FOUND")


def test_note_fields_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "note",
            "fields",
            "--id",
            "101",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 101
        assert "fields" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("NOTE_NOT_FOUND")


def test_card_get_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "card",
            "get",
            "--id",
            "201",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 201
        assert "note_id" in payload["data"]
        assert "deck_id" in payload["data"]
        assert "template" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes("CARD_NOT_FOUND")


@proves("card.suspend", "fixture_integration")
def test_card_suspend_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "card",
            "suspend",
            "--id",
            "201",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 201
        assert payload["data"]["suspended"] is True
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("CARD_NOT_FOUND")


def test_card_unsuspend_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "card",
            "unsuspend",
            "--id",
            "201",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 201
        assert payload["data"]["suspended"] is False
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("CARD_NOT_FOUND")


@proves("note.add", "fixture_integration")
def test_note_add_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "note",
            "add",
            "--deck",
            "Default",
            "--model",
            "Basic",
            "--field",
            "Front=hello",
            "--field",
            "Back=world",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["deck"] == "Default"
        assert payload["data"]["model"] == "Basic"
        assert payload["data"]["fields"]["Front"] == "hello"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes(
            "DECK_NOT_FOUND",
            "MODEL_NOT_FOUND",
        )


def test_import_notes_integration_contract(runner, fixture_collection_path, tmp_path) -> None:
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

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "import",
            "notes",
            "--input",
            str(input_path),
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["count"] == 1
        assert payload["data"]["dry_run"] is True
        assert payload["data"]["items"][0]["deck"] == "Default"
    else:
        assert payload["error"]["code"] in fixture_write_error_codes(
            "DECK_NOT_FOUND",
            "MODEL_NOT_FOUND",
        )


def test_import_patch_integration_contract(runner, fixture_collection_path, tmp_path) -> None:
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

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "import",
            "patch",
            "--input",
            str(input_path),
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["count"] == 1
        assert payload["data"]["dry_run"] is True
        assert payload["data"]["items"][0]["id"] == 101
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("NOTE_NOT_FOUND")


def test_import_notes_stdin_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "import",
            "notes",
            "--stdin-json",
            "--dry-run",
        ],
        input=json.dumps(
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

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["count"] == 1
        assert payload["data"]["source"] == "stdin"
    else:
        assert payload["error"]["code"] in fixture_write_error_codes(
            "DECK_NOT_FOUND",
            "MODEL_NOT_FOUND",
        )


def test_import_patch_stdin_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "import",
            "patch",
            "--stdin-json",
            "--dry-run",
        ],
        input=json.dumps({"items": [{"id": 101, "fields": {"Back": "updated"}}]}),
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["count"] == 1
        assert payload["data"]["source"] == "stdin"
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("NOTE_NOT_FOUND")


def test_note_update_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "note",
            "update",
            "--id",
            "101",
            "--field",
            "Back=updated",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 101
        assert payload["data"]["fields"]["Back"] == "updated"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("NOTE_NOT_FOUND")


def test_note_add_tags_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "note",
            "add-tags",
            "--id",
            "101",
            "--tag",
            "tag3",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 101
        assert payload["data"]["tags"] == ["tag3"]
        assert payload["data"]["action"] == "add"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("NOTE_NOT_FOUND")


def test_note_remove_tags_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "note",
            "remove-tags",
            "--id",
            "101",
            "--tag",
            "tag1",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 101
        assert payload["data"]["tags"] == ["tag1"]
        assert payload["data"]["action"] == "remove"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("NOTE_NOT_FOUND")


def test_note_move_deck_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "note",
            "move-deck",
            "--id",
            "101",
            "--deck",
            "Default",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 101
        assert payload["data"]["deck"] == "Default"
        assert payload["data"]["action"] == "move_deck"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes(
            "NOTE_NOT_FOUND",
            "DECK_NOT_FOUND",
        )


@proves("note.delete", "fixture_integration")
def test_note_delete_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "note",
            "delete",
            "--id",
            "101",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 101
        assert payload["data"]["deleted"] is False
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("NOTE_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_media_list_integration_contract(runner, fixture_collection_path, tmp_path: Path) -> None:
    collection_path, media_dir = _copy_fixture_with_media(fixture_collection_path, tmp_path)
    (media_dir / "used.png").write_text("u")
    (media_dir / "orphan.txt").write_text("o")

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "media", "list"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    assert payload["ok"] is True
    assert [item["name"] for item in payload["data"]["items"]] == ["orphan.txt", "used.png"]


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_media_resolve_path_integration_contract(
    runner,
    fixture_collection_path,
    tmp_path: Path,
) -> None:
    collection_path, media_dir = _copy_fixture_with_media(fixture_collection_path, tmp_path)
    (media_dir / "used.png").write_text("u")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "media",
            "resolve-path",
            "--name",
            "used.png",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    assert payload["ok"] is True
    assert payload["data"]["name"] == "used.png"


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_media_check_integration_contract(runner, fixture_collection_path, tmp_path: Path) -> None:
    collection_path, media_dir = _copy_fixture_with_media(fixture_collection_path, tmp_path)
    (media_dir / "used.png").write_text("u")

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "media", "check"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert "file_count" in payload["data"]
        assert "orphaned_count" in payload["data"]
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_media_attach_integration_contract(runner, fixture_collection_path, tmp_path: Path) -> None:
    collection_path, media_dir = _copy_fixture_with_media(fixture_collection_path, tmp_path)
    del media_dir
    source_path = tmp_path / "upload.txt"
    source_path.write_text("hello")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "media",
            "attach",
            "--source",
            str(source_path),
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    assert payload["ok"] is True
    assert payload["data"]["name"] == "upload.txt"
    assert payload["data"]["action"] == "attach"
    assert payload["data"]["dry_run"] is True


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
@proves("tag.apply", "fixture_integration")
def test_tag_apply_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "tag",
            "apply",
            "--id",
            "101",
            "--tag",
            "review",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 101
        assert payload["data"]["action"] == "add"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("NOTE_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_tag_remove_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(fixture_collection_path),
            "tag",
            "remove",
            "--id",
            "101",
            "--tag",
            "review",
            "--dry-run",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["id"] == 101
        assert payload["data"]["action"] == "remove"
        assert payload["data"]["dry_run"] is True
    else:
        assert payload["error"]["code"] in fixture_write_error_codes("NOTE_NOT_FOUND")


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_media_orphaned_integration_contract(
    runner,
    fixture_collection_path,
    tmp_path: Path,
) -> None:
    collection_path, media_dir = _copy_fixture_with_media(fixture_collection_path, tmp_path)
    (media_dir / "used.png").write_text("u")

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "media", "orphaned"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert isinstance(payload["data"]["items"], list)
    else:
        assert payload["error"]["code"] in fixture_read_error_codes()
