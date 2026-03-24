"""Credential storage for sync/auth flows."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from dataclasses import dataclass

from ankicli.app.errors import AuthStorageUnavailableError


@dataclass(slots=True)
class SyncCredential:
    hkey: str
    endpoint: str | None = None


class CredentialStore:
    """Backend-neutral sync credential storage."""

    def read(self, *, backend_name: str) -> SyncCredential | None:
        raise NotImplementedError

    def write(self, *, backend_name: str, credential: SyncCredential) -> None:
        raise NotImplementedError

    def clear(self, *, backend_name: str) -> bool:
        raise NotImplementedError


class MacOSKeychainCredentialStore(CredentialStore):
    """Persist sync credentials in the macOS Keychain."""

    _ACCOUNT_NAME = "default"

    def __init__(self, *, command: str = "security") -> None:
        self.command = command

    def _service_name(self, backend_name: str) -> str:
        return f"ankicli.{backend_name}.sync"

    def _ensure_available(self) -> None:
        if platform.system() != "Darwin":
            raise AuthStorageUnavailableError(
                "Sync credential storage currently requires the macOS Keychain",
            )
        if shutil.which(self.command) is None:
            raise AuthStorageUnavailableError(
                "macOS security CLI is unavailable in this environment",
            )

    def read(self, *, backend_name: str) -> SyncCredential | None:
        self._ensure_available()
        process = subprocess.run(
            [
                self.command,
                "find-generic-password",
                "-s",
                self._service_name(backend_name),
                "-a",
                self._ACCOUNT_NAME,
                "-w",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode != 0:
            stderr = process.stderr.lower()
            if "could not be found" in stderr or "the specified item could not be found" in stderr:
                return None
            raise AuthStorageUnavailableError(
                "Failed to read sync credentials from the macOS Keychain",
                details={"backend": backend_name, "reason": process.stderr.strip()},
            )
        raw = process.stdout.strip()
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
        process = subprocess.run(
            [
                self.command,
                "add-generic-password",
                "-U",
                "-s",
                self._service_name(backend_name),
                "-a",
                self._ACCOUNT_NAME,
                "-w",
                payload,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode != 0:
            raise AuthStorageUnavailableError(
                "Failed to write sync credentials to the macOS Keychain",
                details={"backend": backend_name, "reason": process.stderr.strip()},
            )

    def clear(self, *, backend_name: str) -> bool:
        self._ensure_available()
        process = subprocess.run(
            [
                self.command,
                "delete-generic-password",
                "-s",
                self._service_name(backend_name),
                "-a",
                self._ACCOUNT_NAME,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode == 0:
            return True
        stderr = process.stderr.lower()
        if "could not be found" in stderr or "the specified item could not be found" in stderr:
            return False
        raise AuthStorageUnavailableError(
            "Failed to delete sync credentials from the macOS Keychain",
            details={"backend": backend_name, "reason": process.stderr.strip()},
        )
