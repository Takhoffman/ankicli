# Study

Use this reference when the task is to tutor, review, reveal, grade, or summarize an Anki study session through ankicli.

## Prefer

- `ankicli --json collection info`
- `ankicli --json study start ...`
- `ankicli --json study details`
- `ankicli --json study reveal`
- `ankicli --json study grade --rating ...`
- `ankicli --json study summary`

## Rules

1. Start with the narrowest deck or query scope that matches the learner goal.
2. Use `study details` as the default current-card read for the front side.
3. Use `study reveal` when the user asks for the answer or when grading requires the back side.
4. Present grading choices in this order: 1. Again 2. Hard 3. Good 4. Easy.
5. Treat study-session state as the tutoring source of truth unless the workflow explicitly says it writes back to Anki scheduling.
6. Explain mistakes in learning terms and patterns instead of dumping raw card fields.

## Anti-patterns

- Do not default to low-level note or deck mutation when the user asked to study.
- Do not skip `study reveal` when the answer has to be shown.
