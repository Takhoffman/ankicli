# Collection Management

Use this reference when the task is to inspect or manage collection, deck, or tag state through ankicli.

## Prefer

- `ankicli --json collection info`
- `ankicli --json deck list`
- `ankicli --json deck stats --name <deck>`
- `ankicli --json tag list`
- `ankicli --json search preview --kind notes --query 'deck:<deck>'`

## Rules

1. Inspect collection and deck state before mutating.
2. Keep operations narrowly scoped.
3. Re-run deck, tag, or collection reads after successful writes.
4. For deck create, rename, delete, or reparent operations, use `--dry-run` or `--yes` as required and explain backend support gaps before attempting the mutation.

## Maintenance workflows

- Prefer explicit preview and verification when cleaning up duplicates, tags, or deck organization.
- Explain the exact target set before applying broad collection changes.
