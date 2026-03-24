# ankicli

`ankicli` is a local-first, automation-grade CLI for inspecting and mutating Anki collections.

The repository is intentionally test-first. The initial goal is to make the product shape, safety
rules, and test tiers durable before the full feature set turns green.

## Status

- Installable Python CLI package exists.
- JSON response contract exists and is exercised by tests.
- Test pyramid exists: `unit`, `smoke`, `fixture_integration`, `e2e`, `distribution`,
  `backend_python_anki_real`.
- Core V1 read/search/note/card mutation commands are implemented.
- Diagnostics, collection ops, search ergonomics, and read-only media inspection are implemented.
- Local profile discovery/resolution and backup flows are implemented for `python-anki`.

## Quickstart

Use the packaged CLI:

```bash
uv build
python -m pip install dist/ankicli-*.whl
ankicli --help
ankicli --version
```

Use the editable dev CLI:

```bash
uv sync --extra dev --frozen
uv run ankicli --help
```

Inspect a collection:

```bash
uv run ankicli --json --collection /path/to/collection.anki2 collection info
uv run ankicli --json --profile "User 1" collection info
uv run ankicli --json --collection /path/to/collection.anki2 collection stats
uv run ankicli --json profile list
uv run ankicli --json profile default
uv run ankicli --json profile resolve --name "User 1"
uv run ankicli --json --collection /path/to/collection.anki2 deck stats --name Default
uv run ankicli --json --collection /path/to/collection.anki2 deck get --name Default
uv run ankicli --json --collection /path/to/collection.anki2 model get --name Basic
uv run ankicli --json --collection /path/to/collection.anki2 model fields --name Basic
uv run ankicli --json --collection /path/to/collection.anki2 model templates --name Basic
uv run ankicli --json --collection /path/to/collection.anki2 media list
uv run ankicli --json --collection /path/to/collection.anki2 media check
uv run ankicli --json --collection /path/to/collection.anki2 media attach --source ./photo.png --dry-run
uv run ankicli --json doctor backend
uv run ankicli --json doctor capabilities
```

Search and mutate safely:

```bash
uv run ankicli --json --collection /path/to/collection.anki2 search notes --query 'deck:Default'
uv run ankicli --json --collection /path/to/collection.anki2 search count --kind notes --query 'deck:Default'
uv run ankicli --json --collection /path/to/collection.anki2 search preview --kind notes --query 'deck:Default' --limit 5
uv run ankicli --json --collection /path/to/collection.anki2 tag list
uv run ankicli --json --collection /path/to/collection.anki2 tag apply --id 123 --tag review --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 note add --deck Default --model Basic --field 'Front=hello' --field 'Back=world' --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 note add-tags --id 123 --tag review --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 note delete --id 123 --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 card suspend --id 456 --dry-run
uv run ankicli --json auth status
uv run ankicli --json --collection /path/to/collection.anki2 sync status
uv run ankicli --json --profile "User 1" backup status
uv run ankicli --json --profile "User 1" backup list
uv run ankicli --json --profile "User 1" backup create
```

Current beta defaults:

- Prefer `--json` for scripts and agents.
- Use `--dry-run` first on write-capable commands.
- Use `sync status` as the safe preflight before running a real sync.
- Prefer `--profile` for normal local usage and `--collection` for explicit low-level targeting.
- Sync is not backup. Use `backup create` or the built-in auto-backup flow when rollback matters.
- Riskier local `python-anki` writes create an automatic pre-mutation backup unless you pass
  `--no-auto-backup`.
- Real `note delete`, `card suspend`, and `card unsuspend` require `--yes`.

## Development

Install:

```bash
uv sync --extra dev --frozen
```

Fast path:

```bash
uv run pytest -m "unit or smoke"
```

Targeted suites:

```bash
uv run pytest tests/integration/test_python_anki_backend.py
uv run pytest tests/e2e/test_cli_e2e.py
uv run pytest -m distribution
uv run pytest -m backend_python_anki_real
uv run pytest -m backend_python_anki_backup_real
```

Disposable real backup tier:

- `backend_python_anki_backup_real` is local-only and uses a temporary Anki2 profile root under
  `/tmp`.
- It does not touch a personal profile.
- It does not require Anki Desktop, AnkiConnect, or AnkiWeb.
- It does require a real `anki` runtime via `ANKI_SOURCE_PATH`.
- Shortcut: `make test-backup-real`

