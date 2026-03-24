from __future__ import annotations

import json

import pytest


@pytest.mark.smoke
def test_cli_help_smoke(runner) -> None:
    result = runner.invoke(args=["--help"])

    assert result.exit_code == 0
    assert "doctor" in result.stdout
    assert "collection" in result.stdout


@pytest.mark.smoke
def test_backend_list_smoke(runner) -> None:
    result = runner.invoke(args=["--json", "backend", "list"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["items"] == ["python-anki", "ankiconnect"]


@pytest.mark.smoke
def test_backend_info_smoke(runner) -> None:
    result = runner.invoke(args=["--json", "backend", "info"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["name"] == "python-anki"
    assert "capabilities" in payload["data"]


@pytest.mark.smoke
def test_ankiconnect_backend_info_smoke(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "info"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["name"] == "ankiconnect"
    assert "capabilities" in payload["data"]
