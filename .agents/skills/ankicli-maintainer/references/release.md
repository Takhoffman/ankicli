# Tagged Release Workflow

Use this reference once the operator explicitly wants to ship a real release, not just inspect readiness.

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

## Release surfaces to verify

Do not treat a pushed tag as success. Confirm the shipped surfaces:

- GitHub Release exists
- expected release assets exist
- checksums file exists
- installer scripts resolve current assets
- site install docs still match the real release contract

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
- do not publish artifacts when validation or distribution checks are red
- do not update docs install commands ad hoc without verifying the installer contract
- do not conflate PyPI success with release success
- do not change executable name and package name casually
