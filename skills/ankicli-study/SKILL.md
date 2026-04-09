---
name: ankicli-study
description: Teach the agent how to run tutor-style Anki study sessions through ankicli.
---

Use the primary study workflows first and keep tutoring separate from collection mutation.

Prefer:

- `ankicli --json ... collection info`
- `ankicli --json ... study start ...`
- `ankicli --json study details`
- `ankicli --json study reveal`
- `ankicli --json study grade --rating ...`
- `ankicli --json study summary`

## Rules

1. Start with the narrowest deck or query scope that matches the learner goal.
2. Use `study details` as the default current-card read for the front side, and use `study reveal` when the user asks for the answer or back side.
3. Present study cards like Anki by default: focus on the prompt and front-side clues first, and do not volunteer the answer until after `study reveal`.
4. Present grading choices in this order when guiding the learner: 1. Again 2. Hard 3. Good 4. Easy.
5. Treat study-session state as the tutoring source of truth unless the workflow explicitly says it writes back to Anki.
6. Explain misses in study terms and patterns instead of dumping raw database fields.

## Anti-Patterns

- Do not default to low-level note or deck mutations when the user asked to study.
- Do not skip `study reveal` when the user asks for the answer or when grading requires a revealed card.
