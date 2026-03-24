from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ankicli.app.quality_matrix import build_report, collect_proofs, load_matrix


def _write_matrix(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "matrix.yaml"
    path.write_text(textwrap.dedent(body).strip() + "\n")
    return path


def _write_proof_report(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "proof-report.json"
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


def test_collect_proofs_ignores_nested_non_collectable_functions(tmp_path: Path) -> None:
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_example.py").write_text(
        textwrap.dedent(
            """
            from tests.proof import proves

            def helper():
                @proves("backup.restore", "unit")
                def test_nested():
                    assert True

            @proves("doctor.env", "unit")
            def test_top_level():
                assert True
            """,
        ).strip()
        + "\n",
    )

    annotations, errors = collect_proofs(tests_root)

    assert errors == []
    assert [(item.command, item.test_name) for item in annotations] == [
        ("doctor.env", "test_top_level"),
    ]


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
    proof_report = _write_proof_report(
        tmp_path,
        f"""
        {{
          "collected_proofs": [
            {{
              "nodeid": "tests/test_example.py::test_env",
              "file": "{(tests_root / 'test_example.py').resolve()}",
              "test_name": "test_env",
              "command": "doctor.env",
              "proofs": ["unit"]
            }}
          ],
          "collected_tests": [
            {{
              "file": "{(tests_root / 'test_example.py').resolve()}",
              "test_name": "test_env"
            }}
          ],
          "passed_nodeids": ["tests/test_example.py::test_env"]
        }}
        """,
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

    report = build_report(
        matrix_path=matrix_path,
        tests_root=tests_root,
        proof_report_paths=[proof_report],
        phase_override="phase2",
    )

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
    proof_report = _write_proof_report(
        tmp_path,
        f"""
        {{
          "collected_proofs": [
            {{
              "nodeid": "tests/test_example.py::test_restore",
              "file": "{(tests_root / 'test_example.py').resolve()}",
              "test_name": "test_restore",
              "command": "backup.restore",
              "proofs": ["unit", "cli_contract", "failure"]
            }}
          ],
          "collected_tests": [
            {{
              "file": "{(tests_root / 'test_example.py').resolve()}",
              "test_name": "test_restore"
            }}
          ],
          "passed_nodeids": ["tests/test_example.py::test_restore"]
        }}
        """,
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

    report = build_report(
        matrix_path=matrix_path,
        tests_root=tests_root,
        proof_report_paths=[proof_report],
        phase_override="phase3",
    )

    assert report["ok"] is True
    assert report["waived_proof_gaps"]["backup.restore"] == ["safety"]


def test_build_report_does_not_count_unrun_collected_proofs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ankicli.app.quality_matrix.implemented_commands", lambda: ["doctor.env"])
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

            @proves("doctor.env", "unit", "cli_contract")
            def test_env():
                assert True
            """,
        ).strip()
        + "\n",
    )
    proof_report = _write_proof_report(
        tmp_path,
        f"""
        {{
          "collected_proofs": [
            {{
              "nodeid": "tests/test_example.py::test_env",
              "file": "{(tests_root / 'test_example.py').resolve()}",
              "test_name": "test_env",
              "command": "doctor.env",
              "proofs": ["unit", "cli_contract"]
            }}
          ],
          "collected_tests": [
            {{
              "file": "{(tests_root / 'test_example.py').resolve()}",
              "test_name": "test_env"
            }}
          ],
          "passed_nodeids": []
        }}
        """,
    )
    matrix_path = _write_matrix(
        tmp_path,
        """
        phase: phase2
        commands:
          - command: doctor.env
            backend_scope: both
            risk: read
            required_proofs: [unit, cli_contract]
            not_applicable_proofs: []
        """,
    )

    report = build_report(
        matrix_path=matrix_path,
        tests_root=tests_root,
        proof_report_paths=[proof_report],
    )

    assert report["ok"] is False
    assert report["missing_required_proofs"]["doctor.env"] == ["cli_contract", "unit"]


def test_build_report_flags_non_collected_proof_annotations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ankicli.app.quality_matrix.implemented_commands", lambda: ["doctor.env"])
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.summarize_backend_support",
        lambda commands: {
            "python-anki": {command: True for command in commands},
            "ankiconnect": {},
        },
    )
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    path = tests_root / "test_example.py"
    path.write_text(
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
    proof_report = _write_proof_report(
        tmp_path,
        """
        {
          "collected_proofs": [],
          "passed_nodeids": []
        }
        """,
    )
    matrix_path = _write_matrix(
        tmp_path,
        """
        phase: phase1
        commands:
          - command: doctor.env
            backend_scope: both
            risk: read
            required_proofs: [unit]
            not_applicable_proofs: []
        """,
    )

    report = build_report(
        matrix_path=matrix_path,
        tests_root=tests_root,
        proof_report_paths=[proof_report],
    )

    assert report["ok"] is False
    assert any(
        "non-collected proof annotation" in message
        for message in report["annotation_errors"]
    )


def test_build_report_allows_collected_but_unrun_annotations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ankicli.app.quality_matrix.implemented_commands", lambda: ["doctor.env"])
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.summarize_backend_support",
        lambda commands: {
            "python-anki": {command: True for command in commands},
            "ankiconnect": {},
        },
    )
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    path = tests_root / "test_example.py"
    path.write_text(
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
    proof_report = _write_proof_report(
        tmp_path,
        f"""
        {{
          "collected_proofs": [],
          "collected_tests": [
            {{
              "file": "{path.resolve()}",
              "test_name": "test_env"
            }}
          ],
          "passed_nodeids": []
        }}
        """,
    )
    matrix_path = _write_matrix(
        tmp_path,
        """
        phase: phase1
        commands:
          - command: doctor.env
            backend_scope: both
            risk: read
            required_proofs: [unit]
            not_applicable_proofs: []
        """,
    )

    report = build_report(
        matrix_path=matrix_path,
        tests_root=tests_root,
        proof_report_paths=[proof_report],
    )

    assert report["annotation_errors"] == []


def test_build_report_merges_multiple_proof_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ankicli.app.quality_matrix.implemented_commands", lambda: ["doctor.env"])
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.summarize_backend_support",
        lambda commands: {
            "python-anki": {command: True for command in commands},
            "ankiconnect": {},
        },
    )
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    path = tests_root / "test_example.py"
    path.write_text(
        textwrap.dedent(
            """
            from tests.proof import proves

            @proves("doctor.env", "unit")
            def test_unit():
                assert True

            @proves("doctor.env", "cli_contract")
            def test_contract():
                assert True
            """,
        ).strip()
        + "\n",
    )
    proof_report_one = _write_proof_report(
        tmp_path,
        f"""
        {{
          "collected_proofs": [
            {{
              "nodeid": "tests/test_example.py::test_unit",
              "file": "{path.resolve()}",
              "test_name": "test_unit",
              "command": "doctor.env",
              "proofs": ["unit"]
            }}
          ],
          "collected_tests": [
            {{
              "file": "{path.resolve()}",
              "test_name": "test_unit"
            }}
          ],
          "passed_nodeids": ["tests/test_example.py::test_unit"]
        }}
        """,
    )
    proof_report_two = tmp_path / "proof-report-two.json"
    proof_report_two.write_text(
        textwrap.dedent(
            f"""
            {{
              "collected_proofs": [
                {{
                  "nodeid": "tests/test_example.py::test_contract",
                  "file": "{path.resolve()}",
                  "test_name": "test_contract",
                  "command": "doctor.env",
                  "proofs": ["cli_contract"]
                }}
              ],
              "collected_tests": [
                {{
                  "file": "{path.resolve()}",
                  "test_name": "test_contract"
                }}
              ],
              "passed_nodeids": ["tests/test_example.py::test_contract"]
            }}
            """,
        ).strip()
        + "\n",
    )
    matrix_path = _write_matrix(
        tmp_path,
        """
        phase: phase2
        commands:
          - command: doctor.env
            backend_scope: both
            risk: read
            required_proofs: [unit, cli_contract]
            not_applicable_proofs: []
        """,
    )

    report = build_report(
        matrix_path=matrix_path,
        tests_root=tests_root,
        proof_report_paths=[proof_report_one, proof_report_two],
    )

    assert report["ok"] is True
    assert report["proofs_by_command"]["doctor.env"] == ["cli_contract", "unit"]


def test_build_report_handles_missing_proof_report_as_audit_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ankicli.app.quality_matrix.implemented_commands",
        lambda: ["doctor.backend"],
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

            @proves("doctor.backend", "unit", "cli_contract")
            def test_backend():
                assert True
            """,
        ).strip()
        + "\n",
    )
    matrix_path = _write_matrix(
        tmp_path,
        """
        phase: phase2
        commands:
          - command: doctor.backend
            backend_scope: both
            risk: read
            required_proofs: [unit, cli_contract]
            not_applicable_proofs: []
        """,
    )

    report = build_report(
        matrix_path=matrix_path,
        tests_root=tests_root,
        proof_report_paths=[tmp_path / "missing.json"],
    )

    assert report["ok"] is False
    assert any("proof report not found" in message for message in report["annotation_errors"])
