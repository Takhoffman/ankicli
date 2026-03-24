# ankicli OpenClaw Plugin

This package is a thin OpenClaw adapter over `ankicli --json`.

It lives in the `ankicli` repo so the Python CLI and the plugin-facing contract
stay owned together. The plugin does not reimplement Anki behavior; it shells
out to `ankicli` and preserves the normalized JSON contract.

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
