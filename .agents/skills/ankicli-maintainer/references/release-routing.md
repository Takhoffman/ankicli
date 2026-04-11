# Release Routing

Use this reference first when the operator says "release", "ship", "publish", "cut a tag", or asks whether the repository is ready to release.

## Start by clarifying intent

Treat release work as one of four modes:

- release readiness only
- tagged GitHub release
- installer or artifact verification only
- package publishing only

Do not jump straight to version bumps or tags unless the operator clearly wants a real release.

## Baseline checks

Inspect these first:

- current git branch
- working tree cleanliness
- package version in `pyproject.toml`
- whether `main` already contains the intended changes
- whether CI, Pages, and release workflows match the current release contract

Useful commands:

```bash
git status --short
git branch --show-current
rg -n '^version = ' pyproject.toml
uv sync --extra dev --frozen
```

## Validation order

Prefer the narrowest useful release gate first, then broaden:

```bash
uv run ruff check .
uv run pytest -m "unit or smoke"
uv build
uv run pytest -m distribution
```

If the release touches standalone packaging, also build at least one target artifact:

```bash
uv run python scripts/build_release_artifact.py --target <target> --version <version>
```

Supported targets:

- `darwin-x64`
- `darwin-arm64`
- `linux-x64`
- `windows-x64`

## Decision rule

- If validation is red, stop and fix release blockers.
- If validation is green and the operator wants a real release, continue into `release.md`.
- If the task is narrower than a full release, read `distribution.md` next instead of treating everything as a tag flow.
