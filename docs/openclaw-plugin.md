# OpenClaw Plugin Compatibility

`ankicli` is the source of truth for Anki behavior. The OpenClaw plugin should
adapt `ankicli --json` output, not reimplement Anki logic in TypeScript.

## Supported Plugin-Facing Commands

The initial OpenClaw plugin surface may call these commands:

- `ankicli collection info --json`
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
- `ANKICONNECT_URL`

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
