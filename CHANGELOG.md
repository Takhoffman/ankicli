# Changelog

All notable changes to `ankicli` are documented here.

## Unreleased

## 0.1.3 - 2026-04-29

- Enforced the quality-matrix audit as a blocking CI gate across fast-path, fixture, and e2e proof
  reports. Thanks @stanlu.
- Added matrix coverage for workspace, skill, study, catalog export, and missing media failure
  contracts. Thanks @stanlu.
- Made the OpenClaw plugin contract portable on Windows, including `.cmd`/`.bat` command shims and
  Windows-style `ankicliPath` handling. Thanks @stanlu.
- Improved the phase3 matrix runner with labeled commands, reusable report directories, and clearer
  real-backend setup guidance. Thanks @stanlu.
- Added generated OpenClaw artifact freshness checks so catalog reference docs and bundled study
  skill guidance stay in sync with `ankicli.app.catalog`. Thanks @stanlu.

## 0.1.2 - 2026-04-28

- Hardened release automation so tag/version mismatches fail before platform builds or publish
  steps run. Thanks @stanlu.
- Made release publishing reruns safer by allowing existing GitHub release assets and PyPI files
  to be handled idempotently. Thanks @stanlu.
- Hardened `auth status` so unsupported live-desktop backends return structured unsupported
  responses before reading local credentials. Thanks @stanlu.
- Made installer checksum and extraction paths more deterministic under inherited locale settings.
  Thanks @stanlu.
- Promoted deterministic fixture integration, editable-entrypoint e2e, packaging, and site checks
  into the CI release confidence path. Thanks @stanlu.
- Made fixture metadata relocatable and excluded local bootstrap/cache/venv/build output from source
  distributions. Thanks @stanlu.
- Hardened shell and PowerShell installers by validating release versions and targets before
  download, checksum lookup, extraction, or install replacement. Thanks @stanlu.
- Tightened PowerShell checksum matching to use exact archive-name fields instead of substring
  matches. Thanks @stanlu.

## 0.1.1 - 2026-04-11

- Added this changelog as the source of truth for user-visible changes.
- Added `ankicli changelog` for terminal access to the latest notes.
- Added `ankicli changelog --all` for the full changelog.

## 0.1.0 - Initial Development

- Established the local-first Anki CLI surface for collection inspection and mutation.
- Added structured JSON output for automation and readable human output for direct terminal use.
- Added profile, backend, backup, sync, note, card, tag, media, import, export, study, and catalog
  command groups.
