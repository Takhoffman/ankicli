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
- existing local/remote tags for the intended version
- existing GitHub Releases, especially empty releases or releases whose name and tag disagree
- latest published PyPI versions when package publishing is in scope
- recent failed release workflow runs

Useful commands:

```bash
git status --short
git branch --show-current
rg -n '^version = ' pyproject.toml
git tag --sort=-version:refname | head -n 20
git ls-remote --tags origin 'refs/tags/v*'
gh release list --repo Takhoffman/ankicli --limit 20
gh run list --repo Takhoffman/ankicli --workflow release --limit 10
python3 -m pip index versions anki-agent-toolkit
uv sync --extra dev --frozen
```

## Release-state preflight

Before choosing or bumping a version, verify that release state is internally consistent:

- intended package version `X.Y.Z` must not already be published to PyPI unless the task is an
  idempotent rerun
- intended git tag `vX.Y.Z` must not already point at the wrong commit
- no existing GitHub Release should use the intended version name with a different tag
- no existing GitHub Release should have the intended tag but missing or incomplete assets unless
  the task is explicitly to repair that release
- failed release workflow runs for nearby tags must be inspected before pushing a new tag

Treat stale or mismatched release state as a release blocker. Stop and report exact evidence before
editing versions, tagging, deleting releases, or deleting tags.

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
- If release-state preflight finds stale tags, mismatched release names/tags, empty releases, or
  failed release workflows for the intended version, stop and ask for explicit cleanup approval.
- If validation is green and the operator wants a real release, continue into `release.md`.
- If the task is narrower than a full release, read `distribution.md` next instead of treating everything as a tag flow.
