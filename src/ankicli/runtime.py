"""CLI runtime helpers."""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from types import ModuleType

SUPPORTED_ANKI_VERSION = "25.9.2"


@dataclass(slots=True)
class Settings:
    collection: str | None
    profile: str | None
    backend_name: str
    json_output: bool
    no_auto_backup: bool


@dataclass(slots=True)
class AnkiRuntimeProbe:
    source_path: str | None
    source_import_path: str | None
    import_available: bool
    module_path: str | None
    version: str | None
    collection_import_available: bool
    runtime_mode: str
    override_active: bool
    supported_runtime_version: str
    supported_runtime: bool
    failure_reason: str | None


def configure_anki_source_path() -> str | None:
    source_path = os.environ.get("ANKI_SOURCE_PATH")
    if not source_path:
        return None

    source_root = Path(source_path).expanduser().resolve()
    candidate_paths = [
        source_root / "pylib",
        source_root / "python",
        source_root,
    ]
    for candidate in candidate_paths:
        if candidate.exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)
            return candidate_str
    return str(source_root)


def _import_anki_module() -> ModuleType:
    return importlib.import_module("anki")


def _collection_import_available() -> bool:
    module_candidates = ("anki.collection", "anki.storage")
    for module_name in module_candidates:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        if getattr(module, "Collection", None) is not None:
            return True
    return False


def _anki_module_path(anki_module: ModuleType) -> str | None:
    module_path = getattr(anki_module, "__file__", None)
    if module_path:
        return str(module_path)
    module_paths = getattr(anki_module, "__path__", None)
    if module_paths:
        for candidate in module_paths:
            return str(candidate)
    return None


def _anki_version(anki_module: ModuleType) -> str | None:
    version = getattr(anki_module, "__version__", None)
    if version is not None:
        return str(version)
    try:
        return metadata.version("anki")
    except metadata.PackageNotFoundError:
        return None


def probe_anki_runtime() -> AnkiRuntimeProbe:
    source_import_path = configure_anki_source_path()
    source_path = os.environ.get("ANKI_SOURCE_PATH")
    override_active = bool(source_path)
    runtime_mode = "override" if override_active else "packaged"

    try:
        anki_module = _import_anki_module()
    except ImportError:
        return AnkiRuntimeProbe(
            source_path=source_path,
            source_import_path=source_import_path,
            import_available=False,
            module_path=None,
            version=None,
            collection_import_available=False,
            runtime_mode=runtime_mode,
            override_active=override_active,
            supported_runtime_version=SUPPORTED_ANKI_VERSION,
            supported_runtime=False,
            failure_reason="missing_runtime",
        )

    module_path = _anki_module_path(anki_module)
    version = _anki_version(anki_module)
    collection_import_available = _collection_import_available()
    if version != SUPPORTED_ANKI_VERSION:
        failure_reason = "version_mismatch"
    elif not collection_import_available:
        failure_reason = "collection_api_unavailable"
    else:
        failure_reason = None

    return AnkiRuntimeProbe(
        source_path=source_path,
        source_import_path=source_import_path,
        import_available=True,
        module_path=module_path,
        version=version,
        collection_import_available=collection_import_available,
        runtime_mode=runtime_mode,
        override_active=override_active,
        supported_runtime_version=SUPPORTED_ANKI_VERSION,
        supported_runtime=failure_reason is None,
        failure_reason=failure_reason,
    )


def get_backend(backend_name: str):
    configure_anki_source_path()
    if backend_name == "python-anki":
        from ankicli.backends.python_anki import PythonAnkiBackend

        return PythonAnkiBackend()
    if backend_name == "ankiconnect":
        from ankicli.backends.ankiconnect import AnkiConnectBackend

        return AnkiConnectBackend()
    raise ValueError(f"Unsupported backend: {backend_name}")
