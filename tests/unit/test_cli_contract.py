from __future__ import annotations

import json

import pytest


@pytest.mark.unit
def test_doctor_env_json_contract(runner) -> None:
    result = runner.invoke(args=["--json", "doctor", "env"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["backend"] == "python-anki"
    assert "anki_import_available" in payload["data"]


@pytest.mark.unit
def test_collection_info_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "collection", "info"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_not_implemented_command_is_stable_error(runner) -> None:
    result = runner.invoke(args=["--json", "search", "notes"])

    assert result.exit_code == 10
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "NOT_IMPLEMENTED_YET"

