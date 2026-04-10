from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ankicli.app.credentials import (
    FileCredentialStore,
    KeyringCredentialStore,
    SyncCredential,
    default_credential_store,
    default_credentials_path,
)


@pytest.mark.unit
def test_keyring_store_reads_json_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[tuple[str, str], str] = {
        ("ankicli.python-anki.sync", "default"): json.dumps(
            {"hkey": "abc", "endpoint": "https://sync"}
        )
    }
    fake_keyring = SimpleNamespace(
        get_keyring=lambda: SimpleNamespace(priority=1),
        get_password=lambda service, account: stored.get((service, account)),
        set_password=lambda service, account, value: stored.__setitem__((service, account), value),
        delete_password=lambda service, account: stored.pop((service, account), None),
    )
    monkeypatch.setattr("ankicli.app.credentials.keyring", fake_keyring)

    result = KeyringCredentialStore().read(backend_name="python-anki")

    assert result == SyncCredential(hkey="abc", endpoint="https://sync")


@pytest.mark.unit
def test_file_store_round_trip(tmp_path: Path) -> None:
    store = FileCredentialStore(path=tmp_path / "credentials.json")

    store.write(
        backend_name="python-anki",
        credential=SyncCredential(hkey="abc", endpoint="https://sync"),
    )

    assert store.read(backend_name="python-anki") == SyncCredential(
        hkey="abc",
        endpoint="https://sync",
    )
    assert store.clear(backend_name="python-anki") is True
    assert store.read(backend_name="python-anki") is None


@pytest.mark.unit
def test_default_credential_store_falls_back_to_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ankicli.app.credentials.keyring", None)

    store = default_credential_store()

    assert store.info().backend == "file-fallback"
    assert store.info().fallback is True


@pytest.mark.unit
def test_default_credentials_path_is_platform_aware(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/.config")

    result = default_credentials_path()

    assert result == Path("/tmp/.config/ankicli/credentials.json")
