"""Profile resolution for local Anki data."""

from __future__ import annotations

import os
import platform
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ankicli.app.errors import ProfileNotFoundError, ProfileResolutionError


def default_anki2_root() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library/Application Support/Anki2"
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Anki2"
        return Path.home() / "AppData/Roaming/Anki2"
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "Anki2"
    return Path.home() / ".local/share/Anki2"


@dataclass(slots=True)
class ProfileContext:
    name: str | None
    data_root: Path
    profile_dir: Path
    collection_path: Path
    media_dir: Path
    media_db_path: Path
    backup_dir: Path
    known_profile: bool

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "data_root": str(self.data_root),
            "profile_dir": str(self.profile_dir),
            "collection_path": str(self.collection_path),
            "media_dir": str(self.media_dir),
            "media_db_path": str(self.media_db_path),
            "backup_dir": str(self.backup_dir),
            "known_profile": self.known_profile,
            "exists": self.collection_path.exists(),
        }


class ProfileResolver:
    """Resolve local Anki profiles and their collection paths."""

    def __init__(self, *, data_root: Path | None = None) -> None:
        self.data_root = (data_root or self._default_data_root()).expanduser().resolve()

    def _default_data_root(self) -> Path:
        override = os.environ.get("ANKICLI_ANKI2_ROOT")
        if override:
            return Path(override)
        return default_anki2_root()

    def _prefs_db(self) -> Path:
        return self.data_root / "prefs21.db"

    def _load_profile_names(self) -> list[str]:
        prefs_db = self._prefs_db()
        if prefs_db.exists():
            try:
                with sqlite3.connect(prefs_db) as connection:
                    rows = connection.execute(
                        "select name from profiles "
                        "where name != '_global' "
                        "order by name collate nocase"
                    ).fetchall()
                names = [str(row[0]) for row in rows if row and row[0]]
                if names:
                    return names
            except sqlite3.Error as exc:
                raise ProfileResolutionError(
                    f"Failed to read Anki profiles from {prefs_db}",
                    details={"path": str(prefs_db), "reason": str(exc)},
                ) from exc
        return sorted(
            entry.name
            for entry in self.data_root.iterdir()
            if entry.is_dir() and (entry / "collection.anki2").exists()
        )

    def _build_context(
        self,
        *,
        name: str | None,
        profile_dir: Path,
        known_profile: bool,
    ) -> ProfileContext:
        return ProfileContext(
            name=name,
            data_root=self.data_root,
            profile_dir=profile_dir.resolve(),
            collection_path=(profile_dir / "collection.anki2").resolve(),
            media_dir=(profile_dir / "collection.media").resolve(),
            media_db_path=(profile_dir / "collection.media.db2").resolve(),
            backup_dir=(profile_dir / "backups").resolve(),
            known_profile=known_profile,
        )

    def list_profiles(self) -> list[ProfileContext]:
        if not self.data_root.exists():
            raise ProfileResolutionError(
                f"Anki data root does not exist: {self.data_root}",
                details={"path": str(self.data_root)},
            )
        return [
            self._build_context(
                name=name,
                profile_dir=self.data_root / name,
                known_profile=True,
            )
            for name in self._load_profile_names()
        ]

    def default_profile(self) -> ProfileContext:
        profiles = self.list_profiles()
        if not profiles:
            raise ProfileNotFoundError(
                "No local Anki profiles were found",
                details={"data_root": str(self.data_root)},
            )
        if len(profiles) == 1:
            return profiles[0]
        for profile in profiles:
            if profile.name == "User 1":
                return profile
        return profiles[0]

    def resolve_profile(self, name: str) -> ProfileContext:
        normalized = name.strip()
        if not normalized:
            raise ProfileResolutionError("--profile must not be empty")
        for profile in self.list_profiles():
            if profile.name and profile.name.casefold() == normalized.casefold():
                return profile
        raise ProfileNotFoundError(
            f'Profile "{name}" was not found',
            details={"profile": name, "data_root": str(self.data_root)},
        )

    def resolve_collection(self, collection_path: str | Path) -> ProfileContext:
        resolved = Path(collection_path).expanduser().resolve()
        profile_dir = resolved.parent
        name = (
            profile_dir.name
            if profile_dir.parent == self.data_root and resolved.name == "collection.anki2"
            else None
        )
        return self._build_context(
            name=name,
            profile_dir=profile_dir,
            known_profile=name is not None,
        )
