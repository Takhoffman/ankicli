---
name: ankicli
description: Use when an agent needs to inspect, study, create, modify, organize, sync, or troubleshoot an Anki collection through ankicli. Covers setup, study workflows, note authoring, collection and deck management, diagnostics, sync and backups, and goal-driven learning plans.
---

Use ankicli as the local source of truth for Anki operations.

## Core operating rules

1. Confirm runtime, backend, and target readiness first.
2. Prefer `--json` in agent-driven workflows.
3. Prefer read, search, and preview commands before mutation.
4. Use `--dry-run` where supported before real writes.
5. Treat structured ankicli error codes and capability flags as authoritative.
6. Distinguish sync from backup.
7. Prefer saved workspace config for routine use.

## Baseline checks

- `ankicli --json doctor env`
- `ankicli --json doctor backend`
- `ankicli --json profile list`
- `ankicli --json workspace show`

## Read the right reference

- Read `references/setup.md` for install verification, `ankicli configure`, workspaces, auth, and skill installation.
- Read `references/study.md` for tutor-style study sessions, reveal flow, grading, and summaries.
- Read `references/note-authoring.md` for note creation, update, tagging, moving, and media-enrichment workflows.
- Read `references/collection-management.md` for collection inspection, decks, tags, and maintenance-style operations.
- Read `references/diagnostics.md` for runtime, profile, backend, capability, and collection troubleshooting.
- Read `references/sync-and-backups.md` for auth status, sync preflight, backup creation, and restore safety.
- Read `references/learning-plans.md` for travel, anime immersion, exam prep, and time-budgeted study-planning workflows.

## Default behavior

1. Verify environment and target before attempting a task.
2. Select the narrowest reference that matches the request.
3. Re-read the relevant object or preview set after successful writes so the operator can verify the final state.
