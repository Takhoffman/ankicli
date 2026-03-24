# ankicli OpenClaw Plugin

This package is a thin OpenClaw adapter over `ankicli --json`.

It lives in the `ankicli` repo so the Python CLI and the plugin-facing contract
stay owned together. The plugin does not reimplement Anki behavior; it shells
out to `ankicli` and preserves the normalized JSON contract.

Current tool surface includes:

- `anki_collection_info`
- `anki_auth_status`
- `anki_sync_status`
- `anki_sync_run`
- `anki_deck_list`
- `anki_model_list`
- `anki_search_notes`
- `anki_search_cards`
- `anki_note_get`
- `anki_note_add`
- `anki_note_update`
- `anki_card_suspend`
- `anki_card_unsuspend`

## Local Install Into OpenClaw

From an OpenClaw checkout or install:

```bash
openclaw plugins install -l /Users/thoffman/ankicli/integrations/openclaw-plugin
```

For local config, set plugin config values such as:

- `ankicliPath`
- `backend`
- `collectionPath`
- `ankiconnectUrl`

See [openclaw-plugin.md](/Users/thoffman/ankicli/docs/openclaw-plugin.md) for
the stable command and JSON contract this adapter expects.
