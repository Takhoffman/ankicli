from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = PROJECT_ROOT / "dist"


def _run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd or PROJECT_ROOT,
        env=env,
    )


@pytest.mark.distribution
def test_built_wheel_installs_and_exposes_cli() -> None:
    wheels = sorted(DIST_DIR.glob("anki_agent_toolkit-*.whl"))
    assert wheels, "run `uv build` before executing distribution tests"

    wheel = wheels[-1]
    with tempfile.TemporaryDirectory(prefix="ankicli-dist-") as temp_dir:
        temp_path = Path(temp_dir)
        venv_path = temp_path / "venv"

        create_venv = _run([sys.executable, "-m", "venv", str(venv_path)])
        assert create_venv.returncode == 0, create_venv.stderr

        if os.name == "nt":
            python_bin = venv_path / "Scripts" / "python.exe"
            cli_bin = venv_path / "Scripts" / "ankicli.exe"
        else:
            python_bin = venv_path / "bin" / "python"
            cli_bin = venv_path / "bin" / "ankicli"

        install = _run([str(python_bin), "-m", "pip", "install", str(wheel)])
        assert install.returncode == 0, install.stderr
        assert cli_bin.exists()

        backend_result = _run([str(cli_bin), "--json", "doctor", "backend"])
        assert backend_result.returncode == 0, backend_result.stderr
        backend_payload = json.loads(backend_result.stdout)
        assert backend_payload["data"]["name"] == "python-anki"
        assert backend_payload["data"]["available"] is True
        assert backend_payload["data"]["supported_runtime"] is True
        assert backend_payload["data"]["runtime_failure_reason"] is None
        assert backend_payload["data"]["default_anki2_root"]
        assert backend_payload["data"]["credential_storage_backend"] in {
            "keyring",
            "file-fallback",
        }
        assert backend_payload["data"]["credential_storage_available"] is True

        env_result = _run([str(cli_bin), "--json", "doctor", "env"])
        assert env_result.returncode == 0, env_result.stderr
        env_payload = json.loads(env_result.stdout)
        assert env_payload["data"]["default_anki2_root"]
        assert env_payload["data"]["credential_storage_backend"] in {
            "keyring",
            "file-fallback",
        }
        assert env_payload["data"]["credential_storage_available"] is True

        help_result = _run([str(cli_bin), "--help"])
        assert help_result.returncode == 0, help_result.stderr
        assert "collection" in help_result.stdout
        assert "skill" in help_result.stdout

        skill_list_result = _run([str(cli_bin), "--json", "skill", "list"])
        assert skill_list_result.returncode == 0, skill_list_result.stderr
        skill_list_payload = json.loads(skill_list_result.stdout)
        assert skill_list_payload["data"]["items"][0]["name"] == "ankicli"

        skill_root = temp_path / "agent-skills"
        skill_install_result = _run(
            [str(cli_bin), "--json", "skill", "install", "--path", str(skill_root)]
        )
        assert skill_install_result.returncode == 0, skill_install_result.stderr
        assert (skill_root / "ankicli" / "SKILL.md").exists()
        assert (skill_root / "ankicli" / "references" / "setup.md").exists()

        version_result = _run([str(cli_bin), "--version"])
        assert version_result.returncode == 0, version_result.stderr
        assert version_result.stdout.strip()
