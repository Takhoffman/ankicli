from __future__ import annotations

import json
import sqlite3

import pytest


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_repo_fixture_is_built_and_deterministic(fixture_collection_path) -> None:
    assert fixture_collection_path.exists()

    connection = sqlite3.connect(fixture_collection_path)
    try:
        row = connection.execute(
            "select value from metadata where key = 'fixture_name'",
        ).fetchone()
    finally:
        connection.close()

    assert row == ("minimal",)


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
def test_collection_info_integration_smoke(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "collection", "info"],
    )

    payload = json.loads(result.stdout)
    assert payload["backend"] == "python-anki"
    if payload["ok"]:
        assert payload["data"]["collection_path"] == str(fixture_collection_path)
    else:
        assert payload["error"]["code"] == "BACKEND_UNAVAILABLE"


@pytest.mark.fixture_integration
@pytest.mark.backend_python_anki
@pytest.mark.xfail(reason="search notes is not implemented yet")
def test_search_notes_integration_contract(runner, fixture_collection_path) -> None:
    result = runner.invoke(
        args=["--json", "--collection", str(fixture_collection_path), "search", "notes"],
    )

    assert result.exit_code == 0
