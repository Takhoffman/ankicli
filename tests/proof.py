from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from ankicli.app.quality_matrix import PROOF_TYPES

F = TypeVar("F", bound=Callable)


def proves(command: str, *proofs: str):
    if not isinstance(command, str) or not command:
        raise ValueError("proves() requires a non-empty command id")
    if not proofs:
        raise ValueError("proves() requires at least one proof type")
    invalid = sorted(set(proofs) - PROOF_TYPES)
    if invalid:
        raise ValueError(f"Unknown proof types for {command}: {', '.join(invalid)}")

    def decorator(func: F) -> F:
        return func

    return decorator
