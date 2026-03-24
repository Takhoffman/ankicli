---
name: anki-operations
description: Use when working with Anki collections through ankicli or the repo-owned OpenClaw plugin, especially for safe inspection, backend-aware troubleshooting, dry-run-first mutation workflows, or multi-step note/card/tag/deck/media operations.
---

# Anki Operations

This skill is the workflow layer above `ankicli` and the repo-owned OpenClaw plugin. Use it to choose the right Anki operation, sequence read and write steps safely, and react to backend-specific limits without inventing new behavior.

## Core Rules

1. Read before write. Inspect the collection, search narrowly, and fetch a representative note or card before changing anything.
2. Prefer `--dry-run` first whenever the command supports it, unless the user clearly wants immediate execution.
3. Re-verify after mutations with a follow-up read, search, or stats command.
4. Treat sync and backup as different tools. Sync keeps local and remote state aligned; backup is the rollback path.
5. Preserve structured `ankicli` errors. Do not reinterpret codes into vague summaries.
6. Use the narrowest command or tool that solves the task. Do not jump straight to bulk operations.
7. Respect backend limits. If the active backend reports `BACKEND_OPERATION_UNSUPPORTED`, switch backend or explain the limit.

## Transport Choice

- In OpenClaw, prefer the repo-owned plugin tools first.
- Outside OpenClaw, prefer `ankicli --json`.
- Treat both as the same logical surface. The CLI is the source of truth; the plugin is only an adapter.

## Workflow Playbooks

### Inspect And Diagnose

Use this before any meaningful change:
- identify backend and capabilities
- resolve the profile when local profile targeting matters
- inspect auth status if sync or remote state matters
- inspect backup status when rollback matters
- inspect collection info or stats
- use `sync status` before assuming local and remote state match
- list decks or models if the target is not known
- use `search count` or `search preview` before wide changes
- fetch the exact note or card before mutating it

Good command/tool progression:
- collection or backend info
- search
- get
- mutate
- verify

### Safe Note Mutation

Use for add, update, patch, tag changes, and note deck moves:
- resolve the target model, deck, note id, or search query first
- if the operation supports dry-run, run it first
- perform the real mutation only after the target is clear
- read the note again afterward to confirm fields, tags, or deck placement

### Safe Card State Changes

Use for suspend and unsuspend:
- fetch the card first
- confirm the deck and note context are the intended target
- dry-run first when available
- re-read the card after the change

### Bulk-Safe Changes

Use for import patch, exports, tag cleanup, and larger migrations:
- count first
- preview a small sample
- export or dry-run before committing writes
- apply the narrowest bulk action possible
- re-run count or preview after the change

## Backend Strategy

Default preference:
- use `python-anki` when local collection semantics matter
- use `ankiconnect` when live desktop integration is the goal

Switch to `python-anki` when you need:
- local collection validation or lock checks
- local profile resolution or backup/restore
- standalone sync/auth
- deck lifecycle writes
- tag lifecycle writes
- media operations
- any operation not supported by `ankiconnect`

Stay on `ankiconnect` when you need:
- live desktop-backed reads
- supported note/card operations through the running app

## Error Handling

- `COLLECTION_REQUIRED`: provide or ask for a collection path when using local collection flows.
- `BACKEND_UNAVAILABLE`: check installation, running services, or backend selection.
- `BACKEND_OPERATION_UNSUPPORTED`: switch backend or choose a narrower workflow.
- `NOTE_NOT_FOUND`, `CARD_NOT_FOUND`, `DECK_NOT_FOUND`, `MODEL_NOT_FOUND`, `TAG_NOT_FOUND`: stop and re-search instead of guessing.
- `UNSAFE_OPERATION`: retry only when the user clearly intends the real write and the command supports confirmation flags.
- `COLLECTION_OPEN_FAILED`: treat it as a real backend or fixture limitation, not a harmless warning.
- `AUTH_REQUIRED`: log in first or confirm stored sync credentials exist.
- `AUTH_INVALID`: stored sync credentials are stale or bad; log in again.
- `AUTH_STORAGE_UNAVAILABLE`: stop and fix the host secret-storage environment.
- `PROFILE_NOT_FOUND` and `PROFILE_RESOLUTION_FAILED`: the local Anki profile selection is wrong or unavailable.
- `BACKUP_RESTORE_UNSAFE`: do not force restore through an unsafe lock/open-state.
- `SYNC_CONFLICT`: explicit `sync pull` or `sync push` choice is required; do not guess.
- `SYNC_IN_PROGRESS` and `SYNC_FAILED`: stop, inspect backend details, and do not stack writes on top of unstable sync state.

## References

Read these only when you need contract detail:
- Plugin-facing contract: [`docs/openclaw-plugin.md`](/Users/thoffman/ankicli/docs/openclaw-plugin.md)
- Full CLI surface: [`docs/spec.md`](/Users/thoffman/ankicli/docs/spec.md)
- Longer workflow version: [`docs/anki-operations-skill.md`](/Users/thoffman/ankicli/docs/anki-operations-skill.md)

## Anti-Patterns

- Do not mutate from a broad search result without fetching the exact target.
- Do not skip dry-run on risky commands when dry-run exists and the user did not ask to skip it.
- Do not hide backend-specific unsupported behavior.
- Do not duplicate the CLI or plugin reference inside this skill.
