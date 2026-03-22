"""Normalized output models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
    notes: list[str] = Field(default_factory=list)

