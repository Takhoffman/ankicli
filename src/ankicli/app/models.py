"""Normalized output models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ankicli.app.catalog import OPERATION_IDS

IMPLEMENTED_BACKEND_OPERATIONS = OPERATION_IDS


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
    runtime_mode: str | None = None
    runtime_override_active: bool = False
    runtime_module_path: str | None = None
    runtime_version: str | None = None
    supported_runtime_version: str | None = None
    supported_runtime: bool | None = None
    runtime_failure_reason: str | None = None
    supported_operations: dict[str, bool] = Field(default_factory=dict)
    supported_workflows: dict[str, bool] = Field(default_factory=dict)
    workflow_support: dict[str, dict[str, Any]] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
