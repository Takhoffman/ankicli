from __future__ import annotations

import json
import subprocess

import pytest

from ankicli.app.credentials import MacOSKeychainCredentialStore, SyncCredential
from ankicli.app.errors import AuthStorageUnavailableError


class _Completed:
    def __init__(self, returncode: int, *, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.mark.unit
def test_macos_keychain_store_reads_json_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr("shutil.which", lambda command: "/usr/bin/security")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: _Completed(
            0,
            stdout=json.dumps({"hkey": "abc", "endpoint": "https://sync"}),
        ),
    )

    result = MacOSKeychainCredentialStore().read(backend_name="python-anki")

    assert result == SyncCredential(hkey="abc", endpoint="https://sync")


@pytest.mark.unit
def test_macos_keychain_store_returns_none_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr("shutil.which", lambda command: "/usr/bin/security")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: _Completed(
            44,
            stderr=(
                "security: SecKeychainSearchCopyNext: The specified item "
                "could not be found in the keychain."
            ),
        ),
    )

    result = MacOSKeychainCredentialStore().read(backend_name="python-anki")

    assert result is None


@pytest.mark.unit
def test_macos_keychain_store_requires_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Linux")

    with pytest.raises(AuthStorageUnavailableError):
        MacOSKeychainCredentialStore().read(backend_name="python-anki")
