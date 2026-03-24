from __future__ import annotations

import importlib.util
import json
import os

import pytest

from ankicli.runtime import configure_anki_source_path


@pytest.mark.backend_python_anki_real
def test_anki_source_path_enables_import() -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")

    configure_anki_source_path()
    assert importlib.util.find_spec("anki") is not None


@pytest.mark.backend_python_anki_real
def test_collection_info_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(args=["--json", "--collection", collection_path, "collection", "info"])

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_collection_stats_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection stats checks")

    result = runner.invoke(args=["--json", "--collection", collection_path, "collection", "stats"])

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_collection_validate_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection validate checks")

    result = runner.invoke(
        args=["--json", "--collection", collection_path, "collection", "validate"],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_collection_lock_status_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection lock-status checks")

    result = runner.invoke(
        args=["--json", "--collection", collection_path, "collection", "lock-status"],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_deck_list_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(args=["--json", "--collection", collection_path, "deck", "list"])

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_deck_get_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    deck_name = os.environ.get("ANKICLI_REAL_DECK")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not deck_name:
        pytest.skip("set ANKICLI_REAL_DECK to run real deck get checks")

    result = runner.invoke(
        args=["--json", "--collection", collection_path, "deck", "get", "--name", deck_name],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_deck_stats_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    deck_name = os.environ.get("ANKICLI_REAL_DECK")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real deck stats checks")
    if not deck_name:
        pytest.skip("set ANKICLI_REAL_DECK to run real deck stats checks")

    result = runner.invoke(
        args=["--json", "--collection", collection_path, "deck", "stats", "--name", deck_name],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_deck_create_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real deck create checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "deck",
            "create",
            "--name",
            "ankicli-real-dry-run",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_deck_rename_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    deck_name = os.environ.get("ANKICLI_REAL_DECK")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real deck rename checks")
    if not deck_name:
        pytest.skip("set ANKICLI_REAL_DECK to run real deck rename checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "deck",
            "rename",
            "--name",
            deck_name,
            "--to",
            f"{deck_name}-renamed",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_deck_delete_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    deck_name = os.environ.get("ANKICLI_REAL_DECK")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real deck delete checks")
    if not deck_name:
        pytest.skip("set ANKICLI_REAL_DECK to run real deck delete checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "deck",
            "delete",
            "--name",
            deck_name,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_deck_reparent_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    deck_name = os.environ.get("ANKICLI_REAL_DECK")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real deck reparent checks")
    if not deck_name:
        pytest.skip("set ANKICLI_REAL_DECK to run real deck reparent checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "deck",
            "reparent",
            "--name",
            deck_name,
            "--to-parent",
            "",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_model_list_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(args=["--json", "--collection", collection_path, "model", "list"])

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_model_get_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    model_name = os.environ.get("ANKICLI_REAL_MODEL")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not model_name:
        pytest.skip("set ANKICLI_REAL_MODEL to run real model get checks")

    result = runner.invoke(
        args=["--json", "--collection", collection_path, "model", "get", "--name", model_name],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_media_list_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real media list checks")

    result = runner.invoke(args=["--json", "--collection", collection_path, "media", "list"])

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_media_check_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real media check checks")

    result = runner.invoke(args=["--json", "--collection", collection_path, "media", "check"])

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_media_attach_real_backend_dry_run(runner, tmp_path) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real media attach checks")
    source_path = tmp_path / "upload.txt"
    source_path.write_text("hello")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "media",
            "attach",
            "--source",
            str(source_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_model_fields_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    model_name = os.environ.get("ANKICLI_REAL_MODEL")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real model fields checks")
    if not model_name:
        pytest.skip("set ANKICLI_REAL_MODEL to run real model fields checks")

    result = runner.invoke(
        args=["--json", "--collection", collection_path, "model", "fields", "--name", model_name],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_model_templates_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    model_name = os.environ.get("ANKICLI_REAL_MODEL")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real model templates checks")
    if not model_name:
        pytest.skip("set ANKICLI_REAL_MODEL to run real model templates checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "model",
            "templates",
            "--name",
            model_name,
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_model_validate_note_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    model_name = os.environ.get("ANKICLI_REAL_MODEL")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real model validate checks")
    if not model_name:
        pytest.skip("set ANKICLI_REAL_MODEL to run real model validate checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "model",
            "validate-note",
            "--model",
            model_name,
            "--field",
            "Front=hello",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_tag_list_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(args=["--json", "--collection", collection_path, "tag", "list"])

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_tag_rename_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    tag_name = os.environ.get("ANKICLI_REAL_TAG")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not tag_name:
        pytest.skip("set ANKICLI_REAL_TAG to run real tag rename checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "tag",
            "rename",
            "--name",
            tag_name,
            "--to",
            f"{tag_name}-renamed",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_tag_delete_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    tag_name = os.environ.get("ANKICLI_REAL_TAG")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not tag_name:
        pytest.skip("set ANKICLI_REAL_TAG to run real tag delete checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "tag",
            "delete",
            "--tag",
            tag_name,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_tag_reparent_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    tag_name = os.environ.get("ANKICLI_REAL_TAG")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not tag_name:
        pytest.skip("set ANKICLI_REAL_TAG to run real tag reparent checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "tag",
            "reparent",
            "--tag",
            tag_name,
            "--to-parent",
            "",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_search_notes_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "search",
            "notes",
            "--query",
            "",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_search_cards_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "search",
            "cards",
            "--query",
            "",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_search_count_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real search count checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "search",
            "count",
            "--kind",
            "notes",
            "--query",
            "",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_search_preview_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real search preview checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
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


@pytest.mark.backend_python_anki_real
def test_export_notes_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "export",
            "notes",
            "--query",
            "",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_export_notes_real_backend_ndjson(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(
        args=[
            "--collection",
            collection_path,
            "export",
            "notes",
            "--query",
            "",
            "--ndjson",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_export_cards_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "export",
            "cards",
            "--query",
            "",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_export_cards_real_backend_ndjson(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")

    result = runner.invoke(
        args=[
            "--collection",
            collection_path,
            "export",
            "cards",
            "--query",
            "",
            "--ndjson",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_note_get_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    note_id = os.environ.get("ANKICLI_REAL_NOTE_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not note_id:
        pytest.skip("set ANKICLI_REAL_NOTE_ID to run real note get checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "note",
            "get",
            "--id",
            note_id,
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_note_fields_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    note_id = os.environ.get("ANKICLI_REAL_NOTE_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not note_id:
        pytest.skip("set ANKICLI_REAL_NOTE_ID to run real note fields checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "note",
            "fields",
            "--id",
            note_id,
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_card_get_real_backend(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    card_id = os.environ.get("ANKICLI_REAL_CARD_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not card_id:
        pytest.skip("set ANKICLI_REAL_CARD_ID to run real card get checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "card",
            "get",
            "--id",
            card_id,
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_note_add_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    deck_name = os.environ.get("ANKICLI_REAL_DECK")
    model_name = os.environ.get("ANKICLI_REAL_MODEL")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not deck_name:
        pytest.skip("set ANKICLI_REAL_DECK to run real note add checks")
    if not model_name:
        pytest.skip("set ANKICLI_REAL_MODEL to run real note add checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "note",
            "add",
            "--deck",
            deck_name,
            "--model",
            model_name,
            "--field",
            "Front=hello",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_import_notes_real_backend_dry_run(runner, tmp_path) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    deck_name = os.environ.get("ANKICLI_REAL_DECK")
    model_name = os.environ.get("ANKICLI_REAL_MODEL")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not deck_name:
        pytest.skip("set ANKICLI_REAL_DECK to run real import notes checks")
    if not model_name:
        pytest.skip("set ANKICLI_REAL_MODEL to run real import notes checks")

    input_path = tmp_path / "notes.json"
    input_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "deck": deck_name,
                        "model": model_name,
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
            collection_path,
            "import",
            "notes",
            "--input",
            str(input_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_import_notes_real_backend_stdin_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    deck_name = os.environ.get("ANKICLI_REAL_DECK")
    model_name = os.environ.get("ANKICLI_REAL_MODEL")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not deck_name:
        pytest.skip("set ANKICLI_REAL_DECK to run real import notes checks")
    if not model_name:
        pytest.skip("set ANKICLI_REAL_MODEL to run real import notes checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "import",
            "notes",
            "--stdin-json",
            "--dry-run",
        ],
        input=json.dumps(
            {
                "items": [
                    {
                        "deck": deck_name,
                        "model": model_name,
                        "fields": {"Front": "hello", "Back": "world"},
                        "tags": ["tag1"],
                    },
                ],
            },
        ),
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_import_patch_real_backend_dry_run(runner, tmp_path) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    note_id = os.environ.get("ANKICLI_REAL_NOTE_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not note_id:
        pytest.skip("set ANKICLI_REAL_NOTE_ID to run real import patch checks")

    input_path = tmp_path / "patches.json"
    input_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": int(note_id),
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
            collection_path,
            "import",
            "patch",
            "--input",
            str(input_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_import_patch_real_backend_stdin_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    note_id = os.environ.get("ANKICLI_REAL_NOTE_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not note_id:
        pytest.skip("set ANKICLI_REAL_NOTE_ID to run real import patch checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "import",
            "patch",
            "--stdin-json",
            "--dry-run",
        ],
        input=json.dumps({"items": [{"id": int(note_id), "fields": {"Back": "updated"}}]}),
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_note_update_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    note_id = os.environ.get("ANKICLI_REAL_NOTE_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not note_id:
        pytest.skip("set ANKICLI_REAL_NOTE_ID to run real note update checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "note",
            "update",
            "--id",
            note_id,
            "--field",
            "Front=hello",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_note_move_deck_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    note_id = os.environ.get("ANKICLI_REAL_NOTE_ID")
    deck_name = os.environ.get("ANKICLI_REAL_DECK")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not note_id:
        pytest.skip("set ANKICLI_REAL_NOTE_ID to run real note move-deck checks")
    if not deck_name:
        pytest.skip("set ANKICLI_REAL_DECK to run real note move-deck checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
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


@pytest.mark.backend_python_anki_real
def test_note_add_tags_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    note_id = os.environ.get("ANKICLI_REAL_NOTE_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not note_id:
        pytest.skip("set ANKICLI_REAL_NOTE_ID to run real note tag add checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "note",
            "add-tags",
            "--id",
            note_id,
            "--tag",
            "tag3",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_note_remove_tags_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    note_id = os.environ.get("ANKICLI_REAL_NOTE_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not note_id:
        pytest.skip("set ANKICLI_REAL_NOTE_ID to run real note tag remove checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "note",
            "remove-tags",
            "--id",
            note_id,
            "--tag",
            "tag1",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_note_delete_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    note_id = os.environ.get("ANKICLI_REAL_NOTE_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not note_id:
        pytest.skip("set ANKICLI_REAL_NOTE_ID to run real note delete checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "note",
            "delete",
            "--id",
            note_id,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_card_suspend_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    card_id = os.environ.get("ANKICLI_REAL_CARD_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not card_id:
        pytest.skip("set ANKICLI_REAL_CARD_ID to run real card suspend checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "card",
            "suspend",
            "--id",
            card_id,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


@pytest.mark.backend_python_anki_real
def test_card_unsuspend_real_backend_dry_run(runner) -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki setup checks")
    collection_path = os.environ.get("ANKICLI_REAL_COLLECTION")
    card_id = os.environ.get("ANKICLI_REAL_CARD_ID")
    if not collection_path:
        pytest.skip("set ANKICLI_REAL_COLLECTION to run real collection info checks")
    if not card_id:
        pytest.skip("set ANKICLI_REAL_CARD_ID to run real card unsuspend checks")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            collection_path,
            "card",
            "unsuspend",
            "--id",
            card_id,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
