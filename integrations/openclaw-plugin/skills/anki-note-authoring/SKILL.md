---
name: anki-note-authoring
description: Teach the agent how to add, inspect, update, and move notes safely.
---

Find the target note first, validate structure mentally, and re-read after writes.

Prefer:

- `anki_search`
- `anki_note_manage`
- `anki_deck_manage`

## Rules

1. Search or inspect before mutating an existing note.
2. Use dry-run for adds, updates, deletes, and moves when available.
3. Treat deletes and broad retagging as explicit user intent only.

