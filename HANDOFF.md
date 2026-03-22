# Handoff

## Current State

- Repository contains a test-first scaffold for `ankicli`.
- Tooling is standardized on `uv`, `ruff`, `pytest`, and `hatchling`.
- CI is tiered into a fast path and a packaging path.
- Test semantics are now explicit:
  - `unit`
  - `smoke`
  - `fixture_integration`
  - `e2e`
  - `distribution`
  - `backend_python_anki_real` is reserved for future real Anki-backed coverage

## Verified Commands

```bash
UV_CACHE_DIR=.uv-cache uv run ruff check .
UV_CACHE_DIR=.uv-cache uv build
UV_CACHE_DIR=.uv-cache uv run pytest
```

Last known result:

- `17 passed, 1 xfailed`
- The `xfail` is `search notes`, which is intentionally unimplemented

## What The Repo Proves Today

- JSON envelope and CLI contract wiring are stable.
- Editable-install CLI entrypoint works through `uv run ankicli ...`.
- Built wheel installs into an isolated virtualenv and exposes the `ankicli` command.
- Fixture-level integration uses a deterministic repo-owned SQLite contract fixture.

## What The Repo Does Not Prove Yet

- Real `import anki` collection reads and writes.
- True Anki collection schema compatibility.
- Backend parity beyond the placeholder `python-anki` adapter.

## Important Files

- Spec: [docs/spec.md](/Users/thoffman/ankicli/docs/spec.md)
- Repo guidance: [AGENTS.md](/Users/thoffman/ankicli/AGENTS.md)
- CLI entrypoint: [src/ankicli/main.py](/Users/thoffman/ankicli/src/ankicli/main.py)
- Backend stub: [src/ankicli/backends/python_anki.py](/Users/thoffman/ankicli/src/ankicli/backends/python_anki.py)
- Fixture generator: [tests/fixtures/build_fixture.py](/Users/thoffman/ankicli/tests/fixtures/build_fixture.py)
- Distribution test: [tests/distribution/test_built_artifact.py](/Users/thoffman/ankicli/tests/distribution/test_built_artifact.py)

## Recommended Next Steps

1. Implement `collection info` in the `python-anki` backend and convert its fixture-level assertions into real backend behavior where possible.
2. Add a true `backend_python_anki_real` suite only when a real Anki collection fixture exists and can be opened through `import anki`.
3. Keep distribution validation separate from editable-entrypoint e2e so packaging confidence stays explicit.
