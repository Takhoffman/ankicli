---
name: ankicli-collection-management
description: Teach the agent how to inspect and manage collection and deck state through ankicli.
---

Read first, dry-run deck writes when supported, and re-verify after mutation.

Prefer:

- `ankicli --json ... collection info`
- `ankicli --json ... deck list`
- `ankicli --json ... deck stats --name <deck>`
- `ankicli --json ... search preview --kind notes --query 'deck:<deck>'`

## Rules

1. Inspect collection and deck state before mutating.
2. Keep deck operations narrowly scoped.
3. Re-run deck or collection reads after successful writes.
4. For deck create, rename, delete, or reparent operations, use `--dry-run` or `--yes` as required and explain backend support gaps before attempting the mutation.
