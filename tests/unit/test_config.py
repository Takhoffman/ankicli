from __future__ import annotations

from pathlib import Path

import pytest

from ankicli.app.config import (
    WorkspaceConfig,
    active_workspace,
    active_workspace_config_path,
    load_workspace_config,
    save_workspace_config,
    set_active_workspace,
    workspace_config_path,
)
from ankicli.app.errors import ValidationError


@pytest.mark.unit
def test_active_workspace_config_path_uses_default_workspace_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANKICLI_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: Path("/home/user"))

    assert active_workspace_config_path() == Path(
        "/home/user/.ankicli/workspaces/default/config.json"
    )


@pytest.mark.unit
def test_workspace_config_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANKICLI_CONFIG_HOME", str(tmp_path))
    config = WorkspaceConfig(anki_profile="User 1")

    path = save_workspace_config(config, "default")

    assert path == tmp_path / "workspaces/default/config.json"
    assert load_workspace_config("default") == config
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.unit
def test_active_workspace_round_trip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANKICLI_CONFIG_HOME", str(tmp_path))

    set_active_workspace("travel")

    assert active_workspace() == "travel"
    assert active_workspace_config_path() == tmp_path / "workspaces/travel/config.json"


@pytest.mark.unit
def test_workspace_config_rejects_profile_and_collection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANKICLI_CONFIG_HOME", str(tmp_path))

    with pytest.raises(ValidationError):
        save_workspace_config(
            WorkspaceConfig(anki_profile="User 1", collection="/tmp/collection.anki2"),
            "default",
        )


@pytest.mark.unit
def test_workspace_config_rejects_unsupported_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANKICLI_CONFIG_HOME", str(tmp_path))

    with pytest.raises(ValidationError):
        save_workspace_config(WorkspaceConfig(backend="unsupported"), "default")


@pytest.mark.unit
def test_workspace_name_must_be_folder_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANKICLI_CONFIG_HOME", str(tmp_path))

    with pytest.raises(ValidationError):
        workspace_config_path("../bad")
