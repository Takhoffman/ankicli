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


class AuthRequiredError(AnkiCliError):
    code = "AUTH_REQUIRED"
    exit_code = 16


class AuthInvalidError(AnkiCliError):
    code = "AUTH_INVALID"
    exit_code = 17


class AuthStorageUnavailableError(AnkiCliError):
    code = "AUTH_STORAGE_UNAVAILABLE"
    exit_code = 18


class SyncUnavailableError(AnkiCliError):
    code = "SYNC_UNAVAILABLE"
    exit_code = 19


class SyncConflictError(AnkiCliError):
    code = "SYNC_CONFLICT"
    exit_code = 20


class SyncInProgressError(AnkiCliError):
    code = "SYNC_IN_PROGRESS"
    exit_code = 21


class SyncFailedError(AnkiCliError):
    code = "SYNC_FAILED"
    exit_code = 22


class BackupUnavailableError(AnkiCliError):
    code = "BACKUP_UNAVAILABLE"
    exit_code = 23


class BackupNotFoundError(AnkiCliError):
    code = "BACKUP_NOT_FOUND"
    exit_code = 24


class BackupCreateFailedError(AnkiCliError):
    code = "BACKUP_CREATE_FAILED"
    exit_code = 25


class BackupRestoreFailedError(AnkiCliError):
    code = "BACKUP_RESTORE_FAILED"
    exit_code = 26


class BackupRestoreUnsafeError(AnkiCliError):
    code = "BACKUP_RESTORE_UNSAFE"
    exit_code = 27


class ProfileNotFoundError(AnkiCliError):
    code = "PROFILE_NOT_FOUND"
    exit_code = 28


class ProfileResolutionError(AnkiCliError):
    code = "PROFILE_RESOLUTION_FAILED"
    exit_code = 29


class StudySessionNotFoundError(AnkiCliError):
    code = "STUDY_SESSION_NOT_FOUND"
    exit_code = 30


class StudySessionRequiredError(AnkiCliError):
    code = "STUDY_SESSION_REQUIRED"
    exit_code = 31
