---
name: anki-diagnostics
description: Teach the agent how to diagnose backend, collection, and capability issues.
---

Treat structured ankicli errors as authoritative and distinguish setup from unsupported behavior.

Prefer:

- `anki_collection_status`
- `ankicli`

## Rules

1. Confirm backend and collection readiness first.
2. Differentiate missing setup from backend operation support gaps.
3. If one backend fails, check whether the alternate backend is intended and supported.
4. Use the media error taxonomy codes verbatim when media resolution or provider setup is the problem.

