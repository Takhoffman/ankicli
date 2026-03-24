#!/usr/bin/env python3
"""Run the explicit higher-assurance matrix workflow."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the aggregated phase3 proof workflow for ankicli.",
    )
    parser.add_argument(
        "--tests-root",
        default="tests",
        help="Path to the tests root to scan for proof annotations.",
    )
    parser.add_argument(
        "--matrix",
        default="ops/test-matrix.yaml",
        help="Path to the matrix YAML file.",
    )
    return parser.parse_args()


def _run(command: list[str], *, env: dict[str, str]) -> None:
    result = subprocess.run(command, env=env, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    args = parse_args()
    if not os.environ.get("ANKI_SOURCE_PATH"):
        print(
            "phase3 requires ANKI_SOURCE_PATH so the real python-anki proof tier can run",
            file=sys.stderr,
        )
        return 2

    repo_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTEST_PLUGINS"] = "ankicli.pytest_plugin"

    with tempfile.TemporaryDirectory(prefix="ankicli-phase3-") as tmpdir:
        reports_dir = Path(tmpdir)
        fast_report = reports_dir / "fast.json"
        fixture_report = reports_dir / "fixture.json"
        real_report = reports_dir / "real-python-anki.json"

        pytest_base = [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str((repo_root / "pyproject.toml").resolve()),
        ]
        _run(
            [
                *pytest_base,
                "-m",
                "unit or smoke",
                "--proof-report",
                str(fast_report),
            ],
            env=env,
        )
        _run(
            [
                *pytest_base,
                str((repo_root / "tests/integration/test_python_anki_backend.py").resolve()),
                "--proof-report",
                str(fixture_report),
            ],
            env=env,
        )
        _run(
            [
                *pytest_base,
                "-m",
                "backend_python_anki_backup_real",
                "--proof-report",
                str(real_report),
            ],
            env=env,
        )
        _run(
            [
                sys.executable,
                str((repo_root / "scripts/audit_quality_matrix.py").resolve()),
                "--phase",
                "phase3",
                "--matrix",
                str((repo_root / args.matrix).resolve()),
                "--tests-root",
                str((repo_root / args.tests_root).resolve()),
                "--proof-report",
                str(fast_report),
                "--proof-report",
                str(fixture_report),
                "--proof-report",
                str(real_report),
            ],
            env=env,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
