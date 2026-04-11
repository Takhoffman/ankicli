# Sync And Backups

Use this reference when the task is about auth status, sync readiness, sync execution, backup creation, or restore safety.

## Prefer

- `ankicli auth status`
- `ankicli auth login`
- `ankicli --json sync status`
- `ankicli --json backup status`
- `ankicli --json backup list`
- `ankicli --json backup create`

## Rules

1. Treat sync and backup as separate concerns.
2. Use sync status as the safe preflight before a real sync.
3. Use backup creation when rollback matters.
4. Treat restore as an explicit operator action and explain the risk before doing it.

## Safety rule

Do not present sync as a substitute for local rollback.
