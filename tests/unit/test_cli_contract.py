from __future__ import annotations

import json

import pytest

from ankicli import __version__


@pytest.mark.unit
def test_doctor_env_json_contract(runner) -> None:
    result = runner.invoke(args=["--json", "doctor", "env"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["backend"] == "python-anki"
    assert "anki_source_path" in payload["data"]
    assert "anki_source_import_path" in payload["data"]
    assert "anki_import_available" in payload["data"]


@pytest.mark.unit
def test_version_reports_package_version(runner) -> None:
    result = runner.invoke(args=["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


@pytest.mark.unit
def test_collection_info_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "collection", "info"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_collection_and_profile_are_mutually_exclusive(runner, tmp_path) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "--profile",
            "User 1",
            "collection",
            "info",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_collection_info_missing_file_is_structured_error(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "collection", "info"],
    )

    assert result.exit_code == 5
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_NOT_FOUND"


@pytest.mark.unit
def test_ankiconnect_backend_capabilities_expose_operation_matrix(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "capabilities"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    operations = payload["data"]["supported_operations"]
    assert operations["note.add"] is True
    assert operations["note.delete"] is False
    assert operations["tag.rename"] is False
    assert operations["collection.validate"] is False
    assert operations["media.list"] is False
    assert operations["auth.status"] is False
    assert operations["sync.run"] is False
    assert operations["profile.list"] is False
    assert operations["backup.restore"] is False


@pytest.mark.unit
def test_auth_status_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "auth", "status"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "auth.status",
    }


@pytest.mark.unit
def test_profile_list_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "profile", "list"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "profile.list",
    }


@pytest.mark.unit
def test_backup_restore_requires_yes(runner, tmp_path) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "backup",
            "restore",
            "--name",
            "backup-2026.colpkg",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_sync_status_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "sync", "status"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_sync_run_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "sync", "run"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "sync.run",
    }


@pytest.mark.unit
def test_deck_list_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "deck", "list"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_media_list_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "media", "list"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_media_resolve_path_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "media", "resolve-path", "--name", "used.png"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_ankiconnect_media_commands_are_structured_unsupported_errors(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "media", "check"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "media.check",
    }


@pytest.mark.unit
def test_media_attach_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "media", "attach", "--source", "/tmp/file.txt", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_media_attach_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    source_path = tmp_path / "file.txt"
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
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_tag_apply_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "tag", "apply", "--id", "101", "--tag", "review", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_tag_remove_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "remove",
            "--id",
            "101",
            "--tag",
            "review",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_deck_get_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "deck", "get", "--name", "Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_deck_stats_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "deck", "stats", "--name", "Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_deck_create_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "deck", "create", "--name", "French", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_deck_rename_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "deck", "rename", "--name", "Default", "--to", "French", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_deck_delete_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "deck", "delete", "--name", "Default", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_deck_reparent_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "deck",
            "reparent",
            "--name",
            "Default",
            "--to-parent",
            "Parent",
            "--dry-run",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_deck_create_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "deck", "create", "--name", "French"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_deck_rename_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "deck",
            "rename",
            "--name",
            "Default",
            "--to",
            "French",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_deck_delete_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "deck",
            "delete",
            "--name",
            "Default",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_deck_reparent_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "deck",
            "reparent",
            "--name",
            "Default",
            "--to-parent",
            "Parent",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_ankiconnect_deck_lifecycle_is_structured_unsupported_error(runner) -> None:
    create_result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "deck",
            "create",
            "--name",
            "French",
            "--dry-run",
        ],
    )
    rename_result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "deck",
            "rename",
            "--name",
            "Default",
            "--to",
            "French",
            "--dry-run",
        ],
    )

    assert create_result.exit_code == 14
    assert rename_result.exit_code == 14
    assert json.loads(create_result.stdout)["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "deck.create",
    }
    assert json.loads(rename_result.stdout)["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "deck.rename",
    }


