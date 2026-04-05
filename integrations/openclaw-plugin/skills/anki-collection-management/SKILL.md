---
name: anki-collection-management
description: Teach the agent how to inspect and manage collection and deck state.
---

Read first, dry-run deck writes when supported, and re-verify after mutation.

Prefer:

- `anki_collection_status`
- `anki_search`
- `anki_deck_manage`

## Rules

1. Inspect collection and deck state before mutating.
2. Keep deck operations narrowly scoped.
3. Re-run deck or collection reads after successful writes.
4. If a backend does not support a deck action, say so before attempting the mutation and recommend switching to a backend that supports deck writes.

