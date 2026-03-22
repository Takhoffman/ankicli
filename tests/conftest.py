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

    def invoke(self, *, args: list[str]):
        return self._runner.invoke(app, args)


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


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    del config, items
