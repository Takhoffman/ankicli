# AnkiCLI Spec

## Summary

Build `ankicli` as a local-first, automation-grade Anki collection management CLI with a stable
service layer, JSON-first responses, and a backend seam present from day one.

## V1 Focus

- Open a collection
- Inspect decks, models, notes, and cards
- Search notes and cards
- Add, update, and delete notes
- Suspend and unsuspend cards
- Emit structured JSON for all important commands

## Backend Policy

- Primary backend: `python-anki`
- Deferred backend: `ankiconnect`
- No raw SQLite write backend in V1

## Test Policy

- Unit tests for fast contract and logic coverage
- Smoke tests for the default local and CI loop
- Fixture-integration tests against a repo-owned deterministic contract fixture by default
- E2E tests through the editable installed CLI entrypoint
- Distribution tests through built artifacts installed into an isolated environment
- Real Python-Anki integration remains a separate future tier

## Development Policy

- `uv.lock` is committed and treated as part of the source of truth for reproducible local and CI
  runs.
- The default integration fixture is generated from source, not manually curated local state.
- The default fixture is a deterministic contract fixture, not yet a true Anki collection fixture.
- Command placeholders are acceptable only when covered by explicit contract tests and clearly
  documented as incomplete.
- `uv` remains the workflow frontend; `hatchling` remains the configured build backend.

## Output Contract

Success:

```json
{"ok": true, "backend": "python-anki", "data": {}, "meta": {}}
```

Failure:

```json
{"ok": false, "backend": "python-anki", "error": {"code": "EXAMPLE", "message": "..." }}
```
