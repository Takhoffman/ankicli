# Changelog

All notable changes to `ankicli` are documented here.

## Unreleased

## 0.1.2 - 2026-04-28

- Thanks `stainlu` for hardening release automation so tag/version mismatches fail before platform
  builds or publish steps run.
- Thanks `stainlu` for making release publishing reruns safer by allowing existing GitHub release
  assets and PyPI files to be handled idempotently.
- Thanks `stainlu` for hardening `auth status` so unsupported live-desktop backends return
  structured unsupported responses before reading local credentials.
- Thanks `stainlu` for making installer checksum and extraction paths more deterministic under
  inherited locale settings.
- Thanks `stainlu` for promoting deterministic fixture integration, editable-entrypoint e2e,
  packaging, and site checks into the CI release confidence path.
- Thanks `stainlu` for making fixture metadata relocatable and excluding local
  bootstrap/cache/venv/build output from source distributions.
- Thanks `stainlu` for hardening shell and PowerShell installers by validating release versions
  and targets before download, checksum lookup, extraction, or install replacement.
- Thanks `stainlu` for tightening PowerShell checksum matching to use exact archive-name fields
  instead of substring matches.

## 0.1.1 - 2026-04-11

- Added this changelog as the source of truth for user-visible changes.
- Added `ankicli changelog` for terminal access to the latest notes.
- Added `ankicli changelog --all` for the full changelog.

## 0.1.0 - Initial Development

- Established the local-first Anki CLI surface for collection inspection and mutation.
- Added structured JSON output for automation and readable human output for direct terminal use.
- Added profile, backend, backup, sync, note, card, tag, media, import, export, study, and catalog
  command groups.
