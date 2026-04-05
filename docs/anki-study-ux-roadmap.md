# Anki Study UX End-State Roadmap

This document tracks the long-term architecture for study-first Anki usage in `ankicli` and the OpenClaw plugin.

## Goal

Make the best LLM-facing experience for studying decks while preserving a precise low-level API for expert and debug usage.

## Architectural Direction

### 1. `ankicli` is the source of truth

`ankicli` should own:

- operation metadata
- workflow metadata
- backend capability truth
- runtime support resolution
- study-session state
- error semantics

The OpenClaw plugin should adapt that contract, not redefine it.

### 2. Two product surfaces

Primary workflow surface:

- `anki_collection_status`
- `anki_search`
- `anki_note_manage`
- `anki_deck_manage`
- `anki_study_start`
- `anki_study_card_details`
- `anki_study_reveal`
- `anki_study_grade`
- `anki_study_summary`

Expert surface:

- low-level legacy tools
- `ankicli` passthrough

### 3. Study is first-class

Study should remain a first-class workflow with its own local session state:

- scope
- queue
- front-side card-details state before reveal
- revealed answer state after reveal
- grade history
- progress summary

The Anki collection is the source of truth for collection data.
The study session is the source of truth for the active tutoring workflow.

## Shipped In This Refactor

- authoritative capability/workflow catalog in `src/ankicli/app/catalog.py`
- backend capability resolution derived from that catalog
- `catalog export` CLI command for structured metadata + runtime support
- first-class `study` CLI commands and local session persistence
- OpenClaw plugin primary workflow tool surface
- plugin-published skills for study, management, authoring, and diagnostics
- `before_prompt_build` dynamic context sourced from `ankicli catalog export`

## Remaining End-State Work

### Near-term

1. Generate more plugin metadata from the exported catalog instead of duplicating labels and descriptions in JS.
2. Add action-level support metadata so workflow tools can explain partial backend support more precisely.
3. Add more focused tests around plugin-side catalog consumption and prompt-context generation.

### Medium-term

1. Add richer study primitives:
   - due-card presets
   - leech/failure introspection
   - deck-specific study plans
   - note-to-explanation workflows
   - presentation-derived `front_card_text` / `back_card_text` as the preferred
     LLM-facing study text surface while keeping `media` unchanged
2. Improve prompt guidance generation from catalog/workflow metadata instead of maintaining static skill prose by hand.
3. Add structured workflow docs generation from the catalog.

### Long-term

1. Replace remaining JS tool registration duplication with generated bindings from `ankicli catalog export`.
2. Add optional backend-aware scheduling mutation for study grading where the backend truly supports it.
3. Add per-session adaptive tutoring metadata such as weak-topic summaries and repeated-miss analysis.
4. Make CLI, plugin, docs, and skills all derive from one versioned workflow contract.

## Non-Goals

- Hiding low-level APIs from expert users
- Replacing precise collection-management commands with vague natural-language-only behavior
- Encoding backend truth in plugin prose or prompt hooks
