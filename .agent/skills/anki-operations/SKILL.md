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
4. Preserve structured `ankicli` errors. Do not reinterpret codes into vague summaries.
5. Use the narrowest command or tool that solves the task. Do not jump straight to bulk operations.
6. Respect backend limits. If the active backend reports `BACKEND_OPERATION_UNSUPPORTED`, switch backend or explain the limit.

## Transport Choice

- In OpenClaw, prefer the repo-owned plugin tools first.
- Outside OpenClaw, prefer `ankicli --json`.
- Treat both as the same logical surface. The CLI is the source of truth; the plugin is only an adapter.

## Workflow Playbooks

### Inspect And Diagnose

Use this before any meaningful change:
- identify backend and capabilities
- inspect collection info or stats
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
