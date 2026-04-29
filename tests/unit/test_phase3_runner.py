from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts import run_matrix_phase3


def _args(
    *,
    reports_dir: Path | None = None,
    keep_reports: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        tests_root="tests",
        matrix="ops/test-matrix.yaml",
        reports_dir=str(reports_dir) if reports_dir is not None else None,
        keep_reports=keep_reports,
    )


def test_phase3_runner_requires_real_backend_setup() -> None:
    calls: list[list[str]] = []

    result = run_matrix_phase3.run_phase3(
        _args(),
        environ={},
        runner=lambda command, *, env: calls.append(command),
    )

    assert result == 2
    assert calls == []


def test_phase3_runner_builds_labeled_proof_workflow(tmp_path: Path) -> None:
    calls: list[tuple[list[str], dict[str, str]]] = []
    reports_dir = tmp_path / "phase3-reports"

    result = run_matrix_phase3.run_phase3(
        _args(reports_dir=reports_dir),
        environ={"ANKI_SOURCE_PATH": "/tmp/anki-wheel"},
        runner=lambda command, *, env: calls.append((command, env)),
    )

    assert result == 0
    assert reports_dir.is_dir()
    assert len(calls) == 4
    assert all(env["PYTEST_PLUGINS"] == "ankicli.pytest_plugin" for _, env in calls)

    fast_command = calls[0][0]
    fixture_command = calls[1][0]
    real_command = calls[2][0]
    audit_command = calls[3][0]

    assert fast_command[:3] == [sys.executable, "-m", "pytest"]
    assert fast_command[-3:] == [
        "unit or smoke",
        "--proof-report",
        str(reports_dir / "fast.json"),
    ]
    assert fixture_command[-2:] == ["--proof-report", str(reports_dir / "fixture.json")]
    assert any("test_python_anki_backend.py" in item for item in fixture_command)
    assert real_command[-3:] == [
        "backend_python_anki_backup_real",
        "--proof-report",
        str(reports_dir / "real-python-anki.json"),
    ]
    assert audit_command[:2] == [
        sys.executable,
        str(Path(run_matrix_phase3.__file__).resolve().parent / "audit_quality_matrix.py"),
    ]
    assert "--phase" in audit_command
    assert "phase3" in audit_command
    assert audit_command.count("--proof-report") == 3
