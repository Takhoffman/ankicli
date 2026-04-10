# OpenClaw Plugin Compatibility

Status: experimental/internal. The current public OpenClaw path is still the
standalone skill installer:

```bash
ankicli skill install --target openclaw
```

Use this page when you are intentionally developing or debugging the richer
OpenClaw plugin adapter.

`ankicli` is the source of truth for Anki behavior. The OpenClaw plugin should
adapt `ankicli --json` output, not reimplement Anki logic in TypeScript.

## Supported Plugin-Facing Commands

The initial OpenClaw plugin surface may call these commands:

- `ankicli collection info --json`
- `ankicli auth status --json`
- `ankicli sync status --json`
- `ankicli sync run --json`
- `ankicli deck list --json`
- `ankicli model list --json`
- `ankicli search notes --query <query> --json`
- `ankicli search cards --query <query> --json`
- `ankicli note get --id <id> --json`
- `ankicli note add --deck <deck> --model <model> --field Name=Value --json`
- `ankicli note update --id <id> --field Name=Value --json`
- `ankicli card suspend --id <id> --json`
- `ankicli card unsuspend --id <id> --json`

The plugin should pass global CLI configuration only through flags and
environment:

- `--backend`
- `--collection`
- `--profile`
- `ANKICONNECT_URL`

The plugin should not expose:

- `backup restore`
- profile-admin flows
- direct credential capture or `auth login`/`auth logout`

## Local Dev Install Into OpenClaw

This is the shortest known-good local workflow for a source checkout of
OpenClaw plus a source checkout of `ankicli`.

Assumptions:

- OpenClaw checkout: `~/openclaw3`
- ankicli checkout: `~/ankicli`
- OpenClaw profile: `dev`

### 1. Link the local plugin into the OpenClaw checkout

```bash
cd ~/openclaw3
pnpm exec node openclaw.mjs --profile dev plugins install -l ~/ankicli/integrations/openclaw-plugin
```

Verify:

```bash
cd ~/openclaw3
pnpm exec node openclaw.mjs --profile dev plugins inspect ankicli
```

Expected:

- `Status: loaded`
- tool list includes `anki_study_card_details`, `anki_study_reveal`, and `anki_study_grade`

### 2. Make sure the OpenClaw tool profile is not restricting plugin tools

For the `dev` profile, `tools.profile` should be `full`, not `coding`, or the
session may keep only the generic coding surface.

Config file:

- `~/.openclaw-dev/openclaw.json`

Relevant shape:

```json
{
  "tools": {
    "profile": "full"
  }
}
```

After changing it, restart the gateway.

### 3. Enable `/plugins` in the OpenClaw profile if you want the slash command in chat

This is optional for runtime loading, but helpful for debugging from the web UI.

```json
{
  "commands": {
    "plugins": true
  }
}
```

### 4. Set `collectionPath` in the plugin config

If the plugin loads but study tools fail with `COLLECTION_REQUIRED`, point the
plugin at a real Anki collection in the OpenClaw profile config.

Relevant shape:

```json
{
  "plugins": {
    "entries": {
      "ankicli": {
        "enabled": true,
        "config": {
          "collectionPath": "/Users/<user>/Library/Application Support/Anki2/User 1/collection.anki2"
        }
      }
    }
  }
}
```

On macOS, the best default candidate is usually:

- `/Users/<user>/Library/Application Support/Anki2/User 1/collection.anki2`

If needed, find candidates with:

```bash
find "$HOME/Library/Application Support/Anki2" -maxdepth 3 \( -name collection.anki2 -o -name collection.anki21 \)
```

### 5. Stop launchd before running the branch manually

If `pnpm gateway:dev` keeps printing `already running under launchd`, stop the
service-managed gateway first:

```bash
cd ~/openclaw3
pnpm exec node openclaw.mjs --profile dev gateway stop
```

If port `19001` is still busy after that, a stray process may still be running.
Check:

```bash
lsof -nP -iTCP:19001 -sTCP:LISTEN
```

### 6. Run OpenClaw from the source checkout

Foreground gateway:

```bash
cd ~/openclaw3
pnpm gateway:dev
```

Optional Vite UI:

```bash
cd ~/openclaw3
pnpm ui:dev
```

Useful local URLs:

- dashboard/control UI: `http://127.0.0.1:19001/` when using the launchd-managed `dev` service
- foreground local branch run: `http://127.0.0.1:18789/`
- Vite UI dev server: `http://localhost:5173/`

### 7. Refresh or start a new chat session after tool/profile changes

The web UI can hold stale session tool availability after:

- changing `tools.profile`
- installing or relinking the plugin
- changing plugin config
- restarting the gateway

If the agent says the Anki workflows exist in prompt context but are not
callable in the session, refresh the UI and start a new chat.

