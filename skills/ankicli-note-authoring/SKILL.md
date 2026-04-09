---
name: ankicli-note-authoring
description: Teach the agent how to add, inspect, update, and retag notes safely through ankicli.
---

Find the target note first, validate structure mentally, and re-read after writes.

Prefer:

- `ankicli --json ... search preview --kind notes --query ...`
- `ankicli --json ... note add ...`
- `ankicli --json ... note update ...`
- `ankicli --json ... note add-tags ...`

## Rules

1. Search or inspect before mutating an existing note.
2. Use `--dry-run` for adds, updates, retagging, deletes, and moves when available.
3. Treat deletes and broad retagging as explicit user intent only.
4. Re-read the note or preview the target set after successful writes so the operator can verify the final state.
