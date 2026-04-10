"""Human-facing workspace configuration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ankicli.app.errors import ValidationError

SUPPORTED_BACKENDS = {"python-anki", "ankiconnect"}
DEFAULT_WORKSPACE = "default"


@dataclass(slots=True)
class WorkspaceConfig:
    """Saved target defaults for one operator workspace."""

    anki_profile: str | None = None
    collection: str | None = None
    backend: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "anki_profile": self.anki_profile,
            "collection": self.collection,
            "backend": self.backend,
        }


def default_config_root() -> Path:
    override = os.environ.get("ANKICLI_CONFIG_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".ankicli"


def workspaces_root() -> Path:
    return default_config_root() / "workspaces"


def active_workspace_path() -> Path:
    return default_config_root() / "active-workspace"


def normalize_workspace_name(name: str | None) -> str:
    normalized = (name or DEFAULT_WORKSPACE).strip()
    if not normalized:
        raise ValidationError("Workspace name must not be empty")
    if normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
        raise ValidationError(
            "Workspace name must be a simple folder name",
            details={"workspace": normalized},
        )
    return normalized


def workspace_root(name: str | None = None) -> Path:
    return workspaces_root() / normalize_workspace_name(name)


def workspace_config_path(name: str | None = None) -> Path:
    return workspace_root(name) / "config.json"


def active_workspace_config_path() -> Path:
    return workspace_config_path(active_workspace())


def _normalized_optional(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def active_workspace() -> str:
    path = active_workspace_path()
    if not path.exists():
        return DEFAULT_WORKSPACE
    return normalize_workspace_name(path.read_text(encoding="utf-8"))


def set_active_workspace(name: str) -> Path:
    normalized_name = normalize_workspace_name(name)
    path = active_workspace_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(normalized_name + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def list_workspaces() -> list[str]:
    root = workspaces_root()
    if not root.exists():
        return []
    return sorted(entry.name for entry in root.iterdir() if entry.is_dir())


def _parse_config_payload(payload: Any, *, path: Path) -> WorkspaceConfig:
    if not isinstance(payload, dict):
        raise ValidationError(
            "ankicli workspace config file must contain a JSON object",
            details={"path": str(path)},
        )
    config = WorkspaceConfig(
        anki_profile=_normalized_optional(payload.get("anki_profile")),
        collection=_normalized_optional(payload.get("collection")),
        backend=_normalized_optional(payload.get("backend")),
    )
    validate_config(config, path=path)
    return config


def validate_config(config: WorkspaceConfig, *, path: Path | None = None) -> None:
    details = {"path": str(path)} if path else {}
    if config.anki_profile and config.collection:
        raise ValidationError(
            "anki_profile and collection are mutually exclusive",
            details=details,
        )
    if config.backend and config.backend not in SUPPORTED_BACKENDS:
        raise ValidationError(
            f"Unsupported backend: {config.backend}",
            details={**details, "supported_backends": sorted(SUPPORTED_BACKENDS)},
        )


def load_workspace_config(name: str | None = None) -> WorkspaceConfig:
    config_path = workspace_config_path(name).expanduser()
    if not config_path.exists():
        return WorkspaceConfig()
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "ankicli workspace config file is not valid JSON",
            details={"path": str(config_path), "reason": str(exc)},
        ) from exc
    return _parse_config_payload(payload, path=config_path)


def save_workspace_config(config: WorkspaceConfig, name: str | None = None) -> Path:
    config_path = workspace_config_path(name).expanduser()
    validate_config(config, path=config_path)
    config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        config_path.chmod(0o600)
    except OSError:
        pass
    return config_path


def workspace_item(name: str) -> dict:
    config = load_workspace_config(name)
    return {
        "name": normalize_workspace_name(name),
        "root": str(workspace_root(name).expanduser()),
        "config_path": str(workspace_config_path(name).expanduser()),
        "config_exists": workspace_config_path(name).expanduser().exists(),
        **config.to_dict(),
    }


def workspace_report(name: str | None = None, config: WorkspaceConfig | None = None) -> dict:
    workspace_name = normalize_workspace_name(name or active_workspace())
    config_path = workspace_config_path(workspace_name).expanduser()
    resolved_config = config or load_workspace_config(workspace_name)
    return {
        "config_root": str(default_config_root().expanduser()),
        "workspaces_root": str(workspaces_root().expanduser()),
        "active_workspace_path": str(active_workspace_path().expanduser()),
        "active_workspace": active_workspace(),
        "selected_workspace": workspace_name,
        "workspace_root": str(workspace_root(workspace_name).expanduser()),
        "config_path": str(config_path),
        "config_exists": config_path.exists(),
        "workspace_config": resolved_config.to_dict(),
        "workspaces": list_workspaces(),
    }
