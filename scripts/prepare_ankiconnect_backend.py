#!/usr/bin/env python3
"""Prepare env vars for live AnkiConnect validation."""

from __future__ import annotations

import argparse
import http.client
import json
import sys
from typing import Any
from urllib.parse import urlsplit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe a live AnkiConnect server and print env vars for "
            "backend_ankiconnect_real."
        ),
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8765",
        help="AnkiConnect base URL.",
    )
    return parser.parse_args()


def invoke(url: str, action: str, params: dict[str, Any] | None = None) -> Any:
    payload = json.dumps(
        {
            "action": action,
            "version": 5,
            "params": params or {},
        },
    ).encode()
    parsed = urlsplit(url)
    if parsed.scheme != "http" or not parsed.hostname:
        raise RuntimeError(f"Invalid AnkiConnect URL: {url}")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    try:
        connection = http.client.HTTPConnection(
            parsed.hostname,
            parsed.port or 80,
            timeout=5,
        )
        connection.request(
            "POST",
            path,
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        decoded = json.loads(response.read().decode())
    except OSError as exc:
        raise RuntimeError(
            f"Could not reach AnkiConnect at {url}. Start Anki Desktop with AnkiConnect enabled.",
        ) from exc
    finally:
        try:
            connection.close()
        except Exception:
            pass

    error = decoded.get("error")
    if error:
        raise RuntimeError(f"AnkiConnect action {action} failed: {error}")
    return decoded.get("result")


def choose_preferred_name(items: dict[str, Any], preferred: str) -> str | None:
    if preferred in items:
        return preferred
    if not items:
        return None
    return sorted(items.keys())[0]


def choose_preferred_model(items: dict[str, Any]) -> str | None:
    if "Basic" in items:
        return "Basic"
    if not items:
        return None
    return sorted(items.keys())[0]


def main() -> int:
    args = parse_args()
    url = args.url

    version = invoke(url, "version")
    decks = invoke(url, "deckNamesAndIds")
    try:
        models = invoke(url, "modelNamesAndIds")
    except RuntimeError:
        model_names = invoke(url, "modelNames")
        models = {name: None for name in model_names}
    note_ids = [int(note_id) for note_id in invoke(url, "findNotes", {"query": ""})]
    card_ids = [int(card_id) for card_id in invoke(url, "findCards", {"query": ""})]

    deck_name = choose_preferred_name(decks, "Default")
    model_name = choose_preferred_model(models)

    print("# Export these in your shell before running the live AnkiConnect suite.")
    print(f'export ANKICONNECT_URL="{url}"')
    if deck_name:
        print(f'export ANKICLI_REAL_DECK="{deck_name}"')
    if model_name:
        print(f'export ANKICLI_REAL_MODEL="{model_name}"')
    if note_ids:
        print(f'export ANKICLI_REAL_NOTE_ID="{note_ids[0]}"')
    if card_ids:
        print(f'export ANKICLI_REAL_CARD_ID="{card_ids[0]}"')
    print("UV_CACHE_DIR=.uv-cache uv run pytest -m backend_ankiconnect_real")
    print()
    print(f"# Detected AnkiConnect version: {version}")
    if not note_ids or not card_ids:
        print("# Create at least one note in Anki if you want note/card retrieval checks to run.")
    if deck_name is None:
        print("# No decks detected from AnkiConnect.")
    if model_name is None:
        print("# No note models detected from AnkiConnect.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
