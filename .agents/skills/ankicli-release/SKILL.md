---
name: ankicli-release
description: Teach the agent how to prepare and validate ankicli release and packaging work.
---

Prefer `ankicli-maintainer` for new maintainer-facing workflows.

This focused skill remains the narrow release-only variant.

Treat releases as packaging-sensitive changes. Confirm version, build, distribution tests,
standalone artifacts, installer checksum behavior, and tag-triggered GitHub Release publishing
before recommending a release.

Prefer:

- `uv sync --extra dev --frozen`
- `uv run ruff check .`
- `uv run pytest -m "unit or smoke"`
- `uv build`
- `uv run pytest -m distribution`
- `uv run python scripts/build_release_artifact.py --target <target> --version <version>`

## Rules

1. Start with the current version in `pyproject.toml` and the installed command name: the PyPI distribution is `anki-agent-toolkit`, while the executable is `ankicli`.
2. Treat `uv.lock` as mandatory. If dependency resolution changes, update and include the lockfile in the same release-prep change.
3. Run the smallest useful release gate first, then broaden to packaging checks: `uv run pytest -m "unit or smoke"`, `uv build`, and `uv run pytest -m distribution`.
4. For standalone release artifacts, use `scripts/build_release_artifact.py` and target only supported release IDs: `darwin-x64`, `darwin-arm64`, `linux-x64`, and `windows-x64`.
5. Verify artifact names and checksums match the contract in `ankicli.app.releases` before publishing or advising a manual upload.
6. Treat installer checksum mismatch, missing executable payloads, or failed distribution tests as release-blocking.
7. GitHub Releases are tag-triggered from `v*`; do not push a release tag or publish artifacts unless the operator explicitly asks for that release action.

## Anti-Patterns

- Do not describe an editable install, fixture integration run, or smoke test alone as proof that a release artifact is valid.
- Do not change the PyPI distribution name or executable name casually during release prep.
- Do not upload or publish artifacts when build, checksum, or distribution validation is incomplete.
