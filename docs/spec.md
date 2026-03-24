# AnkiCLI Spec

## Summary

Build `ankicli` as a local-first, automation-grade Anki collection management CLI with a stable
service layer, JSON-first responses, and a backend seam present from day one.

## V1 Focus

- Open a collection
- Inspect decks, models, notes, and cards
- Inspect tags
 - Inspect media files and basic media health
- Search notes and cards
- Add, update, and delete notes
- Add and remove note tags
- Suspend and unsuspend cards
- Emit structured JSON for all important commands

## Backend Policy

- Primary backend: `python-anki`
- Secondary backend: `ankiconnect`
- No raw SQLite write backend in V1

## Test Policy

- Unit tests for fast contract and logic coverage
- Smoke tests for the default local and CI loop
- Fixture-integration tests against a repo-owned deterministic contract fixture by default
- E2E tests through the editable installed CLI entrypoint
- Distribution tests through built artifacts installed into an isolated environment
- Real Python-Anki integration is an opt-in local tier for validating the implemented command slices
  against a true collection
- Live AnkiConnect integration is a separate opt-in local tier for validating the live-desktop
  backend against a running AnkiConnect server

## Development Policy

- `uv.lock` is committed and treated as part of the source of truth for reproducible local and CI
  runs.
- The default integration fixture is generated from source, not manually curated local state.
- The default fixture is a deterministic contract fixture, not yet a true Anki collection fixture.
- Command placeholders are acceptable only when covered by explicit contract tests and clearly
  documented as incomplete.
- `uv` remains the workflow frontend; `hatchling` remains the configured build backend.
- Real `python-anki` development uses a sibling local source checkout configured through
  `ANKI_SOURCE_PATH`.
- Default pinned upstream reference for local setup: Anki tag `25.09.2`.
- Raw source checkout support is currently sufficient for import-path verification, but real
  `Collection`-level validation may require built/generated upstream Python artifacts or an
  installed official `anki` wheel.

## Local Real-Backend Setup

- `ANKI_SOURCE_PATH=/absolute/path/to/anki`
- `ANKICLI_REAL_COLLECTION=/absolute/path/to/collection.anki2` for opt-in true collection checks
- Runtime resolution order under that path: `pylib/`, then `python/`, then repo root
- Default repo workflow does not require Anki source
- `backend_python_anki_real` is the only test tier that depends on this setup today
- Distinguish two local modes:
  - import-path setup check via raw source checkout
  - true collection validation via wheel-backed or built-artifact-backed `anki`

## Local Live AnkiConnect Setup

- Run Anki Desktop locally with the AnkiConnect add-on enabled
- `ANKICONNECT_URL` defaults to `http://127.0.0.1:8765`
- Reuse `ANKICLI_REAL_DECK`, `ANKICLI_REAL_MODEL`, `ANKICLI_REAL_NOTE_ID`, and
  `ANKICLI_REAL_CARD_ID` for opt-in live checks
- `backend_ankiconnect_real` is the only test tier that depends on this setup
- `scripts/prepare_ankiconnect_backend.py` is the canonical helper for discovering and printing
  the live-test env vars

## Current Implemented Surface

- Collection and backend:
  - `--version`
  - `doctor env|backend|capabilities|collection|safety`
  - `backend list|info|capabilities|test-connection`
  - `collection info|stats|validate|lock-status`
  - `deck list|get|stats|create|rename|delete|reparent`
  - `model list|get|fields|templates|validate-note`
- Search:
  - `search notes --query ...`
  - `search cards --query ...`
  - `search count --kind notes|cards --query ...`
  - `search preview --kind notes|cards --query ... [--limit ...] [--offset ...]`
- Import/export:
  - `export notes --query ... [--limit ...] [--offset ...] [--ndjson]`
  - `export cards --query ... [--limit ...] [--offset ...] [--ndjson]`
  - `import notes (--input ... | --stdin-json) [--dry-run] [--yes]`
  - `import patch (--input ... | --stdin-json) [--dry-run] [--yes]`
- Tags:
  - `tag list`
  - `tag apply --id ... --tag ... [--tag ...] [--dry-run] [--yes]`
  - `tag remove --id ... --tag ... [--tag ...] [--dry-run] [--yes]`
  - `tag rename --name ... --to ... [--dry-run] [--yes]`
  - `tag delete --tag ... [--tag ...] [--dry-run] [--yes]`
  - `tag reparent --tag ... [--tag ...] --to-parent ... [--dry-run] [--yes]`
- Media:
  - `media list`
  - `media check`
  - `media attach --source ... [--name ...] [--dry-run] [--yes]`
  - `media orphaned`
  - `media resolve-path --name ...`
- Notes:
  - `note get --id ...`
  - `note fields --id ...`
  - `note add --deck ... --model ... --field Name=Value [--tag ...] [--dry-run]`
  - `note update --id ... --field Name=Value [--dry-run]`
  - `note move-deck --id ... --deck ... [--dry-run] [--yes]`
  - `note add-tags --id ... --tag ... [--tag ...] [--dry-run] [--yes]`
  - `note remove-tags --id ... --tag ... [--tag ...] [--dry-run] [--yes]`
  - `note delete --id ... [--dry-run] [--yes]`
- Cards:
  - `card get --id ...`
  - `card suspend --id ... [--dry-run] [--yes]`
  - `card unsuspend --id ... [--dry-run] [--yes]`

## Backend Support Matrix

- `python-anki`
  - supports the full currently implemented surface
  - remains the primary local/offline backend
- `ankiconnect`
  - supports:
    - `doctor backend|capabilities`
    - `backend test-connection`
    - `collection info`
    - `collection stats`
    - `deck list|get|stats`
    - `model list|get|fields|templates|validate-note`
    - `tag list|apply|remove`
    - `search notes|cards|count|preview`
    - `export notes|cards`
    - `import notes`
    - `import patch`
    - `note get|fields|add|update|move-deck|add-tags|remove-tags`
    - `card get|suspend|unsuspend`
  - does not support yet:
    - `doctor collection|safety`
    - `collection validate|lock-status`
    - `note delete`
    - `deck create|rename|delete|reparent`
    - `tag rename|delete|reparent`
    - `media list|check|attach|orphaned|resolve-path`
  - expects a running Anki desktop instance with AnkiConnect reachable at
    `http://127.0.0.1:8765` by default
  - does not require `--collection`
- `backend capabilities` exposes an operation-level `supported_operations` map for the implemented
  command surface
- unsupported backend-specific operations should fail with
  `BACKEND_OPERATION_UNSUPPORTED`, not generic placeholder errors

## Current Safety Rules

- Machine-readable mode is `--json` and should be treated as the default automation surface.
- `tag apply`, `tag remove`, `tag rename`, `tag delete`, `tag reparent`, `media attach`,
  `import notes`, `import patch`, `note delete`, `note add-tags`, `note remove-tags`,
  `card suspend`, and `card unsuspend` require `--yes` for real mutation.
- `--dry-run` is available on the implemented write-capable commands.
- Bulk query-based mutation is intentionally deferred until the single-record mutation model is
  harder to misuse.

## Output Contract

Success:

```json
{"ok": true, "backend": "python-anki", "data": {}, "meta": {}}
```

Failure:

```json
{"ok": false, "backend": "python-anki", "error": {"code": "EXAMPLE", "message": "..." }}
```
