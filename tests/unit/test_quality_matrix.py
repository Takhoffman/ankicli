from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ankicli.app.quality_matrix import build_report, collect_proofs, load_matrix


def _write_matrix(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "matrix.yaml"
    path.write_text(textwrap.dedent(body).strip() + "\n")
    return path


def test_load_matrix_parses_valid_rows(tmp_path: Path) -> None:
    path = _write_matrix(
        tmp_path,
        """
        phase: phase1
        commands:
          - command: backup.restore
            backend_scope: python-anki
            risk: restore
            required_proofs: [unit, cli_contract, failure, safety]
            not_applicable_proofs: [real_ankiconnect]
        """,
    )

    phase, entries = load_matrix(path)

    assert phase == "phase1"
    assert entries["backup.restore"].risk == "restore"
    assert entries["backup.restore"].required_proofs == (
        "unit",
        "cli_contract",
        "failure",
        "safety",
    )


def test_load_matrix_rejects_invalid_proof_types(tmp_path: Path) -> None:
    path = _write_matrix(
        tmp_path,
        """
        phase: phase1
        commands:
          - command: backup.restore
            backend_scope: python-anki
            risk: restore
            required_proofs: [made_up]
            not_applicable_proofs: []
        """,
    )

    with pytest.raises(ValueError, match="unknown proof types"):
        load_matrix(path)


def test_collect_proofs_parses_ast_annotations(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_example.py").write_text(
        textwrap.dedent(
            """
            from tests.proof import proves

            @proves("backup.restore", "unit", "failure", "safety")
            def test_restore():
                assert True
            """,
        ).strip()
        + "\n",
    )

    annotations, errors = collect_proofs(tests_root)

    assert errors == []
    assert annotations[0].command == "backup.restore"
    assert annotations[0].proofs == ("unit", "failure", "safety")


def test_collect_proofs_reports_invalid_annotation(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_example.py").write_text(
        textwrap.dedent(
            """
            from tests.proof import proves

            @proves("backup.restore", "not_real")
            def test_restore():
                assert True
            """,
        ).strip()
        + "\n",
    )

    annotations, errors = collect_proofs(tests_root)

    assert annotations == []
    assert errors


def test_build_report_flags_missing_matrix_rows_and_stale_annotations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.implemented_commands",
        lambda: ["doctor.env"],
    )
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.summarize_backend_support",
        lambda commands: {
            "python-anki": {command: True for command in commands},
            "ankiconnect": {},
        },
    )
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_example.py").write_text(
        textwrap.dedent(
            """
            from tests.proof import proves

            @proves("stale.command", "unit")
            def test_stale():
                assert True
            """,
        ).strip()
        + "\n",
    )
    matrix_path = _write_matrix(
        tmp_path,
        """
        phase: phase1
        commands:
          - command: stale.row
            backend_scope: python-anki
            risk: read
            required_proofs: [unit]
            not_applicable_proofs: []
        """,
    )

    report = build_report(matrix_path=matrix_path, tests_root=tests_root)

    assert "stale.row" in report["stale_matrix_rows"]
    assert report["stale_proof_annotations"][0]["command"] == "stale.command"


def test_build_report_honors_phase2_core_proof_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.implemented_commands",
        lambda: ["doctor.env"],
    )
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.summarize_backend_support",
        lambda commands: {
            "python-anki": {command: True for command in commands},
            "ankiconnect": {},
        },
    )
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_example.py").write_text(
        textwrap.dedent(
            """
            from tests.proof import proves

            @proves("doctor.env", "unit")
            def test_env():
                assert True
            """,
        ).strip()
        + "\n",
    )
    matrix_path = _write_matrix(
        tmp_path,
        """
        phase: phase1
        commands:
          - command: doctor.env
            backend_scope: both
            risk: read
            required_proofs: [unit, cli_contract]
            not_applicable_proofs: []
        """,
    )

    report = build_report(matrix_path=matrix_path, tests_root=tests_root, phase_override="phase2")

    assert report["ok"] is False
    assert report["missing_required_proofs"]["doctor.env"] == ["cli_contract"]


def test_build_report_honors_waived_proofs_in_phase3(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.implemented_commands",
        lambda: ["backup.restore"],
    )
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.summarize_backend_support",
        lambda commands: {
            "python-anki": {command: True for command in commands},
            "ankiconnect": {},
        },
    )
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_example.py").write_text(
        textwrap.dedent(
            """
            from tests.proof import proves

            @proves("backup.restore", "unit", "cli_contract", "failure")
            def test_restore():
                assert True
            """,
        ).strip()
        + "\n",
    )
    matrix_path = _write_matrix(
        tmp_path,
        """
        phase: phase1
        commands:
          - command: backup.restore
            backend_scope: python-anki
            risk: restore
            required_proofs: [unit, cli_contract, failure, safety]
            not_applicable_proofs: []
            waived_proofs: [safety]
            waiver_reason: temporary
            waiver_phase: phase1
        """,
    )

    report = build_report(matrix_path=matrix_path, tests_root=tests_root, phase_override="phase3")

    assert report["ok"] is True
    assert report["waived_proof_gaps"]["backup.restore"] == ["safety"]
