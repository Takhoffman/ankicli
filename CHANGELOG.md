# Changelog

All notable changes to `ankicli` are documented here.

## Unreleased

## 0.1.2 - 2026-04-28

- Hardened release automation so tag/version mismatches fail before platform builds or publish
  steps run.
- Made release publishing reruns safer by allowing existing GitHub release assets and PyPI files
  to be handled idempotently.
- Hardened `auth status` so unsupported live-desktop backends return structured unsupported
  responses before reading local credentials.
- Made installer checksum and extraction paths more deterministic under inherited locale settings.
- Promoted deterministic fixture integration, editable-entrypoint e2e, packaging, and site checks
  into the CI release confidence path.
- Made fixture metadata relocatable and excluded local bootstrap/cache/venv/build output from source
  distributions.
- Hardened shell and PowerShell installers by validating release versions and targets before
  download, checksum lookup, extraction, or install replacement.
- Tightened PowerShell checksum matching to use exact archive-name fields instead of substring
  matches.
- Thanks to the contributors behind PRs #2, #3, #4, and #5 for the release improvements.

## 0.1.1 - 2026-04-11

- Added this changelog as the source of truth for user-visible changes.
- Added `ankicli changelog` for terminal access to the latest notes.
- Added `ankicli changelog --all` for the full changelog.

## 0.1.0 - Initial Development

- Established the local-first Anki CLI surface for collection inspection and mutation.
- Added structured JSON output for automation and readable human output for direct terminal use.
- Added profile, backend, backup, sync, note, card, tag, media, import, export, study, and catalog
  command groups.
