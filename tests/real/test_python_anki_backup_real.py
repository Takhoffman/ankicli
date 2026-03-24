from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sqlite3
from pathlib import Path

import pytest

from ankicli.runtime import configure_anki_source_path
from tests.proof import proves


def _require_real_python_anki() -> None:
    if not os.environ.get("ANKI_SOURCE_PATH"):
        pytest.skip("set ANKI_SOURCE_PATH to run real python-anki backup checks")
    configure_anki_source_path()
    if importlib.util.find_spec("anki") is None:
        pytest.skip("real anki runtime is not importable from ANKI_SOURCE_PATH")


def _write_profiles_db(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "prefs21.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("create table profiles(name text primary key, data blob not null)")
        connection.execute("insert into profiles values ('_global', x'00')")
        connection.execute("insert into profiles values ('User 1', x'00')")
        connection.commit()


def _seed_collection(collection_path: Path) -> dict[str, int]:
    collection_module = importlib.import_module("anki.collection")
    Collection = collection_module.Collection

    collection_path.parent.mkdir(parents=True, exist_ok=True)
    col = Collection(str(collection_path))
    try:
        model = col.models.by_name("Basic")
        if model is None:
            raise RuntimeError('Expected stock model "Basic" to exist')
        deck_id = None
        for deck in col.decks.all_names_and_ids():
            if deck.name == "Default":
                deck_id = int(deck.id)
                break
        if deck_id is None:
            raise RuntimeError('Expected stock deck "Default" to exist')

        note = col.new_note(model)
        note["Front"] = "backup seed front"
        note["Back"] = "backup seed back"
        col.add_note(note, deck_id)
        note_id = int(note.id)
        card_ids = [int(card_id) for card_id in col.find_cards("")]
        if not card_ids:
            raise RuntimeError("Expected at least one card in disposable collection")
        return {"note_id": note_id, "card_id": card_ids[0]}
    finally:
        col.close()


@pytest.fixture()
def disposable_profile_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, str | int]:
    _require_real_python_anki()
    root = tmp_path / "Anki2"
    profile_dir = root / "User 1"
    (profile_dir / "collection.media").mkdir(parents=True)
    (profile_dir / "backups").mkdir(parents=True)
    _write_profiles_db(root)
    collection_path = profile_dir / "collection.anki2"
    seeded = _seed_collection(collection_path)
    monkeypatch.setenv("ANKICLI_ANKI2_ROOT", str(root))
    return {
        "profile": "User 1",
        "root": str(root),
        "collection_path": str(collection_path),
        "note_id": seeded["note_id"],
        "card_id": seeded["card_id"],
    }


def _payload(result) -> dict:
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)


@pytest.mark.backend_python_anki_backup_real
def test_real_python_anki_runtime_exposes_backup_methods() -> None:
    _require_real_python_anki()
    collection_module = importlib.import_module("anki.collection")
    Collection = collection_module.Collection

    assert hasattr(Collection, "create_backup")
    assert hasattr(Collection, "sync_login")
    assert hasattr(Collection, "sync_status")
    assert hasattr(Collection, "sync_collection")


@pytest.mark.backend_python_anki_backup_real
@proves("backup.status", "real_python_anki")
@proves("backup.list", "real_python_anki")
@proves("backup.create", "real_python_anki")
@proves("backup.get", "real_python_anki")
@proves("profile.list", "real_python_anki")
@proves("profile.default", "real_python_anki")
@proves("profile.resolve", "real_python_anki")
def test_profile_commands_with_disposable_root(
    runner,
    disposable_profile_root: dict[str, str | int],
) -> None:
    profile = str(disposable_profile_root["profile"])

    list_payload = _payload(runner.invoke(args=["--json", "profile", "list"]))
    default_payload = _payload(runner.invoke(args=["--json", "profile", "default"]))
    resolve_payload = _payload(
        runner.invoke(args=["--json", "profile", "resolve", "--name", profile]),
    )

    assert any(item["name"] == profile for item in list_payload["data"]["items"])
    assert default_payload["data"]["name"] == profile
    assert resolve_payload["data"]["collection_path"].endswith("User 1/collection.anki2")


@pytest.mark.backend_python_anki_backup_real
def test_backup_status_list_create_and_get_real(
    runner,
    disposable_profile_root: dict[str, str | int],
) -> None:
    profile = str(disposable_profile_root["profile"])

    status_before = _payload(
        runner.invoke(args=["--json", "--profile", profile, "backup", "status"]),
    )
    list_before = _payload(runner.invoke(args=["--json", "--profile", profile, "backup", "list"]))
    create_payload = _payload(
        runner.invoke(args=["--json", "--profile", profile, "backup", "create"]),
    )
    list_after = _payload(runner.invoke(args=["--json", "--profile", profile, "backup", "list"]))
    get_payload = _payload(
        runner.invoke(
            args=[
                "--json",
                "--profile",
                profile,
                "backup",
                "get",
                "--name",
                create_payload["data"]["name"],
            ],
        ),
    )

    assert status_before["data"]["profile"] == profile
    assert list_before["data"]["items"] == []
    assert create_payload["data"]["created"] is True
    assert create_payload["data"]["name"]
    assert len(list_after["data"]["items"]) == 1
    assert get_payload["data"]["name"] == create_payload["data"]["name"]


