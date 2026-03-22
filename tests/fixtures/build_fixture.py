from __future__ import annotations

import json
import sqlite3
from pathlib import Path

FIXTURE_ROOT = Path(__file__).resolve().parent / "generated" / "minimal"
COLLECTION_PATH = FIXTURE_ROOT / "collection.anki2"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"


def build_fixture() -> Path:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)

    if COLLECTION_PATH.exists():
        COLLECTION_PATH.unlink()

    connection = sqlite3.connect(COLLECTION_PATH)
    try:
        connection.execute("create table metadata (key text primary key, value text not null)")
        rows = [
            ("fixture_name", "minimal"),
            ("schema_version", "1"),
            ("note_count", "0"),
            ("card_count", "0"),
        ]
        connection.executemany("insert into metadata(key, value) values(?, ?)", rows)
        connection.commit()
    finally:
        connection.close()

    manifest = {
        "fixture_name": "minimal",
        "collection_path": str(COLLECTION_PATH),
        "schema_version": 1,
        "note_count": 0,
        "card_count": 0,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    return COLLECTION_PATH
