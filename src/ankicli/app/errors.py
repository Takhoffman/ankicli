"""Domain and CLI errors."""

from __future__ import annotations


class AnkiCliError(Exception):
    """Base error carrying a stable machine-readable code."""

    code = "UNKNOWN_ERROR"
    exit_code = 1

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AnkiCliError):
    code = "VALIDATION_ERROR"
    exit_code = 2


class BackendUnavailableError(AnkiCliError):
    code = "BACKEND_UNAVAILABLE"
    exit_code = 3


class CollectionRequiredError(AnkiCliError):
    code = "COLLECTION_REQUIRED"
    exit_code = 4


class NotImplementedYetError(AnkiCliError):
    code = "NOT_IMPLEMENTED_YET"
    exit_code = 10

