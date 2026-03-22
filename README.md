# ankicli

`ankicli` is a local-first, automation-grade CLI for inspecting and mutating Anki collections.

The repository is intentionally test-first. The initial goal is to make the product shape, safety
rules, and test tiers durable before the full feature set turns green.

## Status

- Package scaffold exists.
- JSON response contract exists.
- Test pyramid exists: `unit`, `smoke`, `fixture_integration`, `e2e`, `distribution`.
- Core V1 command groups exist with a mix of implemented diagnostics and placeholder operations.

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
```

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
- `backend_python_anki_real`: reserved for future true `import anki` collection coverage

## Confidence Matrix

- `unit` proves local logic and envelopes. It does not prove entrypoints, packaging, or Anki access.
- `smoke` proves the most important commands still respond. It does not prove distribution or real
  backend semantics.
- `fixture_integration` proves deterministic fixture wiring and current contract behavior against the
  repo-owned SQLite fixture. It does not prove a real Anki collection can be opened.
- `e2e` proves the editable installed CLI entrypoint works in the dev environment. It does not prove
  wheel or sdist installation in a clean environment.
- `distribution` proves the built artifact installs and the exported CLI entrypoint runs from an
  isolated environment.

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
- Fixture-integration validates a repo-owned deterministic fixture path and current contract
  behavior.
- E2E validates the editable installed entrypoint in the development environment.
- Distribution validates built-artifact installation in an isolated environment.
- Real collection reads through `import anki` are still incomplete and should be expanded command by
  command.
