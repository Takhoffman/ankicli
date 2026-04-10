"""Credential storage for sync/auth flows."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import keyring
    from keyring.errors import KeyringError
except ImportError:  # pragma: no cover - dependency should normally be present
    keyring = None

    class KeyringError(Exception):
        """Fallback keyring error when the dependency is unavailable."""


from ankicli.app.errors import AuthStorageUnavailableError


@dataclass(slots=True)
class SyncCredential:
    hkey: str
    endpoint: str | None = None


@dataclass(slots=True)
class CredentialStoreInfo:
    backend: str
    available: bool
    fallback: bool
    path: str | None = None
    reason: str | None = None


class CredentialStore:
    """Backend-neutral sync credential storage."""

    backend_label = "unknown"
    fallback_active = False

    def read(self, *, backend_name: str) -> SyncCredential | None:
        raise NotImplementedError

    def write(self, *, backend_name: str, credential: SyncCredential) -> None:
        raise NotImplementedError

    def clear(self, *, backend_name: str) -> bool:
        raise NotImplementedError

    def info(self) -> CredentialStoreInfo:
        return CredentialStoreInfo(
            backend=self.backend_label,
            available=True,
            fallback=self.fallback_active,
        )


def default_credentials_root() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library/Application Support" / "ankicli"
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "ankicli"
        return Path.home() / "AppData/Roaming/ankicli"
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "ankicli"
    return Path.home() / ".config/ankicli"


def default_credentials_path() -> Path:
    return default_credentials_root() / "credentials.json"


class KeyringCredentialStore(CredentialStore):
    """Persist sync credentials in the platform keyring when available."""

    backend_label = "keyring"
    _ACCOUNT_NAME = "default"

    def _service_name(self, backend_name: str) -> str:
        return f"ankicli.{backend_name}.sync"

    def _ensure_available(self) -> Any:
        if keyring is None:
            raise AuthStorageUnavailableError(
                "Python package 'keyring' is unavailable in this environment",
            )
        backend = keyring.get_keyring()
        priority = getattr(backend, "priority", None)
        if priority is not None and priority <= 0:
            raise AuthStorageUnavailableError(
                "No usable system keyring backend is available in this environment",
            )
        return backend

    def read(self, *, backend_name: str) -> SyncCredential | None:
        self._ensure_available()
        try:
            raw = keyring.get_password(self._service_name(backend_name), self._ACCOUNT_NAME)
        except KeyringError as exc:
            raise AuthStorageUnavailableError(
                "Failed to read sync credentials from the system keyring",
                details={"backend": backend_name, "reason": str(exc)},
            ) from exc
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AuthStorageUnavailableError(
                "Stored sync credentials are unreadable",
                details={"backend": backend_name},
            ) from exc
        hkey = str(payload.get("hkey") or "").strip()
        if not hkey:
            return None
        endpoint = payload.get("endpoint")
        return SyncCredential(hkey=hkey, endpoint=str(endpoint) if endpoint else None)

    def write(self, *, backend_name: str, credential: SyncCredential) -> None:
        self._ensure_available()
        payload = json.dumps(
            {
                "hkey": credential.hkey,
                "endpoint": credential.endpoint,
            },
            separators=(",", ":"),
        )
        try:
            keyring.set_password(self._service_name(backend_name), self._ACCOUNT_NAME, payload)
        except KeyringError as exc:
            raise AuthStorageUnavailableError(
                "Failed to write sync credentials to the system keyring",
                details={"backend": backend_name, "reason": str(exc)},
            ) from exc

    def clear(self, *, backend_name: str) -> bool:
        self._ensure_available()
        try:
            existing = keyring.get_password(self._service_name(backend_name), self._ACCOUNT_NAME)
            if existing is None:
                return False
            keyring.delete_password(self._service_name(backend_name), self._ACCOUNT_NAME)
            return True
        except KeyringError as exc:
            raise AuthStorageUnavailableError(
                "Failed to delete sync credentials from the system keyring",
                details={"backend": backend_name, "reason": str(exc)},
            ) from exc


class FileCredentialStore(CredentialStore):
    """Persist sync credentials in a local JSON file with strict local permissions."""

    backend_label = "file-fallback"
    fallback_active = True

    def __init__(self, *, path: Path | None = None, reason: str | None = None) -> None:
        self.path = (path or default_credentials_path()).expanduser().resolve()
        self.reason = reason

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.path.parent.chmod(0o700)

    def _load_payload(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AuthStorageUnavailableError(
                "Stored sync credentials are unreadable",
                details={"path": str(self.path)},
            ) from exc
        if not isinstance(payload, dict):
            raise AuthStorageUnavailableError(
                "Stored sync credentials are unreadable",
                details={"path": str(self.path)},
            )
        return payload

    def _write_payload(self, payload: dict[str, dict[str, Any]]) -> None:
        self._ensure_parent()
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        if os.name != "nt":
            temp_path.chmod(0o600)
        temp_path.replace(self.path)
        if os.name != "nt":
            self.path.chmod(0o600)

    def read(self, *, backend_name: str) -> SyncCredential | None:
        payload = self._load_payload()
        item = payload.get(backend_name)
        if not isinstance(item, dict):
            return None
        hkey = str(item.get("hkey") or "").strip()
        if not hkey:
            return None
        endpoint = item.get("endpoint")
        return SyncCredential(hkey=hkey, endpoint=str(endpoint) if endpoint else None)

    def write(self, *, backend_name: str, credential: SyncCredential) -> None:
        payload = self._load_payload()
        payload[backend_name] = {
            "hkey": credential.hkey,
            "endpoint": credential.endpoint,
        }
        self._write_payload(payload)

    def clear(self, *, backend_name: str) -> bool:
        payload = self._load_payload()
        existed = backend_name in payload
        if existed:
            del payload[backend_name]
            self._write_payload(payload)
        return existed

    def info(self) -> CredentialStoreInfo:
        return CredentialStoreInfo(
            backend=self.backend_label,
            available=True,
            fallback=True,
            path=str(self.path),
            reason=self.reason,
        )


def default_credential_store() -> CredentialStore:
    try:
        store = KeyringCredentialStore()
        store._ensure_available()
        return store
    except AuthStorageUnavailableError as exc:
        return FileCredentialStore(reason=str(exc))


def probe_default_credential_store() -> CredentialStoreInfo:
    return default_credential_store().info()
