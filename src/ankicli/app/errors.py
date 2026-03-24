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


class CollectionNotFoundError(AnkiCliError):
    code = "COLLECTION_NOT_FOUND"
    exit_code = 5


class CollectionOpenError(AnkiCliError):
    code = "COLLECTION_OPEN_FAILED"
    exit_code = 6


class NoteNotFoundError(AnkiCliError):
    code = "NOTE_NOT_FOUND"
    exit_code = 7


class CardNotFoundError(AnkiCliError):
    code = "CARD_NOT_FOUND"
    exit_code = 8


class DeckNotFoundError(AnkiCliError):
    code = "DECK_NOT_FOUND"
    exit_code = 9


class ModelNotFoundError(AnkiCliError):
    code = "MODEL_NOT_FOUND"
    exit_code = 10


class NotImplementedYetError(AnkiCliError):
    code = "NOT_IMPLEMENTED_YET"
    exit_code = 11


class UnsafeOperationError(AnkiCliError):
    code = "UNSAFE_OPERATION"
    exit_code = 12


class TagNotFoundError(AnkiCliError):
    code = "TAG_NOT_FOUND"
    exit_code = 13


class BackendOperationUnsupportedError(AnkiCliError):
    code = "BACKEND_OPERATION_UNSUPPORTED"
    exit_code = 14


class MediaNotFoundError(AnkiCliError):
    code = "MEDIA_NOT_FOUND"
    exit_code = 15
