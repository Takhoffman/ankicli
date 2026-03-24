from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ankicli.main import app
from tests.fixtures.build_fixture import build_fixture


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


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "backend_python_anki: tests for the python-anki backend")
    config.addinivalue_line(
        "markers",
        "backend_python_anki_backup_real: opt-in disposable real backup/profile checks",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    del config, items