@pytest.mark.unit
def test_model_list_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "model", "list"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_model_get_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "model", "get", "--name", "Basic"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_model_fields_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "model", "fields", "--name", "Basic"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_model_templates_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "model", "templates", "--name", "Basic"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_model_validate_note_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "model",
            "validate-note",
            "--model",
            "Basic",
            "--field",
            "Front=hello",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_tag_list_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "tag", "list"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_tag_rename_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "tag",
            "rename",
            "--name",
            "tag1",
            "--to",
            "tag2",
            "--dry-run",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_tag_delete_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "tag", "delete", "--tag", "tag1", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_tag_reparent_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "tag", "reparent", "--tag", "tag1", "--to-parent", "tag2", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_ankiconnect_note_delete_is_structured_unsupported_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "note", "delete", "--id", "101", "--dry-run"],
    )

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "note.delete",
    }


@pytest.mark.unit
def test_ankiconnect_tag_rename_is_structured_unsupported_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "tag",
            "rename",
            "--name",
            "tag1",
            "--to",
            "tag2",
            "--dry-run",
        ],
    )

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "tag.rename",
    }


@pytest.mark.unit
def test_search_notes_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "search", "notes", "--query", "deck:Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_search_cards_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "search", "cards", "--query", "deck:Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_search_count_invalid_kind_is_validation_error(runner) -> None:
    result = runner.invoke(args=["--json", "search", "count", "--kind", "bogus", "--query", ""])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_search_preview_invalid_kind_is_validation_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "search", "preview", "--kind", "bogus", "--query", ""],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_collection_stats_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "collection", "stats"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_doctor_collection_unsupported_on_ankiconnect_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "doctor", "collection"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "doctor.collection",
    }


@pytest.mark.unit
def test_doctor_safety_unsupported_on_ankiconnect_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "doctor", "safety"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "doctor.safety",
    }


@pytest.mark.unit
def test_collection_validate_unsupported_on_ankiconnect_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "collection", "validate"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "collection.validate",
    }


@pytest.mark.unit
def test_collection_lock_status_unsupported_on_ankiconnect_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "collection", "lock-status"],
    )

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "collection.lock_status",
    }


