"""Rendering helpers for CLI responses."""

from __future__ import annotations

import json
from typing import Any

from ankicli.app.errors import AnkiCliError
from ankicli.app.models import Envelope, ErrorBody


def success_envelope(
    *,
    backend: str,
    data: dict[str, Any],
    meta: dict[str, Any] | None = None,
) -> Envelope:
    return Envelope(ok=True, backend=backend, data=data, meta=meta or {})


def error_envelope(error: AnkiCliError, *, backend: str) -> Envelope:
    return Envelope(
        ok=False,
        backend=backend,
        error=ErrorBody(code=error.code, message=error.message, details=error.details),
        meta={},
    )


def render_json(envelope: Envelope) -> str:
    return envelope.model_dump_json(indent=2)


def render_ndjson(items: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(item, sort_keys=True) for item in items)


def render_human(envelope: Envelope) -> str:
    if envelope.ok:
        if not envelope.data:
            return "ok"
        return json.dumps(envelope.data, indent=2, sort_keys=True)
    assert envelope.error is not None
    return f"{envelope.error.code}: {envelope.error.message}"