@pytest.mark.backend_python_anki_backup_real
@proves("backup.restore", "real_python_anki")
def test_backup_restore_round_trip_real(
    runner,
    disposable_profile_root: dict[str, str | int],
) -> None:
    profile = str(disposable_profile_root["profile"])

    initial_stats = _payload(
        runner.invoke(args=["--json", "--profile", profile, "collection", "stats"]),
    )
    create_payload = _payload(
        runner.invoke(args=["--json", "--profile", profile, "backup", "create"]),
    )
    mutated = _payload(
        runner.invoke(
            args=[
                "--json",
                "--profile",
                profile,
                "--no-auto-backup",
                "deck",
                "create",
                "--name",
                "restore-roundtrip-deck",
                "--yes",
            ],
        ),
    )
    mutated_stats = _payload(
        runner.invoke(args=["--json", "--profile", profile, "collection", "stats"]),
    )
    restore_payload = _payload(
        runner.invoke(
            args=[
                "--json",
                "--profile",
                profile,
                "backup",
                "restore",
                "--name",
                create_payload["data"]["name"],
                "--yes",
            ],
        ),
    )
    restored_stats = _payload(
        runner.invoke(args=["--json", "--profile", profile, "collection", "stats"]),
    )

    assert mutated["data"]["name"] == "restore-roundtrip-deck"
    assert mutated_stats["data"]["deck_count"] == initial_stats["data"]["deck_count"] + 1
    assert restore_payload["data"]["restored"] is True
    assert restore_payload["data"]["safety_backup_name"] is not None
    assert restore_payload["data"]["safety_backup_path"] is not None
    assert restored_stats["data"]["deck_count"] == initial_stats["data"]["deck_count"]


@pytest.mark.backend_python_anki_backup_real
@proves("deck.create", "real_python_anki")
def test_real_risky_write_includes_auto_backup_metadata(
    runner,
    disposable_profile_root: dict[str, str | int],
) -> None:
    profile = str(disposable_profile_root["profile"])

    payload = _payload(
        runner.invoke(
            args=[
                "--json",
                "--profile",
                profile,
                "deck",
                "create",
                "--name",
                "auto-backup-deck",
                "--yes",
            ],
        ),
    )

    assert payload["data"]["auto_backup_created"] is True
    assert payload["data"]["auto_backup_name"] is not None
    assert payload["data"]["auto_backup_path"] is not None


@pytest.mark.backend_python_anki_backup_real
def test_real_risky_write_respects_no_auto_backup(
    runner,
    disposable_profile_root: dict[str, str | int],
) -> None:
    profile = str(disposable_profile_root["profile"])

    payload = _payload(
        runner.invoke(
            args=[
                "--json",
                "--profile",
                profile,
                "--no-auto-backup",
                "deck",
                "create",
                "--name",
                "no-auto-backup-deck",
                "--yes",
            ],
        ),
    )

    assert payload["data"]["auto_backup_created"] is False
    assert payload["data"]["auto_backup_name"] is None
    assert payload["data"]["auto_backup_path"] is None


@pytest.mark.backend_python_anki_backup_real
def test_backup_restore_requires_yes_real(
    runner,
    disposable_profile_root: dict[str, str | int],
) -> None:
    profile = str(disposable_profile_root["profile"])
    create_payload = _payload(
        runner.invoke(args=["--json", "--profile", profile, "backup", "create"]),
    )

    result = runner.invoke(
        args=[
            "--json",
            "--profile",
            profile,
            "backup",
            "restore",
            "--name",
            create_payload["data"]["name"],
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.backend_python_anki_backup_real
def test_backup_get_unknown_name_real(
    runner,
    disposable_profile_root: dict[str, str | int],
) -> None:
    profile = str(disposable_profile_root["profile"])

    result = runner.invoke(
        args=["--json", "--profile", profile, "backup", "get", "--name", "missing.colpkg"],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKUP_NOT_FOUND"


@pytest.mark.backend_python_anki_backup_real
def test_backup_restore_unknown_name_real(
    runner,
    disposable_profile_root: dict[str, str | int],
) -> None:
    profile = str(disposable_profile_root["profile"])

    result = runner.invoke(
        args=[
            "--json",
            "--profile",
            profile,
            "backup",
            "restore",
            "--name",
            "missing.colpkg",
            "--yes",
        ],
    )

    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKUP_NOT_FOUND"
