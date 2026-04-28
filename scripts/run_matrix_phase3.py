#!/usr/bin/env python3
"""Run the explicit higher-assurance matrix workflow."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
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
    parser.add_argument(
        "--reports-dir",
        help=(
            "Directory for generated proof reports. Defaults to a temporary "
            "directory that is removed after a successful run."
        ),
    )
    parser.add_argument(
        "--keep-reports",
        action="store_true",
        help="Keep the auto-created temporary proof report directory for debugging.",
    )
    return parser.parse_args()


def _run(command: list[str], *, env: dict[str, str]) -> None:
    result = subprocess.run(command, env=env, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


@contextmanager
def _proof_reports_dir(args: argparse.Namespace) -> Iterator[Path]:
    if args.reports_dir:
        reports_dir = Path(args.reports_dir).expanduser().resolve()
        reports_dir.mkdir(parents=True, exist_ok=True)
        yield reports_dir
        return
    if args.keep_reports:
        reports_dir = Path(tempfile.mkdtemp(prefix="ankicli-phase3-")).resolve()
        print(f"Keeping phase3 proof reports in {reports_dir}", file=sys.stderr)
        yield reports_dir
        return
    with tempfile.TemporaryDirectory(prefix="ankicli-phase3-") as tmpdir:
        yield Path(tmpdir).resolve()


def _repo_path(repo_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _phase3_commands(
    *,
    repo_root: Path,
    args: argparse.Namespace,
    reports_dir: Path,
) -> list[tuple[str, list[str]]]:
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
    return [
        (
            "fast unit/smoke proof tier",
            [
                *pytest_base,
                "-m",
                "unit or smoke",
                "--proof-report",
                str(fast_report),
            ],
        ),
        (
            "fixture integration proof tier",
            [
                *pytest_base,
                str((repo_root / "tests/integration/test_python_anki_backend.py").resolve()),
                "--proof-report",
                str(fixture_report),
            ],
        ),
        (
            "real python-anki proof tier",
            [
                *pytest_base,
                "-m",
                "backend_python_anki_backup_real",
                "--proof-report",
                str(real_report),
            ],
        ),
        (
            "phase3 quality matrix audit",
            [
                sys.executable,
                str((repo_root / "scripts/audit_quality_matrix.py").resolve()),
                "--phase",
                "phase3",
                "--matrix",
                str(_repo_path(repo_root, args.matrix)),
                "--tests-root",
                str(_repo_path(repo_root, args.tests_root)),
                "--proof-report",
                str(fast_report),
                "--proof-report",
                str(fixture_report),
                "--proof-report",
                str(real_report),
            ],
        ),
    ]


def _run_labeled(
    label: str,
    command: list[str],
    *,
    env: dict[str, str],
    runner: Callable[..., None] | None = None,
) -> None:
    print(f"==> {label}", flush=True)
    print(f"+ {shlex.join(command)}", flush=True)
    if runner is None:
        _run(command, env=env)
    else:
        runner(command, env=env)


def _print_missing_real_backend_setup() -> None:
    print(
        "phase3 requires ANKI_SOURCE_PATH so the real python-anki proof tier can run",
        file=sys.stderr,
    )
    print("Prepare a local wheel-backed shim with:", file=sys.stderr)
    print("  uv run python scripts/prepare_real_backend.py --reset", file=sys.stderr)
    print("Then export the ANKI_SOURCE_PATH line printed by that script.", file=sys.stderr)


def run_phase3(
    args: argparse.Namespace,
    *,
    environ: dict[str, str] | None = None,
    runner: Callable[..., None] | None = None,
) -> int:
    source_env = os.environ if environ is None else environ
    if not source_env.get("ANKI_SOURCE_PATH"):
        _print_missing_real_backend_setup()
        return 2

    repo_root = Path(__file__).resolve().parent.parent
    env = dict(source_env)
    env["PYTEST_PLUGINS"] = "ankicli.pytest_plugin"

    with _proof_reports_dir(args) as reports_dir:
        print(f"Phase3 proof reports: {reports_dir}", file=sys.stderr)
        for label, command in _phase3_commands(
            repo_root=repo_root,
            args=args,
            reports_dir=reports_dir,
        ):
            _run_labeled(label, command, env=env, runner=runner)

    return 0


def main() -> int:
    args = parse_args()
    return run_phase3(args)


if __name__ == "__main__":
    raise SystemExit(main())
