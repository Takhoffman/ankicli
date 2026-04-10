---
name: release
description: Use when preparing, validating, and publishing ankicli releases, especially for GitHub Pages deploys, tagged standalone artifact releases, installer verification, and optional PyPI publishing.
---

# Release

This skill is the release workflow layer for `ankicli`. Use it when the task involves shipping a new version, validating the public install path, publishing the product site, or checking release automation end to end.

## Core Rules

1. Treat releases as product changes, not just git tags. Validate the site, installers, standalone artifacts, and package path together.
2. Read before mutate. Inspect the current version, workflow state, and release assets before changing version numbers, tags, or release metadata.
3. Prefer the standalone artifact path as the primary user install surface. Keep `pipx install ankicli` as fallback documentation, not the hero path.
4. Verify both public fronts:
   - GitHub Pages site
   - GitHub Releases assets
5. Do not cut a release without checking the installer contract:
   - raw installer script URLs exist
   - expected asset names match the release workflow
   - post-install verification commands still work
6. Preserve version consistency across Python package metadata, standalone artifact names, and release tags.
7. Never assume a release succeeded because a tag exists. Check workflow status and actual uploaded assets.

## Release Surfaces

- Product site: GitHub Pages
- Standalone artifacts: GitHub Releases
- Raw installer entrypoints:
  - `scripts/install.sh`
  - `scripts/install.ps1`
- Optional package distribution: PyPI/manual publish flow

## Workflow Playbooks

### Pre-Release Validation

Use this before tagging a release:
- inspect current package version
- run repo lint
- run unit, smoke, and distribution coverage relevant to install/release paths
- build the site
- build at least one standalone artifact locally when possible
- extract and execute the built artifact
- confirm install script URLs and asset naming still align

Good progression:
- inspect version and git state
- validate Python/package path
- validate site build
- validate installer tests
- validate standalone artifact build
- tag only after the above is green

### GitHub Pages Validation

Use when the product site is changing:
- build the Astro site locally
- verify landing page install commands
- verify docs links and install pages
- confirm the Pages workflow still targets the built static output
- after push, confirm the live Pages URL renders successfully

### Tagged Release

Use when shipping a real version:
- bump version in package metadata first
- commit the version change
- create and push a tag of the form `vX.Y.Z`
- confirm the release workflow ran
- confirm expected artifacts were uploaded:
  - macOS x64
  - macOS arm64
  - Linux x64
  - Windows x64
  - checksums file
- confirm one downloaded artifact runs `ankicli --version` and `ankicli --json doctor backend`

### Installer Verification

Use when installer scripts or release artifact logic changes:
- verify shell installer path logic
- verify PowerShell parameter and path logic
- verify checksum mismatch behavior
- verify latest-version and explicit-version flows
- verify install location and PATH instructions are still accurate

### Optional PyPI Publish

Use only when the package distribution path matters:
- build the wheel/sdist
- run distribution validation
- publish manually or via the chosen release process
- confirm PyPI and standalone release version numbers match

## Versioning Rules

- Package version uses `X.Y.Z`
- Git tag uses `vX.Y.Z`
- Release artifacts use `ankicli-X.Y.Z-<target>`
- Checksums file uses `ankicli-X.Y.Z-checksums.txt`

Do not mix tag-only versions with unchanged package metadata.

## Error Handling

- Missing Pages deployment: inspect the `pages` workflow and built site artifact path.
- Missing release assets: inspect the `release` workflow matrix and uploaded artifact names.
- Installer download failure: check tag name, release asset names, and raw script URLs first.
- Checksum mismatch: treat as a release-blocking issue.
- Standalone artifact launches but backend probe fails: treat as a packaging/runtime regression, not a docs issue.
- PyPI publish problems: separate them from GitHub Release problems; they are parallel distribution paths.

## References

Read these when contract detail is needed:
- Package metadata: [`pyproject.toml`](/Users/thoffman/ankicli/pyproject.toml)
- CI workflow: [`.github/workflows/ci.yml`](/Users/thoffman/ankicli/.github/workflows/ci.yml)
- Pages workflow: [`.github/workflows/pages.yml`](/Users/thoffman/ankicli/.github/workflows/pages.yml)
- Release workflow: [`.github/workflows/release.yml`](/Users/thoffman/ankicli/.github/workflows/release.yml)
- Product site: [`site/src/pages/index.astro`](/Users/thoffman/ankicli/site/src/pages/index.astro)
- Installer scripts: [`scripts/install.sh`](/Users/thoffman/ankicli/scripts/install.sh) and [`scripts/install.ps1`](/Users/thoffman/ankicli/scripts/install.ps1)

## Anti-Patterns

- Do not tag first and hope validation passes later.
- Do not change release asset names in one place without updating installers and docs.
- Do not publish a release if the standalone artifact path is broken but PyPI still works.
- Do not treat Pages deployment as optional once the site is the public install front door.
- Do not overwrite user-facing install commands ad hoc in docs; keep them aligned with the installer contract.
