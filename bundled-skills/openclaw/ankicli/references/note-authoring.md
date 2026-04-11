# Note Authoring

Use this reference when the task is to create, update, retag, move, enrich, or clean up notes through ankicli.

## Prefer

- `ankicli --json search preview --kind notes --query ...`
- `ankicli --json note add ...`
- `ankicli --json note update ...`
- `ankicli --json note add-tags ...`
- `ankicli --json note remove-tags ...`
- `ankicli --json note move-deck ...`

## Rules

1. Search or inspect before mutating an existing note.
2. Use `--dry-run` for adds, updates, retagging, deletes, and moves when available.
3. Treat deletes and broad retagging as explicit operator intent only.
4. Re-read the note or preview the target set after successful writes so the operator can verify the final state.

## Media workflows

- For image generation or TTS enrichment, ankicli should remain the safe local write layer.
- Generate or prepare media first, then write the final field content or media references through ankicli.
- Deduplicate generated media instead of recreating files each run.
