# Tagged Release Workflow

Use this reference once the operator explicitly wants to ship a real release, not just inspect readiness.

## Tagged release flow

Use this only when the operator explicitly wants to ship.

1. confirm the version to release
2. ensure the working tree is clean
3. ensure validation passed
4. create or verify the release commit
5. rerun release-state preflight for the exact tag
6. create a tag of the form `vX.Y.Z`
7. push the tag
8. confirm the release workflow ran and assets exist

The package version uses `X.Y.Z`.
The git tag uses `vX.Y.Z`.

## Release-state cleanup

Deleting GitHub Releases or remote tags is destructive. Only do it when the operator explicitly
approves the exact targets in chat.

When cleanup is approved, prefer this order for a bad published release/tag pair:

```bash
gh release delete <bad-tag> --repo Takhoffman/ankicli --yes
git push origin :refs/tags/<bad-tag>
git tag -d <bad-tag>
```

Before running those commands, restate:

- release URL
- release name
- release tag
- asset count
- tag SHA
- why it is stale or unsafe to keep

Never delete `vX.Y.Z` just because a release failed; first confirm whether the release should be
repaired, rerun, or removed.

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
- stale release or tag state for the intended version
- GitHub Release name/tag mismatch
- empty GitHub Release for a non-empty published version
- failed release workflow for a tag that is still present
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
