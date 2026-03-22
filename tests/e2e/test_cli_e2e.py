from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(PROJECT_ROOT / ".uv-cache")
    return subprocess.run(
        ["uv", "run", "ankicli", *args],
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