Full path:

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check .
```

Build:

```bash
uv build
```

Package validation:

```bash
uv build
uv run pytest -m distribution
```

## Test Tiers

- `unit`: pure logic, parsing, and JSON contract tests
- `smoke`: fastest local and CI confidence checks
- `fixture_integration`: deterministic repo-owned fixture and command/back-end contract coverage
- `e2e`: editable-install CLI entrypoint checks through `uv run ankicli ...`
- `distribution`: built artifact validation from an isolated install target
- `backend_python_anki_real`: opt-in real `import anki` environment and future collection coverage
- `backend_python_anki_backup_real`: opt-in disposable real backup/profile round-trip coverage
- `backend_ankiconnect_real`: opt-in live AnkiConnect integration coverage against a running Anki
  Desktop instance

## Implemented Commands

Currently implemented:

- `doctor env`
- `doctor backend`
- `doctor capabilities`
- `doctor collection`
- `doctor safety`
- `backend list`
- `backend info`
- `backend capabilities`
- `backend test-connection`
- `auth status`
- `auth login`
- `auth logout`
- `profile list`
- `profile get`
- `profile default`
- `profile resolve`
- `backup status`
- `backup list`
- `backup create`
- `backup get`
- `backup restore`
- `collection info`
- `collection stats`
- `collection validate`
- `collection lock-status`
- `sync status`
- `sync run`
- `sync pull`
- `sync push`
- `deck list`
- `deck get`
- `deck stats`
- `deck create`
- `deck rename`
- `deck delete`
- `deck reparent`
- `model list`
- `model get`
- `model fields`
- `model templates`
- `model validate-note`
- `media list`
- `media check`
- `media attach`
- `media orphaned`
- `media resolve-path`
- `search notes`
- `search cards`
- `search count`
- `search preview`
- `tag list`
- `tag apply`
- `tag remove`
- `tag rename`
- `tag delete`
- `tag reparent`
- `export notes`
- `export cards`
- `import notes`
- `import patch`
- `note get`
- `note fields`
- `note add`
- `note update`
- `note delete`
- `note move-deck`
- `note add-tags`
- `note remove-tags`
- `card get`
- `card suspend`
- `card unsuspend`

Backend availability:

- `python-anki`: full currently implemented surface
- `ankiconnect`: initial live-desktop slice for read/search plus selected note/card/tag mutations
- `backend capabilities` now includes an operation-level `supported_operations` map so automation
  can detect unsupported commands before invoking them

AnkiConnect currently supports:

- `backend info`
- `backend capabilities`
- `backend test-connection`
- `collection info`
- `collection stats`
- `deck list`
- `deck get`
- `deck stats`
- `model list`
- `model get`
- `model fields`
- `model templates`
- `model validate-note`
- `tag list`
- `tag apply`
- `tag remove`
- `search notes`
- `search cards`
- `search count`
- `search preview`
- `export notes`
- `export cards`
- `import notes`
- `import patch`
- `note get`
- `note fields`
- `note add`
- `note update`
- `note move-deck`
- `note add-tags`
- `note remove-tags`
- `card get`
- `card suspend`
- `card unsuspend`

AnkiConnect does not support yet:

- `auth status`
- `auth login`
- `auth logout`
- `profile list`
- `profile get`
- `profile default`
- `profile resolve`
- `backup status`
- `backup list`
- `backup create`
- `backup get`
- `backup restore`
- `sync status`
- `sync run`
- `sync pull`
- `sync push`
- `note delete`
- `deck create`
- `deck rename`
- `deck delete`
- `deck reparent`
- `tag rename`
- `tag delete`
- `tag reparent`
- `media list|check|attach|orphaned|resolve-path`

Unsupported backend operations now fail with the structured error code
`BACKEND_OPERATION_UNSUPPORTED`.

Sync/auth notes:

- `python-anki` is the standalone sync/auth backend.
- `auth login` stores sync credentials in the OS keychain when supported.
- `sync status` is the intended preflight before `sync run`.
- `sync pull` and `sync push` are explicit expert flows.

## CLI Examples

Collection and catalog:

```bash
uv run ankicli --version
uv run ankicli --json doctor backend
uv run ankicli --json doctor capabilities
uv run ankicli --json --collection /path/to/collection.anki2 collection info
uv run ankicli --json --collection /path/to/collection.anki2 collection stats
uv run ankicli --json --collection /path/to/collection.anki2 collection validate
uv run ankicli --json --collection /path/to/collection.anki2 collection lock-status
uv run ankicli --json --collection /path/to/collection.anki2 deck list
uv run ankicli --json --collection /path/to/collection.anki2 deck get --name Default
uv run ankicli --json --collection /path/to/collection.anki2 deck stats --name Default
uv run ankicli --json --collection /path/to/collection.anki2 deck create --name French --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 deck rename --name French --to 'French::Verbs' --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 deck delete --name French --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 deck reparent --name 'French::Verbs' --to-parent Default --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 model list
uv run ankicli --json --collection /path/to/collection.anki2 model get --name Basic
uv run ankicli --json --collection /path/to/collection.anki2 model fields --name Basic
uv run ankicli --json --collection /path/to/collection.anki2 model templates --name Basic
uv run ankicli --json --collection /path/to/collection.anki2 media list
uv run ankicli --json --collection /path/to/collection.anki2 media check
uv run ankicli --json --collection /path/to/collection.anki2 media attach --source ./photo.png --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 media orphaned
uv run ankicli --json --collection /path/to/collection.anki2 media resolve-path --name used.png
uv run ankicli --json --collection /path/to/collection.anki2 model validate-note --model Basic --field 'Front=hello' --field 'Back=world'
uv run ankicli --json backend test-connection
uv run ankicli --json --backend ankiconnect collection info
uv run ankicli --json --backend ankiconnect deck get --name Default
```

Search:

```bash
uv run ankicli --json --collection /path/to/collection.anki2 search notes --query 'deck:Default'
uv run ankicli --json --collection /path/to/collection.anki2 search cards --query 'is:new'
uv run ankicli --json --collection /path/to/collection.anki2 search count --kind notes --query 'deck:Default'
uv run ankicli --json --collection /path/to/collection.anki2 search preview --kind cards --query 'deck:Default' --limit 5
uv run ankicli --json --collection /path/to/collection.anki2 tag list
uv run ankicli --json --collection /path/to/collection.anki2 tag rename --name review --to followup --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 tag delete --tag followup --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 tag reparent --tag followup --to-parent project --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 export notes --query 'deck:Default'
uv run ankicli --json --collection /path/to/collection.anki2 export cards --query 'deck:Default'
```

Notes:

```bash
uv run ankicli --json --collection /path/to/collection.anki2 note get --id 123
uv run ankicli --json --collection /path/to/collection.anki2 note fields --id 123
uv run ankicli --json --collection /path/to/collection.anki2 note add --deck Default --model Basic --field 'Front=hello' --field 'Back=world'
uv run ankicli --json --collection /path/to/collection.anki2 note update --id 123 --field 'Back=updated'
uv run ankicli --json --collection /path/to/collection.anki2 note move-deck --id 123 --deck Default --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 note add-tags --id 123 --tag review --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 note remove-tags --id 123 --tag review --yes
uv run ankicli --json --collection /path/to/collection.anki2 tag apply --id 123 --tag review --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 tag remove --id 123 --tag review --yes
uv run ankicli --json --collection /path/to/collection.anki2 note delete --id 123 --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 note delete --id 123 --yes
```

Import/export:

```bash
uv run ankicli --json --collection /path/to/collection.anki2 export notes --query 'deck:Default'
uv run ankicli --json --collection /path/to/collection.anki2 export cards --query 'deck:Default'
uv run ankicli --collection /path/to/collection.anki2 export notes --query 'deck:Default' --ndjson
uv run ankicli --collection /path/to/collection.anki2 export cards --query 'deck:Default' --ndjson
uv run ankicli --json --collection /path/to/collection.anki2 import notes --input notes.json --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 import notes --input notes.json --yes
uv run ankicli --json --collection /path/to/collection.anki2 import patch --input patches.json --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 import patch --input patches.json --yes
cat notes.json | uv run ankicli --json --collection /path/to/collection.anki2 import notes --stdin-json --dry-run
cat patches.json | uv run ankicli --json --collection /path/to/collection.anki2 import patch --stdin-json --dry-run
```

Cards:

```bash
uv run ankicli --json --collection /path/to/collection.anki2 card get --id 456
uv run ankicli --json --collection /path/to/collection.anki2 card suspend --id 456 --dry-run
uv run ankicli --json --collection /path/to/collection.anki2 card unsuspend --id 456 --yes
```

Safety model:

- `tag apply`, `tag remove`, `tag rename`, `tag delete`, `tag reparent`, `media attach`,
  `import notes`, `import patch`, `note delete`, `note add-tags`, `note remove-tags`,
  `card suspend`, and `card unsuspend` require `--yes` for real mutation.
- `--dry-run` is available on the current write-capable commands to validate intent without writing.
- `--json` is supported across the implemented command surface and should be treated as the primary
  automation mode.
- `export notes` and `export cards` also support `--ndjson` for one-record-per-line automation output.

## Confidence Matrix

- `unit` proves local logic and envelopes. It does not prove entrypoints, packaging, or Anki access.
- `smoke` proves the most important commands still respond. It does not prove distribution or real
  backend semantics.
- `fixture_integration` proves deterministic fixture wiring and current contract behavior against the
  repo-owned SQLite fixture. It does not prove a real Anki collection can be opened, and it is
  expected to stay green whether or not a local `anki` wheel is installed.
- `e2e` proves the editable installed CLI entrypoint works in the dev environment. It does not prove
  wheel or sdist installation in a clean environment.
- `distribution` proves the built artifact installs and the exported CLI entrypoint runs from an
  isolated environment.
- `backend_python_anki_real` proves the local Anki setup plus the currently implemented command
  slices against a real collection. It is optional and not part of the default loop.
- Installing `anki` locally for real-backend work must not make the default fixture-integration
  suite stricter than the contract fixture supports.
- `ankiconnect` is a separate live-desktop backend path and does not use
  `backend_python_anki_real`.

## Live AnkiConnect Checks

Use this only when Anki Desktop is running locally with the AnkiConnect add-on enabled.

Recommended minimum setup:

```bash
UV_CACHE_DIR=.uv-cache uv run python scripts/prepare_ankiconnect_backend.py
```

Notes:

- `ANKICONNECT_URL` defaults to `http://127.0.0.1:8765`; override it only if your AnkiConnect
  server is bound elsewhere.
