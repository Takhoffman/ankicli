# Anki Operations Skill Spec

This document defines the intended workflow layer above `ankicli` and the
OpenClaw plugin. It is written as a skill-style operating manual, not a command
reference.

`ankicli` remains the source of truth for Anki behavior. The OpenClaw plugin is
just a transport adapter over `ankicli --json`. This skill layer should guide
how an agent uses those surfaces safely and effectively.

## Purpose

Use this skill when an agent needs to inspect, diagnose, or mutate an Anki
collection through either:

- direct `ankicli --json` invocation
- native OpenClaw tools backed by the `ankicli` plugin

The skill should optimize for:

- read-first workflows
- dry-run-first mutations
- narrow, explicit operations
- backend-aware troubleshooting
- post-mutation verification

It should not duplicate the full CLI or plugin reference.

## Core Rules

1. Read before write.
- Inspect collection, search, and fetch representative records before mutating.

2. Prefer the narrowest operation.
- Use the most specific note/card/deck/tag command or tool that solves the task.

3. Prefer dry-run first.
- For write-capable operations that support `dry_run`, use it before real
  mutation unless the user explicitly wants immediate execution.

4. Treat sync and backup as different safety tools.
- `sync` keeps local and remote state aligned.
- `backup` is for rollback.
- Do not present sync as a substitute for a restorable snapshot.

5. Preserve structured errors.
- Treat `ankicli` error codes as authoritative. Do not invent alternate error
  meanings.

6. Re-verify after writes.
- After any mutation, run a read operation to confirm the expected state.

7. Respect backend limits.
- If the active backend reports unsupported behavior, switch strategy or explain
  the limitation instead of guessing.

## Transport Guidance

When both transports are available, prefer:

1. OpenClaw native tools inside OpenClaw sessions.
2. Direct `ankicli --json` outside OpenClaw.

Treat both transports as the same logical capability surface. The skill should
describe workflows and safety policy, not transport-specific implementation
details.

## Workflow Playbooks

### 1. Inspect And Diagnose

Use when the goal is understanding current state or confirming environment
health.

Suggested sequence:

1. Identify backend and capabilities.
2. Inspect collection summary.
3. Inspect relevant deck/model if the task is scoped.
4. Search notes/cards.
5. Fetch one or more representative records.

Good targets:

- `doctor backend`
- `backend capabilities`
- `profile default`
- `profile resolve`
- `auth status`
- `backup status`
- `collection info`
- `sync status`
- `search count`
- `search preview`
- `note get`
- `card get`

### 2. Safe Note Mutation

Use when adding or updating notes.

Suggested sequence:

1. Confirm deck/model existence.
2. Validate search results or inspect a sample note when updating.
3. Run dry-run if supported.
4. Apply the write.
5. Re-fetch the note or re-run search to confirm.

Good targets:

- `deck get`
- `model get`
- `model validate-note`
- `note add`
- `note update`
- `note get`

### 3. Safe Card State Changes

Use when suspending or unsuspending cards.

Suggested sequence:

1. Search or inspect the card first.
2. Run dry-run.
3. Apply the confirmed mutation.
4. Re-fetch the card.

Good targets:

- `search cards`
- `card get`
- `card suspend`
- `card unsuspend`

### 4. Tag Workflows

Use when applying or removing tags from notes.

Suggested sequence:

1. Search and inspect the note.
2. Check current tags.
3. Run dry-run where supported.
4. Apply or remove tags.
5. Re-fetch the note to confirm tags.

Good targets:

- `tag list`
- `note get`
- `tag apply`
- `tag remove`
- `note add-tags`
- `note remove-tags`

### 5. Bulk-Safe Change Workflow

Use when the user wants broad edits across many notes/cards.

Suggested sequence:

1. Count the target set.
2. Preview a small sample.
3. Confirm the search is correct.
4. Use the narrowest bulk-friendly path available.
5. Re-query after the change.

Good targets:

- `search count`
- `search preview`
- `backup create`
- `export notes`
- `import patch`

## Error Handling Guidance

Interpret these codes consistently:

- `COLLECTION_REQUIRED`
  - collection path is missing; ask for it or configure it
- `COLLECTION_NOT_FOUND`
  - path is wrong or unavailable; stop and fix pathing
- `COLLECTION_OPEN_FAILED`
  - collection exists but backend cannot open it; inspect backend/fixture reality
- `BACKEND_UNAVAILABLE`
  - runtime/backend dependency is missing; fix env or switch backend
- `BACKEND_OPERATION_UNSUPPORTED`
  - current backend cannot do the requested operation; choose another backend or
    another workflow
- `NOTE_NOT_FOUND`, `CARD_NOT_FOUND`, `DECK_NOT_FOUND`, `MODEL_NOT_FOUND`
  - stop and re-search or correct the identifier/name
- `UNSAFE_OPERATION`
  - rerun only with explicit user intent and the required confirmation semantics
- `VALIDATION_ERROR`
  - fix the payload, flags, or field names before retrying
- `AUTH_REQUIRED`
  - log in first or confirm stored sync credentials exist
- `AUTH_INVALID`
  - stored credentials are stale or bad; log in again
- `AUTH_STORAGE_UNAVAILABLE`
  - OS secret storage is unavailable; stop and fix the host environment
- `BACKUP_RESTORE_UNSAFE`
  - restore is blocked by lock/open-state or context mismatch; do not force it
- `PROFILE_NOT_FOUND`, `PROFILE_RESOLUTION_FAILED`
  - local profile targeting is wrong or the Anki data root is unavailable
- `SYNC_CONFLICT`
  - explicit pull/push choice is required; do not guess
- `SYNC_IN_PROGRESS`
  - wait or resolve the existing sync instead of retrying blindly
- `SYNC_FAILED`
  - inspect backend details and avoid repeating writes until sync state is clear

## Backend Strategy

Prefer `python-anki` when:

- local collection semantics matter
- richer local operations are needed
- file or collection diagnostics are relevant
- profile resolution or backup/restore is required
- standalone sync/auth is required

Prefer `ankiconnect` when:

- Anki Desktop is already running
- the required operation is supported there
- live desktop integration is more convenient than local Python backend setup

If a task can be solved on either backend, choose the backend already configured
and working unless there is a clear reason to switch.

## Anti-Patterns

Do not:

- mutate records before inspecting any sample
- skip dry-run on supported mutations without a reason
- treat backend-specific extras as portable contract fields
- infer success from process exit alone when structured JSON exists
- duplicate the CLI reference inside the skill
- reimplement Anki business logic in the skill layer

## Relationship To Other Docs

- [openclaw-plugin.md](/Users/thoffman/ankicli/docs/openclaw-plugin.md)
  - stable transport and contract surface
- [spec.md](/Users/thoffman/ankicli/docs/spec.md)
  - product and CLI scope

This document is the workflow layer above those references.
