# Diagnostics

Use this reference when the task is to diagnose ankicli runtime, backend, collection, profile, or capability issues.

## Prefer

- `ankicli --json doctor env`
- `ankicli --json doctor backend`
- `ankicli --json doctor capabilities`
- `ankicli --json collection info`

## Rules

1. Confirm runtime, backend, and collection readiness first.
2. Differentiate missing setup from unsupported behavior.
3. If one backend fails, check whether the alternate backend is intended and supported before retrying a write.
4. Preserve structured error codes and capability reasons verbatim instead of paraphrasing them into vague summaries.

## Common patterns

- Missing collection target: resolve setup or workspace targeting first.
- Runtime mismatch: inspect doctor output before retrying collection commands.
- Capability gap: explain that it is unsupported instead of pretending there is a fallback.
