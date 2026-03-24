from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ankicli.main import app
from tests.fixtures.build_fixture import build_fixture
from tests.proof import PROOF_ATTR


class AppRunner:
    def __init__(self, app_runner: CliRunner) -> None:
        self._runner = app_runner

    def invoke(self, *, args: list[str], input: str | None = None):
        result = self._runner.invoke(app, args, input=input)
        if "blocked main thread" in result.stdout and any(
            flag in args for flag in ("--json", "--ndjson")
        ):
            for marker in ("{", "["):
                index = result.stdout.find(marker)
                if index != -1:
                    result.stdout_bytes = result.stdout[index:].encode()
                    break
        return result


@pytest.fixture()
def runner() -> AppRunner:
    return AppRunner(CliRunner())


@pytest.fixture()
def fixture_collection_path() -> Path:
    value = os.environ.get("ANKICLI_TEST_COLLECTION")
    if value:
        return Path(value)
    return build_fixture()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--proof-report",
        action="store",
        default=None,
        help="Write collected/passed proof metadata to this JSON file.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "backend_python_anki: tests for the python-anki backend")
    config.addinivalue_line(
        "markers",
        "backend_python_anki_backup_real: opt-in disposable real backup/profile checks",
    )
    config._ankicli_proof_rows = []  # type: ignore[attr-defined]
    config._ankicli_passed_nodeids = set()  # type: ignore[attr-defined]
    config._ankicli_collected_tests = set()  # type: ignore[attr-defined]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    del config, items


def _proof_rows_for_items(items: list[pytest.Item]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in items:
        obj = getattr(item, "obj", None)
        proof_specs = getattr(obj, PROOF_ATTR, ())
        if not proof_specs:
            continue
        test_name = getattr(item, "originalname", None) or item.name.split("[", 1)[0]
        for command, proofs in proof_specs:
            rows.append(
                {
                    "nodeid": item.nodeid,
                    "file": str(Path(str(item.path))),
                    "test_name": test_name,
                    "command": command,
                    "proofs": list(proofs),
                },
            )
    return rows


def _collected_test_refs(items: list[pytest.Item]) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    for item in items:
        test_name = getattr(item, "originalname", None) or item.name.split("[", 1)[0]
        refs.add((str(Path(str(item.path)).resolve()), test_name))
    return refs


def pytest_collection_finish(session: pytest.Session) -> None:
    rows = _proof_rows_for_items(session.items)
    session.config._ankicli_proof_rows = rows  # type: ignore[attr-defined]
    session.config._ankicli_collected_tests.update(_collected_test_refs(session.items))  # type: ignore[attr-defined]


def pytest_deselected(items: list[pytest.Item]) -> None:
    if not items:
        return
    config = items[0].config
    config._ankicli_proof_rows.extend(_proof_rows_for_items(items))  # type: ignore[attr-defined]
    config._ankicli_collected_tests.update(_collected_test_refs(items))  # type: ignore[attr-defined]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.outcome == "passed":
        item.config._ankicli_passed_nodeids.add(item.nodeid)  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del exitstatus
    report_path = session.config.getoption("--proof-report")
    if not report_path:
        return
    payload = {
        "collected_proofs": session.config._ankicli_proof_rows,  # type: ignore[attr-defined]
        "collected_tests": [  # type: ignore[attr-defined]
            {"file": file, "test_name": test_name}
            for file, test_name in sorted(session.config._ankicli_collected_tests)
        ],
        "passed_nodeids": sorted(session.config._ankicli_passed_nodeids),  # type: ignore[attr-defined]
    }
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
