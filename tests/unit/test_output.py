from __future__ import annotations

import json

import pytest

from ankicli.app.errors import ValidationError
from ankicli.app.output import error_envelope, render_human, render_json, success_envelope


@pytest.mark.unit
def test_success_envelope_renders_json_contract() -> None:
    envelope = success_envelope(backend="python-anki", data={"items": [1, 2, 3]}, meta={"count": 3})
    payload = json.loads(render_json(envelope))

    assert payload == {
        "ok": True,
        "backend": "python-anki",
        "data": {"items": [1, 2, 3]},
        "error": None,
        "meta": {"count": 3},
    }


@pytest.mark.unit
def test_error_envelope_renders_human_message() -> None:
    envelope = error_envelope(ValidationError("bad input"), backend="python-anki")

    assert render_human(envelope) == "VALIDATION_ERROR: bad input"

