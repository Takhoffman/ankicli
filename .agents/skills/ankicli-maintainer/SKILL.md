---
name: ankicli-maintainer
description: Use when an agent is helping maintain ankicli itself: releasing versions, validating packaging, checking installer and site contracts, and coordinating maintainer-facing repo workflows. Start by clarifying which maintainer task the operator wants. Prefer a guided workflow over assuming release intent.
---

Use this skill when the task is about maintaining `ankicli` as a product and repository, not when using the CLI against an Anki collection.

## Core behavior

1. Start as a guided maintainer workflow.
2. If the operator has not named the task clearly, ask what maintainer workflow they want.
3. Offer concise maintainer choices in plain language, not internal jargon.
4. Do not assume a release is wanted just because versioning, packaging, or GitHub is mentioned.
5. Read the narrowest reference for the selected workflow before taking action.

## Initial routing

Use a short prompt like:

- "What do you want to do with ankicli maintenance right now: prepare a release, validate packaging, inspect release automation, or something else?"

If the operator already asked for release work, skip the routing question and go straight to the release reference.

## Baseline checks

Before substantive maintainer work, inspect:

- current git branch and worktree state
- current package version in `pyproject.toml`
- relevant workflow files when the task touches CI, Pages, or releases

## Read the right reference

- Read `references/release.md` for release prep, tagged release flow, installers, standalone artifacts, and optional PyPI publishing.

## Current scope

Right now, the only fully detailed maintainer reference is release work.

If the operator asks for a maintainer workflow that is not documented yet:

1. say the maintainer skill currently has first-class release guidance
2. continue the task normally if it is still safe to do so
3. extend the maintainer skill later if that workflow becomes recurring