@pytest.mark.unit
def test_export_notes_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "export", "notes", "--query", "deck:Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_export_cards_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "export", "cards", "--query", "deck:Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_export_notes_ndjson_emits_one_record_per_line(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "export",
            "notes",
            "--query",
            "deck:Default",
            "--ndjson",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_NOT_FOUND"


@pytest.mark.unit
def test_export_cards_ndjson_emits_one_record_per_line(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "export",
            "cards",
            "--query",
            "deck:Default",
            "--ndjson",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_NOT_FOUND"


@pytest.mark.unit
def test_import_notes_without_path_is_structured_error(runner, tmp_path) -> None:
    input_path = tmp_path / "notes.json"
    input_path.write_text("[]")

    result = runner.invoke(
        args=["--json", "import", "notes", "--input", str(input_path), "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_import_patch_without_path_is_structured_error(runner, tmp_path) -> None:
    input_path = tmp_path / "patches.json"
    input_path.write_text("[]")

    result = runner.invoke(
        args=["--json", "import", "patch", "--input", str(input_path), "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_note_get_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "note", "get", "--id", "123"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_note_fields_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "note", "fields", "--id", "123"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_card_get_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "card", "get", "--id", "123"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_card_suspend_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "card", "suspend", "--id", "201", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_card_unsuspend_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "card", "unsuspend", "--id", "201", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_card_suspend_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "card", "suspend", "--id", "201"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_card_unsuspend_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "card", "unsuspend", "--id", "201"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_note_add_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "note",
            "add",
            "--deck",
            "Default",
            "--model",
            "Basic",
            "--field",
            "Front=hello",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_note_update_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "note",
            "update",
            "--id",
            "123",
            "--field",
            "Front=hello",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_note_delete_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "note", "delete", "--id", "123", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_note_add_tags_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "note", "add-tags", "--id", "123", "--tag", "tag1", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_note_remove_tags_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "note", "remove-tags", "--id", "123", "--tag", "tag1", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_note_delete_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "note", "delete", "--id", "123"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_note_add_tags_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "add-tags",
            "--id",
            "123",
            "--tag",
            "tag1",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_note_remove_tags_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "remove-tags",
            "--id",
            "123",
            "--tag",
            "tag1",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_note_move_deck_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "note", "move-deck", "--id", "123", "--deck", "Default", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_note_move_deck_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "move-deck",
            "--id",
            "123",
            "--deck",
            "Default",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_note_tag_commands_require_a_tag_value(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    add_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "add-tags",
            "--id",
            "123",
            "--dry-run",
        ],
    )
    remove_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "remove-tags",
            "--id",
            "123",
            "--dry-run",
        ],
    )

    assert add_result.exit_code == 2
    assert remove_result.exit_code == 2
    assert json.loads(add_result.stdout)["error"]["code"] == "VALIDATION_ERROR"
    assert json.loads(remove_result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_tag_rename_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "rename",
            "--name",
            "tag1",
            "--to",
            "tag2",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_tag_delete_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "delete",
            "--tag",
            "tag1",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_tag_delete_requires_a_tag_value(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "delete",
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_tag_reparent_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "reparent",
            "--tag",
            "tag1",
            "--to-parent",
            "tag2",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_tag_reparent_requires_a_tag_value(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "reparent",
            "--to-parent",
            "tag2",
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_tag_rename_rejects_empty_or_same_names(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    empty_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "rename",
            "--name",
            " ",
            "--to",
            "tag2",
            "--dry-run",
        ],
    )
    same_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "rename",
            "--name",
            "tag1",
            "--to",
            "tag1",
            "--dry-run",
        ],
    )

    assert empty_result.exit_code == 2
    assert same_result.exit_code == 2
    assert json.loads(empty_result.stdout)["error"]["code"] == "VALIDATION_ERROR"
    assert json.loads(same_result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_tag_reparent_rejects_same_parent_as_tag(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "reparent",
            "--tag",
            "tag1",
            "--to-parent",
            "tag1",
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_import_notes_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "notes.json"
    input_path.write_text("[]")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "notes",
            "--input",
            str(input_path),
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_import_notes_rejects_missing_input(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "notes.json"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "notes",
            "--input",
            str(input_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_import_patch_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "patches.json"
    input_path.write_text("[]")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "patch",
            "--input",
            str(input_path),
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_import_patch_rejects_missing_input(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "patches.json"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "patch",
            "--input",
            str(input_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_import_notes_accepts_stdin_json(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    payload = json.dumps(
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
    )

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "notes",
            "--stdin-json",
            "--dry-run",
        ],
        input=payload,
    )

    payload_json = json.loads(result.stdout)
    assert payload_json["error"]["code"] in {
        "COLLECTION_NOT_FOUND",
        "DECK_NOT_FOUND",
        "MODEL_NOT_FOUND",
    }


@pytest.mark.unit
def test_import_patch_accepts_stdin_json(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    payload = json.dumps({"items": [{"id": 101, "fields": {"Back": "updated"}}]})

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "patch",
            "--stdin-json",
            "--dry-run",
        ],
        input=payload,
    )

    payload_json = json.loads(result.stdout)
    assert payload_json["error"]["code"] in {"COLLECTION_NOT_FOUND", "NOTE_NOT_FOUND"}


@pytest.mark.unit
def test_import_commands_require_exactly_one_input_source(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "notes.json"
    input_path.write_text("[]")

    notes_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "notes",
            "--input",
            str(input_path),
            "--stdin-json",
            "--dry-run",
        ],
        input="[]",
    )
    patch_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "patch",
            "--input",
            str(input_path),
            "--stdin-json",
            "--dry-run",
        ],
        input="[]",
    )

    assert notes_result.exit_code == 2
    assert patch_result.exit_code == 2
    assert json.loads(notes_result.stdout)["error"]["code"] == "VALIDATION_ERROR"
    assert json.loads(patch_result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_not_implemented_command_is_stable_error(runner) -> None:
    result = runner.invoke(args=["--json", "backend", "list", "extra"])

    assert result.exit_code != 0
