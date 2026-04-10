# ankicli OpenClaw Plugin

This package is a thin OpenClaw adapter over `ankicli --json`.

Status: experimental/internal. The primary public path today is the standalone
skill installer:

```bash
ankicli skill install --target openclaw
```

Use the plugin only when you are intentionally working on the richer OpenClaw
adapter, not for normal public onboarding yet.

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

## Experimental Local Plugin Install Into OpenClaw

From an OpenClaw checkout or install:

```bash
openclaw plugins install -l ~/ankicli/integrations/openclaw-plugin
```

If you are testing against an OpenClaw source checkout and a `dev` profile, the
practical setup we needed was:

1. Set `tools.profile` to `full` in `~/.openclaw-dev/openclaw.json`.
2. Enable the `/plugins` chat command if you want in-UI debugging:
   `"commands": { "plugins": true }`
3. Point the plugin at a real collection path:
   `"plugins.entries.ankicli.config.collectionPath": "/Users/<user>/Library/Application Support/Anki2/User 1/collection.anki2"`
4. Stop the launchd-managed gateway before starting the branch manually:
   `openclaw --profile dev gateway stop`
5. Refresh the UI and start a new chat after plugin/profile changes so the
   session does not keep a stale tool list.

The fuller troubleshooting guide lives in
[openclaw-plugin.md](../../docs/openclaw-plugin.md).

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

See [openclaw-plugin.md](../../docs/openclaw-plugin.md) for
the stable command and JSON contract this adapter expects, and
[anki-study-ux-roadmap.md](../../docs/anki-study-ux-roadmap.md)
for the longer-term end-state plan. Generated reference output lives at
[anki-catalog-reference.md](../../docs/anki-catalog-reference.md).
