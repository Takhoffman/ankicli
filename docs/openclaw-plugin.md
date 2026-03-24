# OpenClaw Plugin Compatibility

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
