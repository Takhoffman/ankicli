# ankicli OpenClaw Plugin

This package is a thin OpenClaw adapter over `ankicli --json`.

It lives in the `ankicli` repo so the Python CLI and the plugin-facing contract
stay owned together. The plugin does not reimplement Anki behavior; it shells
out to `ankicli` and preserves the normalized JSON contract.

The plugin now exposes two layers:

- primary LLM-facing workflows
- legacy low-level tools plus the expert passthrough

Primary workflow tools:

- `anki_collection_status`
- `anki_search`
- `anki_note_manage`
- `anki_deck_manage`
- `anki_study_start`
- `anki_study_card_details`
- `anki_study_reveal`
- `anki_study_grade`
- `anki_study_summary`

Low-level and expert surfaces remain available:

- legacy low-level tools such as `anki_note_get`, `anki_note_add`, `anki_search_cards`
- `ankicli` passthrough for expert/debug use

`ankicli` is a freeform passthrough tool. It accepts a single `command` string,
omits the executable name, and automatically forces `--json`.

Examples:

- `collection info`
- `search notes --query "deck:Spanish is:due"`
- `note update --id 123 --field Front="hola" --dry-run`

This plugin publishes workflow skills:

- `anki-study`
- `anki-collection-management`
- `anki-note-authoring`
- `anki-diagnostics`

These skill files and the reference catalog doc are generated from the
authoritative Python catalog via:

```bash
uv run python scripts/generate_openclaw_artifacts.py
```

It also uses `before_prompt_build` to append small runtime context sourced from
`ankicli catalog export`, so the agent sees the active backend, supported
primary workflows, backend notes, active study-session details, and any
OpenClaw-rich preview hints without
hardcoding that state in the plugin.

## Local Install Into OpenClaw

From an OpenClaw checkout or install:

```bash
openclaw plugins install -l /Users/thoffman/ankicli/integrations/openclaw-plugin
```

For local config, set plugin config values such as:

- `ankicliPath`
- `backend`
- `toolMode`
- `collectionPath`
- `ankiconnectUrl`

`toolMode` defaults to `llm-default` and supports:

- `llm-default`
  - primary study-oriented workflows plus expert passthrough
- `primary-only`
- `legacy-low-level`
- `expert-only`
- `all`
- compatibility aliases: `passthrough-only`, `curated-only`

See [openclaw-plugin.md](/Users/thoffman/ankicli/docs/openclaw-plugin.md) for
the stable command and JSON contract this adapter expects, and
[anki-study-ux-roadmap.md](/Users/thoffman/ankicli/docs/anki-study-ux-roadmap.md)
for the longer-term end-state plan. Generated reference output lives at
[anki-catalog-reference.md](/Users/thoffman/ankicli/docs/anki-catalog-reference.md).
