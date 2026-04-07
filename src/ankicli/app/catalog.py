"""Authoritative Anki capability, workflow, and plugin-tool catalog."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

CATALOG_SCHEMA_VERSION = "2026-03-27.2"

SURFACE_PRIMARY = "primary"
SURFACE_LEGACY = "legacy"
SURFACE_EXPERT = "expert"

BACKEND_NAMES = ("python-anki", "ankiconnect")

SEARCH_KIND_SCHEMA = {
    "type": "string",
    "enum": ["notes", "cards"],
}
STUDY_RATING_SCHEMA = {
    "type": "string",
    "enum": ["again", "hard", "good", "easy"],
}
STUDY_SCOPE_PRESET_SCHEMA = {
    "type": "string",
    "enum": ["due", "new", "all", "custom"],
}
NOTE_ACTION_SCHEMA = {
    "type": "string",
    "enum": [
        "get",
        "fields",
        "add",
        "update",
        "delete",
        "add_tags",
        "remove_tags",
        "move_deck",
    ],
}
DECK_ACTION_SCHEMA = {
    "type": "string",
    "enum": ["list", "get", "stats", "create", "rename", "delete", "reparent"],
}
FIELDS_SCHEMA = {
    "type": "object",
    "additionalProperties": {"type": "string"},
}
STRING_ARRAY_SCHEMA = {
    "type": "array",
    "items": {"type": "string"},
}


def object_schema(
    properties: dict[str, dict[str, Any]],
    *,
    required: tuple[str, ...] = (),
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
    }
    if required:
        payload["required"] = list(required)
    return payload


@dataclass(frozen=True, slots=True)
class OperationSpec:
    id: str
    description: str
    safety: str
    required_context: tuple[str, ...] = ()
    user_goals: tuple[str, ...] = ()
    output_shape: str = "json-envelope"
    verification_hints: tuple[str, ...] = ()
    clarifying_questions: tuple[str, ...] = ()
    anti_patterns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowActionSpec:
    id: str
    label: str
    description: str
    required_operations: tuple[str, ...] = ()
    requires_any_operation: tuple[str, ...] = ()
    output_shape: str = "json-envelope"
    verification_hints: tuple[str, ...] = ()
    fallback_hint: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowSpec:
    id: str
    label: str
    description: str
    kind: str
    visibility: str
    required_operations: tuple[str, ...] = ()
    requires_any_operation: tuple[str, ...] = ()
    required_context: tuple[str, ...] = ()
    user_goals: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    preferred_usage_order: tuple[str, ...] = ()
    clarifying_questions: tuple[str, ...] = ()
    anti_patterns: tuple[str, ...] = ()
    output_shape: str = "json-envelope"
    verification_hints: tuple[str, ...] = ()
    actions: tuple[WorkflowActionSpec, ...] = ()
    support_mode: str = "derived"


@dataclass(frozen=True, slots=True)
class PluginToolCommandSpec:
    mode: str
    argv: tuple[str, ...] = ()
    action_map: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PluginToolSpec:
    name: str
    label: str
    description: str
    surface: str
    workflow_id: str | None
    parameter_schema: dict[str, Any]
    command: PluginToolCommandSpec
    preferred_for_goals: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SkillSpec:
    slug: str
    name: str
    description: str
    summary: str
    tool_names: tuple[str, ...]
    rules: tuple[str, ...]
    anti_patterns: tuple[str, ...] = ()


MEDIA_ERROR_TAXONOMY: tuple[dict[str, str], ...] = (
    {
        "code": "MEDIA_REFERENCE_UNRESOLVED",
        "description": (
            "A card referenced media, but the local media root or filename "
            "could not be resolved."
        ),
    },
    {
        "code": "MEDIA_FILE_MISSING",
        "description": (
            "A media reference resolved to a local path, but the file was "
            "missing on disk."
        ),
    },
    {
        "code": "MEDIA_PROVIDER_UNCONFIGURED",
        "description": (
            "A downstream media helper needs an external provider that is "
            "not configured."
        ),
    },
    {
        "code": "MEDIA_PROVIDER_QUOTA_EXCEEDED",
        "description": "A downstream media helper exhausted the configured provider quota.",
    },
    {
        "code": "MEDIA_INPUT_INVALID",
        "description": "A media tag or helper input was malformed or unsuitable for processing.",
    },
)


OPERATION_SPECS: tuple[OperationSpec, ...] = (
    OperationSpec("doctor.backend", "Summarize backend health and support.", "read"),
    OperationSpec("doctor.capabilities", "Summarize backend capability matrix.", "read"),
    OperationSpec("doctor.collection", "Run collection diagnostics.", "read", ("collection",)),
    OperationSpec("doctor.safety", "Inspect safety-related configuration.", "read"),
    OperationSpec("backend.test_connection", "Probe backend connectivity.", "read"),
    OperationSpec("profile.list", "List local Anki profiles.", "read"),
    OperationSpec("profile.get", "Inspect one local Anki profile.", "read", ("profile",)),
    OperationSpec("profile.default", "Report the default Anki profile.", "read"),
    OperationSpec(
        "profile.resolve",
        "Resolve a profile to its collection path.",
        "read",
        ("profile",),
    ),
    OperationSpec("auth.status", "Inspect sync credential state.", "read"),
    OperationSpec("auth.login", "Store sync credentials.", "write", user_goals=("sync",)),
    OperationSpec("auth.logout", "Delete sync credentials.", "write", user_goals=("sync",)),
    OperationSpec("backup.status", "Inspect backup availability.", "read", ("collection",)),
    OperationSpec("backup.list", "List backups for a collection.", "read", ("collection",)),
    OperationSpec("backup.create", "Create a backup for a collection.", "write", ("collection",)),
    OperationSpec("backup.get", "Inspect one backup.", "read", ("collection",)),
    OperationSpec("backup.restore", "Restore a backup.", "write", ("collection",)),
    OperationSpec(
        "collection.info",
        "Inspect collection metadata and counts.",
        "read",
        ("collection",),
        verification_hints=("Re-run collection info after configuration changes.",),
    ),
    OperationSpec("collection.stats", "Inspect collection stats.", "read", ("collection",)),
    OperationSpec("collection.validate", "Validate a collection file.", "read", ("collection",)),
    OperationSpec(
        "collection.lock_status",
        "Inspect collection lock sidecar state.",
        "read",
        ("collection",),
    ),
    OperationSpec(
        "deck.list",
        "List decks.",
        "read",
        ("collection",),
        ("deck_management", "study"),
    ),
    OperationSpec("deck.get", "Inspect one deck.", "read", ("collection", "deck")),
    OperationSpec(
        "deck.stats",
        "Inspect deck-level card/note counts.",
        "read",
        ("collection", "deck"),
    ),
    OperationSpec("deck.create", "Create a deck.", "write", ("collection", "deck")),
    OperationSpec("deck.rename", "Rename a deck.", "write", ("collection", "deck")),
    OperationSpec("deck.delete", "Delete a deck.", "write", ("collection", "deck")),
    OperationSpec("deck.reparent", "Reparent a deck.", "write", ("collection", "deck")),
    OperationSpec("model.list", "List note models.", "read", ("collection",)),
    OperationSpec("model.get", "Inspect one note model.", "read", ("collection", "model")),
    OperationSpec("model.fields", "List fields for a note model.", "read", ("collection", "model")),
    OperationSpec(
        "model.templates",
        "List templates for a note model.",
        "read",
        ("collection", "model"),
    ),
    OperationSpec(
        "model.validate_note",
        "Validate note fields against a model.",
        "read",
        ("collection", "model"),
    ),
    OperationSpec("tag.list", "List tags.", "read", ("collection",)),
    OperationSpec("tag.apply", "Apply tags to notes.", "write", ("collection", "note")),
    OperationSpec("tag.remove", "Remove tags from notes.", "write", ("collection", "note")),
    OperationSpec("tag.rename", "Rename a tag.", "write", ("collection", "tag")),
    OperationSpec("tag.delete", "Delete tags.", "write", ("collection", "tag")),
    OperationSpec("tag.reparent", "Reparent tags.", "write", ("collection", "tag")),
    OperationSpec("media.list", "List media entries.", "read", ("collection",)),
    OperationSpec("media.check", "Run media consistency checks.", "read", ("collection",)),
    OperationSpec("media.attach", "Attach media to a collection.", "write", ("collection",)),
    OperationSpec("media.orphaned", "List orphaned media files.", "read", ("collection",)),
    OperationSpec("media.resolve_path", "Resolve a media file path.", "read", ("collection",)),
    OperationSpec(
        "search.notes",
        "Search notes with an Anki query.",
        "read",
        ("collection", "query"),
        ("search", "study"),
    ),
    OperationSpec(
        "search.cards",
        "Search cards with an Anki query.",
        "read",
        ("collection", "query"),
        ("search", "study"),
    ),
    OperationSpec(
        "search.count",
        "Count notes or cards matching a query.",
        "read",
        ("collection", "query"),
    ),
    OperationSpec(
        "search.preview",
        "Preview notes or cards matching a query.",
        "read",
        ("collection", "query"),
    ),
    OperationSpec(
        "export.notes",
        "Export notes as normalized JSON.",
        "read",
        ("collection", "query"),
    ),
    OperationSpec(
        "export.cards",
        "Export cards as normalized JSON.",
        "read",
        ("collection", "query"),
    ),
    OperationSpec("import.notes", "Import notes from normalized JSON.", "write", ("collection",)),
    OperationSpec(
        "import.patch",
        "Patch existing notes from normalized JSON.",
        "write",
        ("collection",),
    ),
    OperationSpec("sync.status", "Inspect sync state.", "read", ("collection",)),
    OperationSpec("sync.run", "Run sync.", "write", ("collection",)),
    OperationSpec("sync.pull", "Run sync pull.", "write", ("collection",)),
    OperationSpec("sync.push", "Run sync push.", "write", ("collection",)),
    OperationSpec(
        "note.get",
        "Inspect one note.",
        "read",
        ("collection", "note"),
        ("search", "study", "note_authoring"),
    ),
    OperationSpec(
        "note.add",
        "Create a note.",
        "write",
        ("collection", "deck", "model"),
        ("note_authoring",),
    ),
    OperationSpec(
        "note.update",
        "Update note fields.",
        "write",
        ("collection", "note"),
        ("note_authoring",),
    ),
    OperationSpec("note.delete", "Delete a note.", "write", ("collection", "note")),
    OperationSpec("note.fields", "Inspect note fields.", "read", ("collection", "note")),
    OperationSpec(
        "note.move_deck",
        "Move a note's cards to another deck.",
        "write",
        ("collection", "note", "deck"),
    ),
    OperationSpec("note.add_tags", "Add tags to a note.", "write", ("collection", "note")),
    OperationSpec("note.remove_tags", "Remove tags from a note.", "write", ("collection", "note")),
    OperationSpec("card.get", "Inspect one card.", "read", ("collection", "card"), ("study",)),
    OperationSpec("card.suspend", "Suspend a card.", "write", ("collection", "card")),
    OperationSpec("card.unsuspend", "Unsuspend a card.", "write", ("collection", "card")),
)

WORKFLOW_SPECS: tuple[WorkflowSpec, ...] = (
    WorkflowSpec(
        id="study.start",
        label="Study Start",
        description="Create a tutor-style study session from a deck, preset, or query.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("search.cards", "card.get", "note.get"),
        required_context=("collection",),
        user_goals=("study",),
        notes=("Creates local tutor-session state.",),
        preferred_usage_order=("collection.status", "study.start", "study.next"),
        clarifying_questions=(
            "Which deck or query should the study session use?",
            "Should the session focus on due, new, all, or a custom query?",
        ),
        anti_patterns=("Do not skip scope selection when the user already named a deck.",),
        verification_hints=("Confirm card_count and scope before continuing.",),
        actions=(
            WorkflowActionSpec(
                id="study.start.default",
                label="Start Study Session",
                description="Start a study session using a deck, preset, or custom query.",
                required_operations=("search.cards", "card.get", "note.get"),
            ),
        ),
    ),
    WorkflowSpec(
        id="study.next",
        label="Study Next",
        description="Return the current or next card from the active study session.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("search.cards", "card.get", "note.get"),
        user_goals=("study",),
        preferred_usage_order=("study.start", "study.details", "study.grade.local"),
    ),
    WorkflowSpec(
        id="study.details",
        label="Study Card Details",
        description=(
            "Return the current study card details from the front side of the active session."
        ),
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("search.cards", "card.get", "note.get"),
        user_goals=("study",),
        preferred_usage_order=("study.start", "study.details", "study.reveal", "study.grade.local"),
    ),
    WorkflowSpec(
        id="study.reveal",
        label="Study Reveal",
        description="Reveal the answer and back side for the current study card.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("search.cards", "card.get", "note.get"),
        user_goals=("study",),
        anti_patterns=("Do not grade a card before reveal.",),
    ),
    WorkflowSpec(
        id="study.grade.local",
        label="Study Grade Local",
        description="Record a local tutor-session grade without mutating Anki scheduling.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("search.cards", "card.get", "note.get"),
        user_goals=("study",),
        notes=("This mode is always safe and local-only.",),
    ),
    WorkflowSpec(
        id="study.grade.backend",
        label="Study Grade Backend",
        description="Record a study grade back into backend scheduling when supported.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=(),
        user_goals=("study",),
        notes=("Currently unsupported; reserved for future backend-native review writes.",),
        support_mode="never",
    ),
    WorkflowSpec(
        id="study.summary",
        label="Study Summary",
        description="Summarize the current study session, misses, and progress.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("search.cards", "card.get", "note.get"),
        user_goals=("study",),
    ),
    WorkflowSpec(
        id="study.weak_cards",
        label="Weak Card Review",
        description="Summarize repeatedly missed cards from the current study session.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("search.cards", "card.get", "note.get"),
        user_goals=("study",),
        notes=("Derived from local study-session history.",),
    ),
    WorkflowSpec(
        id="study.plan",
        label="Study Plan",
        description="Recommend the next study slice based on deck scope and misses.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("search.cards", "card.get", "note.get"),
        user_goals=("study",),
        notes=("Derived from local study-session state and current deck scope.",),
    ),
    WorkflowSpec(
        id="search.unified",
        label="Unified Search",
        description="Search notes or cards with preview-oriented defaults.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("search.count",),
        requires_any_operation=("search.notes", "search.cards"),
        required_context=("collection", "query"),
        user_goals=("search", "study"),
        actions=(
            WorkflowActionSpec(
                id="search.notes",
                label="Search Notes",
                description="Search note ids or previews.",
                required_operations=("search.notes",),
            ),
            WorkflowActionSpec(
                id="search.cards",
                label="Search Cards",
                description="Search card ids or previews.",
                required_operations=("search.cards",),
            ),
        ),
    ),
    WorkflowSpec(
        id="note.manage",
        label="Note Manage",
        description="Inspect or mutate notes through one intent-oriented surface.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        requires_any_operation=(
            "note.get",
            "note.add",
            "note.update",
            "note.delete",
            "note.move_deck",
            "note.add_tags",
            "note.remove_tags",
            "note.fields",
        ),
        required_context=("collection",),
        user_goals=("note_authoring", "deck_management"),
        actions=(
            WorkflowActionSpec("get", "Get Note", "Fetch one note.", ("note.get",)),
            WorkflowActionSpec("fields", "Note Fields", "Fetch note fields.", ("note.fields",)),
            WorkflowActionSpec("add", "Add Note", "Create a note.", ("note.add",)),
            WorkflowActionSpec("update", "Update Note", "Update note fields.", ("note.update",)),
            WorkflowActionSpec("delete", "Delete Note", "Delete a note.", ("note.delete",)),
            WorkflowActionSpec(
                "add_tags",
                "Add Note Tags",
                "Add tags to a note.",
                ("note.add_tags",),
            ),
            WorkflowActionSpec(
                "remove_tags",
                "Remove Note Tags",
                "Remove tags from a note.",
                ("note.remove_tags",),
            ),
            WorkflowActionSpec(
                "move_deck",
                "Move Note Deck",
                "Move a note's cards to another deck.",
                ("note.move_deck",),
            ),
        ),
    ),
    WorkflowSpec(
        id="deck.manage",
        label="Deck Manage",
        description="Inspect or mutate decks through one intent-oriented surface.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        requires_any_operation=(
            "deck.list",
            "deck.get",
            "deck.stats",
            "deck.create",
            "deck.rename",
            "deck.delete",
            "deck.reparent",
        ),
        required_context=("collection",),
        user_goals=("deck_management", "study"),
        actions=(
            WorkflowActionSpec("list", "List Decks", "List decks.", ("deck.list",)),
            WorkflowActionSpec("get", "Get Deck", "Inspect one deck.", ("deck.get",)),
            WorkflowActionSpec("stats", "Deck Stats", "Inspect deck stats.", ("deck.stats",)),
            WorkflowActionSpec(
                "create",
                "Create Deck",
                "Create a deck.",
                ("deck.create",),
                fallback_hint="Switch to the python-anki backend for deck creation.",
            ),
            WorkflowActionSpec(
                "rename",
                "Rename Deck",
                "Rename a deck.",
                ("deck.rename",),
                fallback_hint="Switch to the python-anki backend for deck rename operations.",
            ),
            WorkflowActionSpec(
                "delete",
                "Delete Deck",
                "Delete a deck.",
                ("deck.delete",),
                fallback_hint="Switch to the python-anki backend for deck deletion.",
            ),
            WorkflowActionSpec(
                "reparent",
                "Reparent Deck",
                "Move a deck under a new parent.",
                ("deck.reparent",),
                fallback_hint="Switch to the python-anki backend for deck hierarchy changes.",
            ),
        ),
    ),
    WorkflowSpec(
        id="collection.status",
        label="Collection Status",
        description="Summarize backend and collection readiness for study or management.",
        kind="primary",
        visibility=SURFACE_PRIMARY,
        required_operations=("collection.info",),
        required_context=("collection",),
        user_goals=("diagnostics", "study"),
    ),
    WorkflowSpec(
        id="operation.invoke",
        label="Operation Invoke",
        description="Expert escape hatch for arbitrary low-level ankicli operations.",
        kind="expert",
        visibility=SURFACE_EXPERT,
        user_goals=("debugging", "expert"),
        notes=("Prefer primary workflows unless a precise low-level action is required.",),
    ),
)

PLUGIN_TOOL_SPECS: tuple[PluginToolSpec, ...] = (
    PluginToolSpec(
        name="anki_collection_status",
        label="Anki Collection Status",
        description="Summarize collection readiness for study or management through ankicli.",
        surface=SURFACE_PRIMARY,
        workflow_id="collection.status",
        parameter_schema=object_schema({}),
        command=PluginToolCommandSpec(mode="fixed", argv=("collection", "info")),
        preferred_for_goals=("study", "diagnostics"),
    ),
    PluginToolSpec(
        name="anki_search",
        label="Anki Search",
        description="Search notes or cards with preview-oriented defaults through ankicli.",
        surface=SURFACE_PRIMARY,
        workflow_id="search.unified",
        parameter_schema=object_schema(
            {
                "kind": SEARCH_KIND_SCHEMA,
                "query": {"type": "string"},
                "preview": {"type": "boolean"},
                "limit": {"type": "number", "minimum": 0},
                "offset": {"type": "number", "minimum": 0},
            }
        ),
        command=PluginToolCommandSpec(mode="search-unified"),
        preferred_for_goals=("study", "search"),
    ),
    PluginToolSpec(
        name="anki_note_manage",
        label="Anki Note Manage",
        description="Inspect or mutate notes through one intent-oriented ankicli surface.",
        surface=SURFACE_PRIMARY,
        workflow_id="note.manage",
        parameter_schema=object_schema(
            {
                "action": NOTE_ACTION_SCHEMA,
                "id": {"type": "number"},
                "deck": {"type": "string"},
                "model": {"type": "string"},
                "fields": FIELDS_SCHEMA,
                "tags": STRING_ARRAY_SCHEMA,
                "yes": {"type": "boolean"},
                "dryRun": {"type": "boolean"},
            },
            required=("action",),
        ),
        command=PluginToolCommandSpec(mode="note-manage"),
        preferred_for_goals=("note_authoring", "deck_management"),
    ),
    PluginToolSpec(
        name="anki_deck_manage",
        label="Anki Deck Manage",
        description="Inspect or mutate decks through one intent-oriented ankicli surface.",
        surface=SURFACE_PRIMARY,
        workflow_id="deck.manage",
        parameter_schema=object_schema(
            {
                "action": DECK_ACTION_SCHEMA,
                "name": {"type": "string"},
                "to": {"type": "string"},
                "toParent": {"type": "string"},
                "yes": {"type": "boolean"},
                "dryRun": {"type": "boolean"},
            },
            required=("action",),
        ),
        command=PluginToolCommandSpec(mode="deck-manage"),
        preferred_for_goals=("deck_management", "study"),
    ),
    PluginToolSpec(
        name="anki_study_start",
        label="Anki Study Start",
        description="Create a local tutor-style study session from a deck, preset, or query.",
        surface=SURFACE_PRIMARY,
        workflow_id="study.start",
        parameter_schema=object_schema(
            {
                "deck": {"type": "string"},
                "query": {"type": "string"},
                "scopePreset": STUDY_SCOPE_PRESET_SCHEMA,
                "limit": {"type": "number", "minimum": 1},
            }
        ),
        command=PluginToolCommandSpec(mode="study-start"),
        preferred_for_goals=("study",),
    ),
    PluginToolSpec(
        name="anki_study_next",
        label="Anki Study Next",
        description="Return the current or next study card from the active local tutor session.",
        surface=SURFACE_PRIMARY,
        workflow_id="study.next",
        parameter_schema=object_schema({"sessionId": {"type": "string"}}),
        command=PluginToolCommandSpec(mode="study-session", argv=("study", "next")),
        preferred_for_goals=("study",),
    ),
    PluginToolSpec(
        name="anki_study_card_details",
        label="Anki Study Card Details",
        description=(
            "Return the current study card details from the front side of the active session."
        ),
        surface=SURFACE_PRIMARY,
        workflow_id="study.details",
        parameter_schema=object_schema({"sessionId": {"type": "string"}}),
        command=PluginToolCommandSpec(mode="study-session", argv=("study", "details")),
        preferred_for_goals=("study",),
    ),
    PluginToolSpec(
        name="anki_study_reveal",
        label="Anki Study Reveal",
        description="Reveal the answer and back side for the current study card.",
        surface=SURFACE_PRIMARY,
        workflow_id="study.reveal",
        parameter_schema=object_schema({"sessionId": {"type": "string"}}),
        command=PluginToolCommandSpec(mode="study-session", argv=("study", "reveal")),
        preferred_for_goals=("study",),
    ),
    PluginToolSpec(
        name="anki_study_grade",
        label="Anki Study Grade",
        description="Record a local study grade and advance the active tutor session.",
        surface=SURFACE_PRIMARY,
        workflow_id="study.grade.local",
        parameter_schema=object_schema(
            {
                "rating": STUDY_RATING_SCHEMA,
                "sessionId": {"type": "string"},
            },
            required=("rating",),
        ),
        command=PluginToolCommandSpec(mode="study-grade"),
        preferred_for_goals=("study",),
    ),
    PluginToolSpec(
        name="anki_study_summary",
        label="Anki Study Summary",
        description="Summarize progress for the active local tutor session.",
        surface=SURFACE_PRIMARY,
        workflow_id="study.summary",
        parameter_schema=object_schema({"sessionId": {"type": "string"}}),
        command=PluginToolCommandSpec(mode="study-session", argv=("study", "summary")),
        preferred_for_goals=("study",),
    ),
    PluginToolSpec(
        name="anki_collection_info",
        label="Anki Collection Info",
        description="Fetch high-level collection metadata and counts through ankicli.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema({}),
        command=PluginToolCommandSpec(mode="fixed", argv=("collection", "info")),
    ),
    PluginToolSpec(
        name="anki_auth_status",
        label="Anki Auth Status",
        description="Report whether sync credentials are available through ankicli.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema({}),
        command=PluginToolCommandSpec(mode="fixed", argv=("auth", "status")),
    ),
    PluginToolSpec(
        name="anki_sync_status",
        label="Anki Sync Status",
        description="Check whether the configured collection requires sync through ankicli.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema({}),
        command=PluginToolCommandSpec(mode="fixed", argv=("sync", "status")),
    ),
    PluginToolSpec(
        name="anki_sync_run",
        label="Anki Sync Run",
        description="Run the normal collection sync flow through ankicli.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema({}),
        command=PluginToolCommandSpec(mode="fixed", argv=("sync", "run")),
    ),
    PluginToolSpec(
        name="anki_deck_list",
        label="Anki Deck List",
        description="List decks in the configured collection through ankicli.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema({}),
        command=PluginToolCommandSpec(mode="fixed", argv=("deck", "list")),
    ),
    PluginToolSpec(
        name="anki_model_list",
        label="Anki Model List",
        description="List note types in the configured collection through ankicli.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema({}),
        command=PluginToolCommandSpec(mode="fixed", argv=("model", "list")),
    ),
    PluginToolSpec(
        name="anki_search_notes",
        label="Anki Search Notes",
        description="Search note ids with an Anki-style query through ankicli.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema(
            {
                "query": {"type": "string"},
                "limit": {"type": "number", "minimum": 0},
                "offset": {"type": "number", "minimum": 0},
            },
            required=("query",),
        ),
        command=PluginToolCommandSpec(mode="fixed-search", argv=("search", "notes")),
    ),
    PluginToolSpec(
        name="anki_search_cards",
        label="Anki Search Cards",
        description="Search card ids with an Anki-style query through ankicli.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema(
            {
                "query": {"type": "string"},
                "limit": {"type": "number", "minimum": 0},
                "offset": {"type": "number", "minimum": 0},
            },
            required=("query",),
        ),
        command=PluginToolCommandSpec(mode="fixed-search", argv=("search", "cards")),
    ),
    PluginToolSpec(
        name="anki_note_get",
        label="Anki Note Get",
        description="Fetch one normalized note record by id through ankicli.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema({"id": {"type": "number"}}, required=("id",)),
        command=PluginToolCommandSpec(mode="fixed-id", argv=("note", "get")),
    ),
    PluginToolSpec(
        name="anki_note_add",
        label="Anki Note Add",
        description="Add a note through ankicli with optional dry-run safety.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema(
            {
                "deck": {"type": "string"},
                "model": {"type": "string"},
                "fields": FIELDS_SCHEMA,
                "tags": STRING_ARRAY_SCHEMA,
                "dryRun": {"type": "boolean"},
            },
            required=("deck", "model", "fields"),
        ),
        command=PluginToolCommandSpec(mode="legacy-note-add"),
    ),
    PluginToolSpec(
        name="anki_note_update",
        label="Anki Note Update",
        description="Update note fields through ankicli with optional dry-run safety.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema(
            {
                "id": {"type": "number"},
                "fields": FIELDS_SCHEMA,
                "dryRun": {"type": "boolean"},
            },
            required=("id", "fields"),
        ),
        command=PluginToolCommandSpec(mode="legacy-note-update"),
    ),
    PluginToolSpec(
        name="anki_card_suspend",
        label="Anki Card Suspend",
        description="Suspend a card through ankicli with explicit yes/dry-run flags.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema(
            {
                "id": {"type": "number"},
                "yes": {"type": "boolean"},
                "dryRun": {"type": "boolean"},
            },
            required=("id",),
        ),
        command=PluginToolCommandSpec(mode="card-mutation", argv=("card", "suspend")),
    ),
    PluginToolSpec(
        name="anki_card_unsuspend",
        label="Anki Card Unsuspend",
        description="Unsuspend a card through ankicli with explicit yes/dry-run flags.",
        surface=SURFACE_LEGACY,
        workflow_id=None,
        parameter_schema=object_schema(
            {
                "id": {"type": "number"},
                "yes": {"type": "boolean"},
                "dryRun": {"type": "boolean"},
            },
            required=("id",),
        ),
        command=PluginToolCommandSpec(mode="card-mutation", argv=("card", "unsuspend")),
    ),
    PluginToolSpec(
        name="ankicli",
        label="ankicli",
        description="Run a freeform ankicli command as a thin JSON-mode passthrough.",
        surface=SURFACE_EXPERT,
        workflow_id="operation.invoke",
        parameter_schema=object_schema(
            {"command": {"type": "string"}},
            required=("command",),
        ),
        command=PluginToolCommandSpec(mode="freeform"),
        preferred_for_goals=("expert", "debugging"),
    ),
)

SKILL_SPECS: tuple[SkillSpec, ...] = (
    SkillSpec(
        slug="anki-study",
        name="anki-study",
        description="Teach the agent how to run tutor-style Anki study sessions.",
        summary=(
            "Use the primary study workflows first and keep tutoring separate "
            "from collection mutation."
        ),
        tool_names=(
            "anki_collection_status",
            "anki_study_start",
            "anki_study_card_details",
            "anki_study_reveal",
            "anki_study_grade",
            "anki_study_summary",
        ),
        rules=(
            "Start with the narrowest deck or scope preset that matches the "
            "user goal, and compare due, new, learning, and review counts "
            "when the user needs help picking a deck.",
            "Use anki_study_card_details as the default current-card read for "
            "front-side tutoring, and use anki_study_reveal when the user asks "
            "to reveal the answer or back side.",
            "Present study cards like Anki by default: focus on the prompt, "
            "question, and front-side clues first, and do not volunteer the "
            "answer or back-side content until after you call "
            "anki_study_reveal; include media in the same response when it "
            "helps the learner without spoiling the answer.",
            "Present grading choices as a numbered list in this order when "
            "you guide the user: 1. Again 2. Hard 3. Good 4. Easy.",
            "Treat study-session state as the tutoring source of truth, and "
            "only call anki_study_grade after the current card has been "
            "revealed.",
            "Prefer curated study_view output over raw_fields, and only fall "
            "back to raw fields when the curated answer is missing or the "
            "user asks for full detail.",
            "When current_card.view is present, rely on the returned canvas "
            "metadata to show the card in Control UI, use "
            "current_card.tutoring_summary for reasoning, and use "
            "current_card.study_media for native Discord or Telegram media "
            "delivery; if media resolution fails, name the structured error "
            "code instead of inventing a generic failure.",
            "Explain misses in study terms and patterns instead of dumping raw database fields.",
        ),
        anti_patterns=(
            "Do not default to low-level tools when the user asked to study.",
            "Do not mutate notes or decks unless explicitly asked.",
            (
                "Do not skip anki_study_reveal when the user asks for the answer "
                "or when grading requires a revealed card."
            ),
        ),
    ),
    SkillSpec(
        slug="anki-collection-management",
        name="anki-collection-management",
        description="Teach the agent how to inspect and manage collection and deck state.",
        summary="Read first, dry-run deck writes when supported, and re-verify after mutation.",
        tool_names=("anki_collection_status", "anki_search", "anki_deck_manage"),
        rules=(
            "Inspect collection and deck state before mutating.",
            "Keep deck operations narrowly scoped.",
            "Re-run deck or collection reads after successful writes.",
            "If a backend does not support a deck action, say so before "
            "attempting the mutation and recommend switching to a backend "
            "that supports deck writes.",
        ),
    ),
    SkillSpec(
        slug="anki-note-authoring",
        name="anki-note-authoring",
        description="Teach the agent how to add, inspect, update, and move notes safely.",
        summary=(
            "Find the target note first, validate structure mentally, and "
            "re-read after writes."
        ),
        tool_names=("anki_search", "anki_note_manage", "anki_deck_manage"),
        rules=(
            "Search or inspect before mutating an existing note.",
            "Use dry-run for adds, updates, deletes, and moves when available.",
            "Treat deletes and broad retagging as explicit user intent only.",
        ),
    ),
    SkillSpec(
        slug="anki-diagnostics",
        name="anki-diagnostics",
        description="Teach the agent how to diagnose backend, collection, and capability issues.",
        summary=(
            "Treat structured ankicli errors as authoritative and distinguish "
            "setup from unsupported behavior."
        ),
        tool_names=("anki_collection_status", "ankicli"),
        rules=(
            "Confirm backend and collection readiness first.",
            "Differentiate missing setup from backend operation support gaps.",
            "If one backend fails, check whether the alternate backend is intended and supported.",
            "Use the media error taxonomy codes verbatim when media "
            "resolution or provider setup is the problem.",
        ),
    ),
)

ALWAYS_AVAILABLE_BY_BACKEND: dict[str, set[str]] = {
    "python-anki": {
        "profile.list",
        "profile.get",
        "profile.default",
        "profile.resolve",
        "backup.status",
        "backup.list",
        "backup.get",
    },
    "ankiconnect": set(),
}

ANKICONNECT_OPERATION_IDS: set[str] = {
    "doctor.backend",
    "doctor.capabilities",
    "backend.test_connection",
    "collection.info",
    "collection.stats",
    "deck.list",
    "deck.get",
    "deck.stats",
    "model.list",
    "model.get",
    "model.fields",
    "model.templates",
    "model.validate_note",
    "tag.list",
    "search.notes",
    "search.cards",
    "search.count",
    "search.preview",
    "export.notes",
    "export.cards",
    "import.notes",
    "import.patch",
    "note.get",
    "note.add",
    "note.update",
    "note.fields",
    "note.move_deck",
    "note.add_tags",
    "note.remove_tags",
    "card.get",
    "card.suspend",
    "card.unsuspend",
}

OPERATION_IDS = tuple(spec.id for spec in OPERATION_SPECS)
WORKFLOW_IDS = tuple(spec.id for spec in WORKFLOW_SPECS)


def get_operation_specs() -> tuple[OperationSpec, ...]:
    return OPERATION_SPECS


def get_workflow_specs() -> tuple[WorkflowSpec, ...]:
    return WORKFLOW_SPECS


def get_plugin_tool_specs() -> tuple[PluginToolSpec, ...]:
    return PLUGIN_TOOL_SPECS


def get_skill_specs() -> tuple[SkillSpec, ...]:
    return SKILL_SPECS


def supported_operations_for_backend(backend_name: str, *, available: bool) -> dict[str, bool]:
    if backend_name == "python-anki":
        supported = {operation_id: available for operation_id in OPERATION_IDS}
        for operation_id in ALWAYS_AVAILABLE_BY_BACKEND[backend_name]:
            supported[operation_id] = True
        return supported
    if backend_name == "ankiconnect":
        return {
            operation_id: operation_id in ANKICONNECT_OPERATION_IDS
            for operation_id in OPERATION_IDS
        }
    raise ValueError(f"Unsupported backend: {backend_name}")


def _action_supported(
    action: WorkflowActionSpec,
    supported_operations: dict[str, bool],
) -> bool:
    required_ok = all(
        supported_operations.get(operation_id, False)
        for operation_id in action.required_operations
    )
    any_ok = True
    if action.requires_any_operation:
        any_ok = any(
            supported_operations.get(operation_id, False)
            for operation_id in action.requires_any_operation
        )
    return required_ok and any_ok


def workflow_support_for_operations(
    supported_operations: dict[str, bool],
) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for spec in WORKFLOW_SPECS:
        if spec.support_mode == "never":
            resolved[spec.id] = {
                "supported": False,
                "actions": {
                    action.id: False
                    for action in spec.actions
                },
            }
            continue
        required_ok = all(
            supported_operations.get(operation_id, False)
            for operation_id in spec.required_operations
        )
        any_ok = True
        if spec.requires_any_operation:
            any_ok = any(
                supported_operations.get(operation_id, False)
                for operation_id in spec.requires_any_operation
            )
        supported = required_ok and any_ok
        action_support = {
            action.id: _action_supported(action, supported_operations)
            for action in spec.actions
        }
        resolved[spec.id] = {
            "supported": supported,
            "actions": action_support,
        }
    return resolved


def supported_workflows_for_operations(supported_operations: dict[str, bool]) -> dict[str, bool]:
    support = workflow_support_for_operations(supported_operations)
    return {workflow_id: bool(payload["supported"]) for workflow_id, payload in support.items()}


def support_matrix_snapshot() -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for backend_name in BACKEND_NAMES:
        available = True
        supported_operations = supported_operations_for_backend(backend_name, available=available)
        snapshot[backend_name] = {
            "operations": supported_operations,
            "workflows": supported_workflows_for_operations(supported_operations),
            "workflow_support": workflow_support_for_operations(supported_operations),
        }
    return snapshot


def _skill_fragment_payload(spec: SkillSpec) -> dict[str, Any]:
    return asdict(spec)


def catalog_snapshot() -> dict[str, Any]:
    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "operations": [asdict(spec) for spec in OPERATION_SPECS],
        "workflows": [asdict(spec) for spec in WORKFLOW_SPECS],
        "plugin_tools": [asdict(spec) for spec in PLUGIN_TOOL_SPECS],
        "skills": [_skill_fragment_payload(spec) for spec in SKILL_SPECS],
        "support_matrix": support_matrix_snapshot(),
        "error_taxonomy": list(MEDIA_ERROR_TAXONOMY),
    }
