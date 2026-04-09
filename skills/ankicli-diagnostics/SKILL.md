---
name: ankicli-diagnostics
description: Teach the agent how to diagnose ankicli runtime, backend, collection, and capability issues.
---

Treat structured ankicli errors as authoritative and distinguish setup problems from unsupported behavior.

Prefer:

- `ankicli --json doctor env`
- `ankicli --json doctor backend`
- `ankicli --json doctor capabilities`
- `ankicli --json ... collection info`

## Rules

1. Confirm runtime, backend, and collection readiness first.
2. Differentiate missing setup from backend operation support gaps.
3. If one backend fails, check whether the alternate backend is intended and supported before retrying a write.
4. Preserve structured error codes and capability reasons verbatim instead of paraphrasing them into vague summaries.
