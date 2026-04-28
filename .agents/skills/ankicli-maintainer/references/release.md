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

## Proper release sequence

For a normal prepared-release PR, do this order:

1. merge the release-prep PR into `main`
2. update the local primary checkout to `origin/main`
3. rerun release-state preflight for the exact version and tag
4. clean up stale release/tag state only if the operator explicitly approved the exact targets
5. create an annotated tag on the verified `main` commit
6. push only the release tag
7. watch the release workflow to completion
8. verify GitHub Release assets, checksums, installers, docs, and optional PyPI state
9. draft release announcement copy after the shipped surfaces are confirmed

Suggested command shape:

```bash
gh pr merge <release-pr> --squash --delete-branch --match-head-commit <head-sha>
git fetch origin --tags
git switch main
git pull --ff-only origin main
git status --short
rg -n '^version = ' pyproject.toml
git ls-remote --tags origin 'refs/tags/vX.Y.Z'
gh release view vX.Y.Z --repo Takhoffman/ankicli
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
gh run list --repo Takhoffman/ankicli --workflow release --limit 5
gh run watch <run-id> --repo Takhoffman/ankicli --exit-status
gh release view vX.Y.Z --repo Takhoffman/ankicli --json name,tagName,url,assets
```

Never push `main` as part of this sequence. The only push after merge should be the release tag.

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

## Release announcement drafts

Draft social copy only after the release exists and assets are verified, unless the operator asks
for preview copy. Keep it factual, compact, and tied to user-visible value.

Prepare two or three formats instead of one final post:

- Short ship note:
  `ankicli vX.Y.Z is out: <primary user-visible change>. Also includes <secondary change> and
  <reliability/installer/docs note>. <release-url>`
- Contributor thanks:
  `ankicli vX.Y.Z is live. This release improves <area>, hardens <area>, and tightens <area>.
  Thanks @handle for the PRs behind this one. <release-url>`
- Maintainer-focused:
  `Released ankicli vX.Y.Z with safer release automation, stronger installer validation, and a
  more deterministic test/release path. Useful if you run Anki workflows from the terminal.
  <release-url>`

For Twitter/X-style drafts:

- keep under 280 characters unless the operator asks for a thread
- include the release URL placeholder if the real URL is not verified yet
- use public handles only when the operator supplied them or the PR/release uses them publicly
- do not invent benchmarks, adoption claims, or compatibility promises
