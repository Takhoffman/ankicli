---
name: anki-study
description: Teach the agent how to run tutor-style Anki study sessions.
---

Use the primary study workflows first and keep tutoring separate from collection mutation.

Prefer:

- `anki_collection_status`
- `anki_study_start`
- `anki_study_card_details`
- `anki_study_reveal`
- `anki_study_grade`
- `anki_study_summary`

## Rules

1. Start with the narrowest deck or scope preset that matches the user goal, and compare due, new, learning, and review counts when the user needs help picking a deck.
2. Use anki_study_card_details as the default current-card read for the front side, and use anki_study_reveal when the user asks to reveal the answer or back side.
3. Present study cards like Anki by default: focus on the prompt, question, and front-side clues first, and do not volunteer the answer or back-side content until after anki_study_reveal; include media in the same response when it helps the learner without spoiling the answer.
4. Present grading choices as a numbered list in this order when you guide the user: 1. Again 2. Hard 3. Good 4. Easy.
5. Treat study-session state as the tutoring source of truth unless the workflow explicitly says it writes back to Anki, and only grade after the current card has been revealed.
6. Prefer curated study_view output over raw_fields, and only fall back to raw fields when the curated answer is missing or the user asks for full detail.
7. When current_card.view is present, rely on the returned canvas metadata to show the card in Control UI, use current_card.tutoring_summary for reasoning, and use current_card.study_media for native Discord or Telegram media delivery; if media resolution fails, name the structured error code instead of inventing a generic failure.
8. Explain misses in study terms and patterns instead of dumping raw database fields.

## Anti-Patterns

- Do not default to low-level tools when the user asked to study.
- Do not mutate notes or decks unless explicitly asked.
- Do not skip anki_study_reveal when the user asks for the answer or when grading requires a revealed card.
