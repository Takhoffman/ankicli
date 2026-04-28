from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from ankicli import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def uv_executable() -> str:
    env_uv = os.environ.get("UV_EXE")
    if env_uv:
        return env_uv
    uv = shutil.which("uv")
    if uv:
        return uv
    bootstrap_uv = (
        PROJECT_ROOT / ".uv-bootstrap" / ("Scripts/uv.exe" if os.name == "nt" else "bin/uv")
    )
    if bootstrap_uv.exists():
        return str(bootstrap_uv)
    return "uv"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as config_home:
        env = os.environ.copy()
        env["UV_CACHE_DIR"] = str(PROJECT_ROOT / ".uv-cache")
        env["ANKICLI_CONFIG_HOME"] = config_home
        return subprocess.run(
            [uv_executable(), "run", "ankicli", *args],
            capture_output=True,
            text=True,
            env=env,
            check=False,
            cwd=PROJECT_ROOT,
        )


@pytest.mark.e2e
def test_doctor_env_e2e() -> None:
    result = run_cli("--json", "doctor", "env")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True


@pytest.mark.e2e
def test_collection_info_missing_collection_e2e() -> None:
    result = run_cli("--json", "collection", "info")

    assert result.returncode == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.e2e
def test_installed_entrypoint_help_e2e() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "collection" in result.stdout


@pytest.mark.e2e
def test_installed_entrypoint_version_e2e() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert result.stdout.strip() == __version__


@pytest.mark.e2e
def test_export_notes_missing_collection_e2e() -> None:
    result = run_cli("--json", "export", "notes", "--query", "")

    assert result.returncode == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.e2e
def test_export_cards_missing_collection_e2e() -> None:
    result = run_cli("--json", "export", "cards", "--query", "")

    assert result.returncode == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.e2e
def test_import_patch_missing_collection_e2e(tmp_path: Path) -> None:
    input_path = tmp_path / "patches.json"
    input_path.write_text("[]")

    result = run_cli("--json", "import", "patch", "--input", str(input_path), "--dry-run")

    assert result.returncode == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.e2e
def test_import_notes_stdin_missing_collection_e2e() -> None:
    with tempfile.TemporaryDirectory() as config_home:
        env = os.environ.copy()
        env["UV_CACHE_DIR"] = str(PROJECT_ROOT / ".uv-cache")
        env["ANKICLI_CONFIG_HOME"] = config_home
        result = subprocess.run(
            [
                uv_executable(),
                "run",
                "ankicli",
                "--json",
                "import",
                "notes",
                "--stdin-json",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            input='{"items":[]}',
            env=env,
            check=False,
            cwd=PROJECT_ROOT,
        )

    assert result.returncode == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"
