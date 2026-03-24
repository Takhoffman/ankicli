"""Normalized output models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

IMPLEMENTED_BACKEND_OPERATIONS = (
    "doctor.backend",
    "doctor.capabilities",
    "doctor.collection",
    "doctor.safety",
    "backend.test_connection",
    "profile.list",
    "profile.get",
    "profile.default",
    "profile.resolve",
    "auth.status",
    "auth.login",
    "auth.logout",
    "backup.status",
    "backup.list",
    "backup.create",
    "backup.get",
    "backup.restore",
    "collection.info",
    "collection.stats",
    "collection.validate",
    "collection.lock_status",
    "deck.list",
    "deck.get",
    "deck.stats",
    "deck.create",
    "deck.rename",
    "deck.delete",
    "deck.reparent",
    "model.list",
    "model.get",
    "model.fields",
    "model.templates",
    "model.validate_note",
    "tag.list",
    "tag.apply",
    "tag.remove",
    "tag.rename",
    "tag.delete",
    "tag.reparent",
    "media.list",
    "media.check",
    "media.attach",
    "media.orphaned",
    "media.resolve_path",
    "search.notes",
    "search.cards",
    "search.count",
    "search.preview",
    "export.notes",
    "export.cards",
    "import.notes",
    "import.patch",
    "sync.status",
    "sync.run",
    "sync.pull",
    "sync.push",
    "note.get",
    "note.add",
    "note.update",
    "note.delete",
    "note.fields",
    "note.move_deck",
    "note.add_tags",
    "note.remove_tags",
    "card.get",
    "card.suspend",
    "card.unsuspend",
)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class Envelope(BaseModel):
    ok: bool
    backend: str
    data: dict[str, Any] | None = None
    error: ErrorBody | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class BackendCapabilities(BaseModel):
    backend: str
    available: bool
    supports_collection_reads: bool
    supports_collection_writes: bool
    supports_live_desktop: bool
    supported_operations: dict[str, bool] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
