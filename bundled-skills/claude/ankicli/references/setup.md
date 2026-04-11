# Setup

Use this reference when the task is about installation, first-run configuration, profile targeting, auth setup, or installing the ankicli umbrella skill into an agent home.

## Baseline setup flow

1. Run `ankicli --version`.
2. Run `ankicli configure`.
3. Run `ankicli --json doctor env`.
4. Run `ankicli --json doctor backend`.
5. Run `ankicli --json profile list`.

## Workspaces

- Human-facing workspace config lives under `~/.ankicli/workspaces/<name>/config.json`.
- The active workspace name is stored separately and selects the default target for routine commands.
- Prefer `ankicli configure` or `ankicli workspace set --profile "User 1"` over repeating `--profile` on every command.

## Skill installation

- Install the umbrella skill with `ankicli skill install --target codex`, `--target claude`, or `--target openclaw`.
- `ankicli skill install --target all` installs into every detected skill home.
- Use `--path` only for custom agent homes.

## Auth

- `ankicli auth login` requires a real collection target because the python-anki sync flow works through the collection runtime.
- Prefer saving a workspace target first, then run `ankicli auth status` and `ankicli auth login`.

## Default safety rule

If setup is incomplete, stop and explain the missing requirement instead of guessing a collection path or sync state.
