from __future__ import annotations


def fixture_read_error_codes(*extra: str) -> set[str]:
    return {"BACKEND_UNAVAILABLE", "COLLECTION_OPEN_FAILED", *extra}


def fixture_write_error_codes(*extra: str) -> set[str]:
    return {"BACKEND_UNAVAILABLE", "COLLECTION_OPEN_FAILED", *extra}
