from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ankicli.app.errors import ProfileNotFoundError
from ankicli.app.profiles import ProfileResolver, default_anki2_root


def _write_profiles_db(root: Path, names: list[str]) -> None:
    db_path = root / "prefs21.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("create table profiles(name text primary key, data blob not null)")
        connection.execute("insert into profiles values ('_global', x'00')")
        for name in names:
            connection.execute("insert into profiles values (?, x'00')", (name,))
        connection.commit()


@pytest.mark.unit
def test_profile_resolver_lists_profiles_from_prefs_db(tmp_path: Path) -> None:
    root = tmp_path / "Anki2"
    root.mkdir()
    _write_profiles_db(root, ["User 1", "Spanish"])
    (root / "User 1").mkdir()
    (root / "User 1" / "collection.anki2").write_text("fixture")
    (root / "Spanish").mkdir()
    (root / "Spanish" / "collection.anki2").write_text("fixture")

    result = ProfileResolver(data_root=root).list_profiles()

    assert [profile.name for profile in result] == ["Spanish", "User 1"]
    assert result[0].collection_path.name == "collection.anki2"


@pytest.mark.unit
def test_profile_resolver_default_prefers_user_1(tmp_path: Path) -> None:
    root = tmp_path / "Anki2"
    root.mkdir()
    _write_profiles_db(root, ["Spanish", "User 1"])
    for name in ("Spanish", "User 1"):
        (root / name).mkdir()
        (root / name / "collection.anki2").write_text("fixture")

    result = ProfileResolver(data_root=root).default_profile()

    assert result.name == "User 1"


@pytest.mark.unit
def test_profile_resolver_resolve_collection_infers_known_profile(tmp_path: Path) -> None:
    root = tmp_path / "Anki2"
    root.mkdir()
    (root / "User 1").mkdir()
    collection_path = root / "User 1" / "collection.anki2"
    collection_path.write_text("fixture")

    result = ProfileResolver(data_root=root).resolve_collection(collection_path)

    assert result.name == "User 1"
    assert result.known_profile is True
    assert result.backup_dir.name == "backups"


@pytest.mark.unit
def test_profile_resolver_raises_for_unknown_profile(tmp_path: Path) -> None:
    root = tmp_path / "Anki2"
    root.mkdir()
    _write_profiles_db(root, ["User 1"])
    (root / "User 1").mkdir()
    (root / "User 1" / "collection.anki2").write_text("fixture")

    with pytest.raises(ProfileNotFoundError):
        ProfileResolver(data_root=root).resolve_profile("Missing")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("system_name", "env_key", "env_value", "expected_suffix"),
    [
        ("Darwin", None, None, "Library/Application Support/Anki2"),
        ("Windows", "APPDATA", "/tmp/AppData/Roaming", "Anki2"),
        ("Linux", "XDG_DATA_HOME", "/tmp/.local/share", "Anki2"),
    ],
)
def test_default_anki2_root_uses_platform_defaults(
    monkeypatch: pytest.MonkeyPatch,
    system_name: str,
    env_key: str | None,
    env_value: str | None,
    expected_suffix: str,
) -> None:
    monkeypatch.setattr("platform.system", lambda: system_name)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    if env_key and env_value:
        monkeypatch.setenv(env_key, env_value)

    result = default_anki2_root()

    assert result.as_posix().endswith(expected_suffix.replace("\\", "/"))
