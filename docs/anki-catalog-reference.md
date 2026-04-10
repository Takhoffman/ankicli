# Generated Anki Catalog Reference

Schema version: `2026-03-27.2`

This file is generated from `ankicli.app.catalog`.

## Workflows

- `study.start` [primary]: Create a tutor-style study session from a deck, preset, or query.
- `study.next` [primary]: Return the current or next card from the active study session.
- `study.details` [primary]: Return the current study card details from the front side of the active session.
- `study.reveal` [primary]: Reveal the answer and back side for the current study card.
- `study.grade.local` [primary]: Record a local tutor-session grade without mutating Anki scheduling.
- `study.grade.backend` [primary]: Record a study grade back into backend scheduling when supported.
- `study.summary` [primary]: Summarize the current study session, misses, and progress.
- `study.weak_cards` [primary]: Summarize repeatedly missed cards from the current study session.
- `study.plan` [primary]: Recommend the next study slice based on deck scope and misses.
- `search.unified` [primary]: Search notes or cards with preview-oriented defaults.
- `note.manage` [primary]: Inspect or mutate notes through one intent-oriented surface.
- `deck.manage` [primary]: Inspect or mutate decks through one intent-oriented surface.
- `collection.status` [primary]: Summarize backend and collection readiness for study or management.
- `operation.invoke` [expert]: Expert escape hatch for arbitrary low-level ankicli operations.

## Plugin Tools

- `anki_collection_status` [primary]: Summarize collection readiness for study or management through ankicli.
- `anki_search` [primary]: Search notes or cards with preview-oriented defaults through ankicli.
- `anki_note_manage` [primary]: Inspect or mutate notes through one intent-oriented ankicli surface.
- `anki_deck_manage` [primary]: Inspect or mutate decks through one intent-oriented ankicli surface.
- `anki_study_start` [primary]: Create a local tutor-style study session from a deck, preset, or query.
- `anki_study_next` [primary]: Return the current or next study card from the active local tutor session.
- `anki_study_card_details` [primary]: Return the current study card details from the front side of the active session.
- `anki_study_reveal` [primary]: Reveal the answer and back side for the current study card.
- `anki_study_grade` [primary]: Record a local study grade and advance the active tutor session.
- `anki_study_summary` [primary]: Summarize progress for the active local tutor session.
- `anki_collection_info` [legacy]: Fetch high-level collection metadata and counts through ankicli.
- `anki_auth_status` [legacy]: Report whether sync credentials are available through ankicli.
- `anki_sync_status` [legacy]: Check whether the configured collection requires sync through ankicli.
- `anki_sync_run` [legacy]: Run the normal collection sync flow through ankicli.
- `anki_deck_list` [legacy]: List decks in the configured collection through ankicli.
- `anki_model_list` [legacy]: List note types in the configured collection through ankicli.
- `anki_search_notes` [legacy]: Search note ids with an Anki-style query through ankicli.
- `anki_search_cards` [legacy]: Search card ids with an Anki-style query through ankicli.
- `anki_note_get` [legacy]: Fetch one normalized note record by id through ankicli.
- `anki_note_add` [legacy]: Add a note through ankicli with optional dry-run safety.
- `anki_note_update` [legacy]: Update note fields through ankicli with optional dry-run safety.
- `anki_card_suspend` [legacy]: Suspend a card through ankicli with explicit yes/dry-run flags.
- `anki_card_unsuspend` [legacy]: Unsuspend a card through ankicli with explicit yes/dry-run flags.
- `ankicli` [expert]: Run a freeform ankicli command as a thin JSON-mode passthrough.

## Backend Workflow Support

- `python-anki` supports 13 workflows: study.start, study.next, study.details, study.reveal, study.grade.local, study.summary, study.weak_cards, study.plan, search.unified, note.manage, deck.manage, collection.status, operation.invoke
- `ankiconnect` supports 13 workflows: study.start, study.next, study.details, study.reveal, study.grade.local, study.summary, study.weak_cards, study.plan, search.unified, note.manage, deck.manage, collection.status, operation.invoke

## Workflow Actions

- `study.start` actions: study.start.default
- `search.unified` actions: search.notes, search.cards
- `note.manage` actions: get, fields, add, update, delete, add_tags, remove_tags, move_deck
- `deck.manage` actions: list, get, stats, create, rename, delete, reparent

## Backend Action Support

- `python-anki` `study.start` supported: study.start.default; unsupported: none
- `python-anki` `search.unified` supported: search.notes, search.cards; unsupported: none
- `python-anki` `note.manage` supported: get, fields, add, update, delete, add_tags, remove_tags, move_deck; unsupported: none
- `python-anki` `deck.manage` supported: list, get, stats, create, rename, delete, reparent; unsupported: none
- `ankiconnect` `study.start` supported: study.start.default; unsupported: none
- `ankiconnect` `search.unified` supported: search.notes, search.cards; unsupported: none
- `ankiconnect` `note.manage` supported: get, fields, add, update, delete, add_tags, remove_tags, move_deck; unsupported: none
- `ankiconnect` `deck.manage` supported: list, get, stats, create, rename, delete, reparent; unsupported: none
- `ankiconnect` media operations supported: list, check, attach, resolve-path; unsupported: orphaned
- `ankiconnect` still does not support auth, sync, or backup flows; use `python-anki` for those

## Deck Stats Contract

- `deck stats` returns `id`, `name`, `note_count`, `card_count`, `due_count`, `new_count`, `learning_count`, and `review_count`.

## Study Payload Contract

- Study responses expose `current_card.study_view`, `current_card.media`, and `current_card.raw_fields`.
- `study details` and compatible reveal-style outputs may also emit a top-level `kind: "canvas"` payload so OpenClaw can render the current card inline while preserving structured card fields.
- `study_view` contains `rendered_front_html`, `rendered_back_html`, `rendered_front_telegram_html`, `rendered_back_telegram_html`, `front_card_text`, `back_card_text`, `prompt`, `answer`, `supporting`, and `raw_fields_available`.
- `rendered_front_html` is returned when backend presentation is available; `rendered_back_html` is returned by `study details` and withheld on prompt-only study reads.
- `rendered_front_telegram_html` is a best-effort Telegram-safe projection of rendered front HTML; `rendered_back_telegram_html` is returned by `study details` and withheld on prompt-only study reads.
- `front_card_text` is always available when the prompt side can be normalized to text; `back_card_text` is returned by `study details` and withheld on prompt-only study reads.
- `media.audio[]` and `media.images[]` entries include `tag`, `path`, `exists`, and `error_code`.

## Media And Provider Errors

- `MEDIA_REFERENCE_UNRESOLVED`: A card referenced media, but the local media root or filename could not be resolved.
- `MEDIA_FILE_MISSING`: A media reference resolved to a local path, but the file was missing on disk.
- `MEDIA_PROVIDER_UNCONFIGURED`: A downstream media helper needs an external provider that is not configured.
- `MEDIA_PROVIDER_QUOTA_EXCEEDED`: A downstream media helper exhausted the configured provider quota.
- `MEDIA_INPUT_INVALID`: A media tag or helper input was malformed or unsuitable for processing.