- The helper script [prepare_ankiconnect_backend.py](/Users/thoffman/ankicli/scripts/prepare_ankiconnect_backend.py)
  prints the exact exports and pytest command for your current desktop state.
- The live AnkiConnect tests skip cleanly when Anki Desktop or the add-on is not reachable.
- The marker is opt-in and is not part of the default CI path.

## Real Python-Anki Setup

Use this only for real backend development. It is not required for normal scaffold, contract,
fixture-integration, e2e, or distribution work.

Pinned upstream reference:

- Upstream repo: [ankitects/anki](https://github.com/ankitects/anki)
- Recommended tag: `25.09.2`

Recommended checkout layout:

```text
~/code/anki
~/code/ankicli
```

Setup flow:

```bash
git clone --branch 25.09.2 https://github.com/ankitects/anki ~/code/anki
cd /Users/thoffman/ankicli
export ANKI_SOURCE_PATH=~/code/anki
UV_CACHE_DIR=.uv-cache uv run python -c "from ankicli.runtime import configure_anki_source_path; import importlib.util; configure_anki_source_path(); print(importlib.util.find_spec('anki') is not None)"
UV_CACHE_DIR=.uv-cache uv run pytest -m backend_python_anki_real -k anki_source_path_enables_import
```

Real collection validation flow:

```bash
UV_CACHE_DIR=.uv-cache uv run python scripts/prepare_real_backend.py --reset
```

Notes:

- `ANKI_SOURCE_PATH` is the only supported local source override for real `python-anki` work.
- The runtime currently looks for `pylib/`, then `python/`, then the repo root under
  `ANKI_SOURCE_PATH`.
- A raw upstream source checkout is currently enough for import-path checks, but not necessarily for
  `Collection`-level validation. Upstream source may require generated build artifacts such as the
  protobuf outputs before `anki.collection.Collection` can be used directly.
- If `ANKI_SOURCE_PATH` is unset or wrong, the default fast loop still works and real-backend tests
  should be skipped or remain unavailable.
- Set `ANKICLI_REAL_COLLECTION=/absolute/path/to/collection.anki2` when you want the real-backend
  suite to exercise `collection info` against an actual collection.
- For true collection-level validation, use either:
  - an installed official `anki` wheel in the project environment, or
  - a built upstream Anki checkout with the generated Python artifacts available
- One workable local pattern is a shim path such as `/tmp/anki-wheel/pylib/anki` pointing at the
  installed wheel package, then setting `ANKI_SOURCE_PATH=/tmp/anki-wheel`.
- The helper script [prepare_real_backend.py](/Users/thoffman/ankicli/scripts/prepare_real_backend.py)
  automates the validated local flow and prints the exact exports for the real suite.

## Fixture Collection

Fixture-integration tests default to a repo-owned deterministic contract fixture built from
[build_fixture.py](/Users/thoffman/ankicli/tests/fixtures/build_fixture.py).
`ANKICLI_TEST_COLLECTION` can still override that path when you want to run against a different
local collection.

This fixture is intentionally not described as a real Anki collection. It is a deterministic SQLite
fixture for contract-level testing. A separate real Anki fixture track should be introduced once the
backend can reliably open collections through `import anki`.

## Packaging Stack

- `uv` is the workflow frontend for environment sync, command execution, and build invocation.
- `hatchling` is the PEP 517 build backend configured in
  [pyproject.toml](/Users/thoffman/ankicli/pyproject.toml).
- `uv build` invokes the configured build backend; it is not a different packaging format.

Current implementation status:

- Unit and smoke validate the CLI contract and fast command wiring.
- Fixture-integration validates the contract fixture path and remains stable even when a local
  `anki` wheel is installed for real-backend work.
- E2E validates the editable installed entrypoint in the development environment.
- Distribution validates built-artifact installation in an isolated environment.
- Real collection validation is proven locally against `anki==25.9.2` for the implemented command
  slices, but raw source checkout support is still only partially proven unless that checkout has
  been built far enough to generate the required Python artifacts.
