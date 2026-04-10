# AnkiCLI Spec

## Summary

Build `ankicli` as a local-first, automation-grade Anki collection management CLI with a stable
service layer, JSON-first responses, and a backend seam present from day one.

## V1 Focus

- Open a collection
- Inspect decks, models, notes, and cards
- Inspect tags
- Inspect media files and basic media health
- Resolve local Anki profiles into collection/media/backup paths
- Create and inspect local backups
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
- Matrix-driven proof auditing is the primary command-adequacy gate
- Smoke tests for the default local and CI loop
- Fixture-integration tests against a repo-owned deterministic contract fixture by default
- E2E tests through the editable installed CLI entrypoint
- Distribution tests through built artifacts installed into an isolated environment
- Real Python-Anki integration is an opt-in local tier for validating the implemented command slices
  against a true collection
- Disposable Python-Anki backup integration is a separate opt-in local tier that creates a throwaway
  Anki2 profile root under `/tmp` and validates backup/profile flows without touching a personal
  profile
- Live AnkiConnect integration is a separate opt-in local tier for validating the live-desktop
  backend against a running AnkiConnect server

## Proof Matrix Policy

- `ops/test-matrix.yaml` is the source of truth for required proof by command
- `scripts/audit_quality_matrix.py` is the primary unified auditor
- test proof is attached explicitly with `@proves("command.id", "proof_type", ...)`
- proof satisfaction comes from pytest-collected and pytest-passed tests via the proof report, not from source annotations alone
- the auditor can merge multiple proof reports from separate pytest runs
- the auditor should summarize proof contribution per report source for aggregated runs
- the auditor should expose a machine-readable `phase3_readiness` summary for blocked proof categories
- the readiness summary should include an execution-plan mapping from blocking proof category to concrete runner/tier guidance where known
- backend capability reporting remains a sibling signal, not a required proof type
- raw line/branch coverage remains supplemental and is not the primary adequacy gate
- default enforcement is `phase2`:
  - fail on malformed matrix state
  - fail on stale matrix rows, stale proof annotations, or non-collected proof annotations
  - fail when required `unit` or `cli_contract` proof is not satisfied by passed pytest items
- `phase3` is reserved for environments that actually execute the required real-backend proof tiers
- `scripts/run_matrix_phase3.py` is the explicit higher-assurance runner:
  - run fast-path proof
  - run fixture-integration proof
  - run disposable real `python-anki` backup/profile proof
  - audit all resulting proof reports together under `phase3`

## Development Policy

- `uv.lock` is committed and treated as part of the source of truth for reproducible local and CI
  runs.
- The default integration fixture is generated from source, not manually curated local state.
- The default fixture is a deterministic contract fixture, not yet a true Anki collection fixture.
- Command placeholders are acceptable only when covered by explicit contract tests and clearly
  documented as incomplete.
- `uv` remains the workflow frontend; `hatchling` remains the configured build backend.
- Default packaged installs bundle the supported `anki==25.9.2` runtime.
- Real `python-anki` development still supports a sibling local source checkout configured through
  `ANKI_SOURCE_PATH`.
- Default pinned upstream reference for local setup: Anki tag `25.09.2`.
- Raw source checkout support is currently sufficient for import-path verification, but real
  `Collection`-level validation may require built/generated upstream Python artifacts or an
  installed official `anki` wheel.

## Local Real-Backend Setup

- `ANKI_SOURCE_PATH=/absolute/path/to/anki`
- `ANKICLI_REAL_COLLECTION=/absolute/path/to/collection.anki2` for opt-in true collection checks
- Runtime resolution order under that path: `pylib/`, then `python/`, then repo root
- Default repo workflow and default user installs do not require Anki source
- `backend_python_anki_real` is the only test tier that depends on this setup today
- `backend_python_anki_backup_real` also depends on this setup, but creates its own disposable
  profile root via `ANKICLI_ANKI2_ROOT` during the test run
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
  - `changelog [--all]`
  - `--collection /path/to/collection.anki2`
  - `--profile <name>`
  - `doctor env|backend|capabilities|collection|safety`
  - `backend list|info|capabilities|test-connection`
  - `auth status|login|logout`
  - `profile list|get|default|resolve`
  - `backup status|list|create|get|restore`
  - `collection info|stats|validate|lock-status`
  - `sync status|run|pull|push`
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
  - owns standalone sync auth and stored credentials
  - owns local profile discovery, backup creation, and backup restore
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
    - `auth status|login|logout`
    - `profile list|get|default|resolve`
    - `backup status|list|create|get|restore`
    - `sync status|run|pull|push`
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
- `--collection` and `--profile` are mutually exclusive.
- `--profile` resolves local Anki data using platform defaults for macOS, Windows, and Linux.
- `auth login` stores sync credentials in the supported local credential store.
- `sync status` is the safe preflight command before any real sync operation.
- Sync is not backup. Backup and restore are local rollback flows, not remote replication.
- `backup restore` is CLI-only, requires `--yes`, and creates a fresh safety backup first.
- Risky real `python-anki` writes create an automatic pre-mutation backup unless
  `--no-auto-backup` is passed.
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

Sync/auth-specific stable error codes:

- `AUTH_REQUIRED`
- `AUTH_INVALID`
- `AUTH_STORAGE_UNAVAILABLE`
- `SYNC_UNAVAILABLE`
- `SYNC_CONFLICT`
- `SYNC_IN_PROGRESS`
- `SYNC_FAILED`

Backup/profile-specific stable error codes:

- `BACKUP_UNAVAILABLE`
- `BACKUP_NOT_FOUND`
- `BACKUP_CREATE_FAILED`
- `BACKUP_RESTORE_FAILED`
- `BACKUP_RESTORE_UNSAFE`
- `PROFILE_NOT_FOUND`
- `PROFILE_RESOLUTION_FAILED`
