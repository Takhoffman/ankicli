# Release Workflow

Use this reference when the operator wants to:

- prepare a release
- validate release readiness
- ship a tagged GitHub release
- verify standalone artifacts or installer scripts
- optionally publish the Python package

This repository has two names that must stay aligned:

- PyPI distribution: `anki-agent-toolkit`
- executable command: `ankicli`

## Maintainer workflow

Start by clarifying the release intent:

- release readiness only
- full tagged GitHub release
- installer/artifact verification only
- package publishing only

Do not jump straight to tagging unless the operator explicitly wants a real release.

## Pre-release baseline

Check these first:

- current branch and git status
- current version in `pyproject.toml`
- whether `main` already contains the intended changes
- whether the release workflows and installer scripts match the current product contract

Useful commands:

```bash
git status --short
git branch --show-current
rg -n '^version = ' pyproject.toml
uv sync --extra dev --frozen
```

## Validation order

Prefer the smallest useful gate first, then broaden:

```bash
uv run ruff check .
uv run pytest -m "unit or smoke"
uv build
uv run pytest -m distribution
```

If release artifacts changed, also validate standalone packaging:

```bash
uv run python scripts/build_release_artifact.py --target darwin-arm64 --version <version>
```

Use supported targets only:

- `darwin-x64`
- `darwin-arm64`
- `linux-x64`
- `windows-x64`

## Release contract

Treat releases as product changes, not just tags.

The release is only healthy if these surfaces line up:

- package version
- Git tag
- GitHub Release assets
- installer scripts
- product/docs site install commands

Expected artifact naming:

- `ankicli-<version>-darwin-arm64.tar.gz`
- `ankicli-<version>-darwin-x64.tar.gz`
- `ankicli-<version>-linux-x64.tar.gz`
- `ankicli-<version>-windows-x64.zip`
- `ankicli-<version>-checksums.txt`

## Tagged release flow

Use this only when the operator explicitly wants to ship.

1. confirm the version to release
2. ensure the working tree is clean
3. ensure validation passed
4. create or verify the release commit
5. create a tag of the form `vX.Y.Z`
6. push the tag
7. confirm the release workflow ran and assets exist

The package version uses `X.Y.Z`.
The git tag uses `vX.Y.Z`.

## Installer verification

When installer scripts or artifacts changed, verify:

- raw installer URLs are still correct
- expected asset names still match the release workflow
- checksums still match the installer contract
- post-install verification commands still work

Relevant files:

- [`scripts/install.sh`](/Users/thoffman/ankicli/scripts/install.sh)
- [`scripts/install.ps1`](/Users/thoffman/ankicli/scripts/install.ps1)
- [`src/ankicli/app/releases.py`](/Users/thoffman/ankicli/src/ankicli/app/releases.py)

## Site and docs checks

If the public site or install docs changed, validate them before release:

```bash
cd site
npm install
npm run build
```

Confirm:

- landing page install commands match the current installers
- docs still describe the supported install path
- release/version wording is consistent

## Optional PyPI publishing

Use only when package distribution matters for the current release.

Build first:

```bash
uv build
```

Then publish using the configured workflow or manual `uv publish` flow.

Do not describe PyPI success as proof that GitHub Release artifacts are healthy. They are parallel distribution paths.

## Release blockers

Treat these as release-blocking:

- failing lint, unit, smoke, or distribution validation
- artifact name drift
- checksum mismatch
- standalone artifact launches but `ankicli --json doctor backend` fails
- installer script points at missing assets
- package version, git tag, and release asset version drift

## Anti-patterns

- do not tag first and validate later
- do not publish artifacts when distribution checks are red
- do not update docs install commands ad hoc without verifying the installer contract
- do not conflate PyPI success with release success
- do not change executable name and package name casually