## Known Failure Modes

### Plugin listed in config but not actually loaded

Symptom:

- `plugins.entries.ankicli.enabled` exists in config
- but `openclaw plugins inspect ankicli` says `Plugin not found`

Cause:

- the config entry survived, but the plugin bundle/link is missing

Fix:

- rerun `openclaw plugins install -l /path/to/openclaw-plugin`

### Plugin loads, but Anki tools are not callable in the web session

Symptom:

- `plugins inspect ankicli` shows tools
- but the agent says no Anki tools are callable

Most likely causes:

- `tools.profile` is too restrictive
- the chat session is stale and needs to be recreated

### Study tools return `COLLECTION_REQUIRED`

Symptom:

- `anki_study_start` is callable
- but returns `COLLECTION_REQUIRED`

Cause:

- plugin config has no `collectionPath`, and no equivalent workspace/profile
  path reached the CLI

Fix:

- set `plugins.entries.ankicli.config.collectionPath`

### Raw `[canvas ...]` text appears instead of an inline render

Symptom:

- the assistant bubble shows literal shortcode text

Cause:

- either canvas rendering is not active on that path, or the emitted shortcode
  shape is not supported

Known-good inline HTML form:

```text
[canvas content_type="html" title="Status"]
<div>hello</div>
[/canvas]
```

## JSON Envelope Contract

Every plugin-facing command should be treated as returning one of these stable
envelopes:

Success:

```json
{
  "ok": true,
  "backend": "python-anki",
  "data": {},
  "meta": {}
}
```

Error:

```json
{
  "ok": false,
  "backend": "python-anki",
  "error": {
    "code": "COLLECTION_REQUIRED",
    "message": "collection path required",
    "details": {}
  },
  "meta": {}
}
```

The plugin should preserve `data` shapes instead of inventing a second schema.

## Stable Success Fields

- `collection info`
  - `collection_name`
  - `collection_path`
  - `exists`
  - `backend_available`
  - `note_count`
  - `card_count`
  - `deck_count`
  - `model_count`
- `auth status`
  - `authenticated`
  - `credential_backend`
  - `credential_present`
  - `backend_available`
  - `supports_sync`
- `sync status`
  - `required`
  - `required_bool`
  - `performed`
  - `direction`
  - `changes`
  - `warnings`
  - `conflicts`
- `sync run`
  - `required`
  - `performed`
  - `direction`
  - `changes`
  - `warnings`
  - `conflicts`
- `deck list`
  - `items`: array of `{id, name}`
- `model list`
  - `items`: array of `{id, name}`
- `search notes`
  - `items`: array of `{id}`
  - `query`
  - `limit`
  - `offset`
  - `total`
- `search cards`
  - `items`: array of `{id}`
  - `query`
  - `limit`
  - `offset`
  - `total`
- `note get`
  - `id`
  - `model`
  - `fields`
  - `tags`
- `note add`
  - `id`
  - `deck`
  - `model`
  - `fields`
  - `tags`
  - `dry_run`
- `note update`
  - `id`
  - `model`
  - `fields`
  - `tags`
  - `dry_run`
- `card suspend`
  - `id`
  - `suspended`
  - `dry_run`
- `card unsuspend`
  - `id`
  - `suspended`
  - `dry_run`

Backend-specific extras may appear, but the plugin should not depend on them as
required contract fields.

## Stable Error Codes

The plugin should preserve these codes when available:

- `BACKEND_UNAVAILABLE`
- `BACKEND_OPERATION_UNSUPPORTED`
- `COLLECTION_REQUIRED`
- `COLLECTION_NOT_FOUND`
- `COLLECTION_OPEN_FAILED`
- `VALIDATION_ERROR`
- `NOTE_NOT_FOUND`
- `CARD_NOT_FOUND`
- `DECK_NOT_FOUND`
- `MODEL_NOT_FOUND`
- `UNSAFE_OPERATION`
- `AUTH_REQUIRED`
- `AUTH_INVALID`
- `AUTH_STORAGE_UNAVAILABLE`
- `SYNC_UNAVAILABLE`
- `SYNC_CONFLICT`
- `SYNC_IN_PROGRESS`
- `SYNC_FAILED`
- `BACKUP_NOT_FOUND`
- `BACKUP_RESTORE_UNSAFE`
- `PROFILE_NOT_FOUND`
- `PROFILE_RESOLUTION_FAILED`

Useful stable `error.details` keys when present:

- `note_id`
- `card_id`
- `deck_name`
- `model_name`
- `backend`
- `operation`

## Compatibility Expectation

The commands and fields above are the stable plugin-facing API for the initial
OpenClaw adapter. Future CLI changes should preserve these JSON envelopes,
fields, and error codes or be treated as compatibility changes for the plugin.
