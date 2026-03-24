from __future__ import annotations

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
    wheels = sorted(DIST_DIR.glob("ankicli-*.whl"))
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

        help_result = _run([str(cli_bin), "--help"])
        assert help_result.returncode == 0, help_result.stderr
        assert "collection" in help_result.stdout

        version_result = _run([str(cli_bin), "--version"])
        assert version_result.returncode == 0, version_result.stderr
        assert version_result.stdout.strip()
