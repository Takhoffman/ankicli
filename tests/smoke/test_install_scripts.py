from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tarfile
import zipfile
from hashlib import sha256
from pathlib import Path

import pytest


def _make_fake_binary(path: Path) -> None:
    backend_payload = (
        '{"ok":true,"backend":"python-anki","data":{"name":"python-anki","available":true}}'
    )
    path.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then\n'
        '  echo "ankicli 9.9.9"\n'
        'elif [ "$1" = "--json" ] && [ "$2" = "doctor" ] && [ "$3" = "backend" ]; then\n'
        f"  echo '{backend_payload}'\n"
        "else\n"
        '  echo "unexpected args: $*" >&2\n'
        "  exit 1\n"
        "fi\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_checksum(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.mark.smoke
def test_shell_installer_supports_versioned_local_release(tmp_path: Path) -> None:
    release_root = tmp_path / "release"
    payload_root = tmp_path / "payload" / "ankicli-1.2.3-darwin-x64"
    payload_root.mkdir(parents=True)
    _make_fake_binary(payload_root / "ankicli")
    (payload_root / "README-install.txt").write_text("readme", encoding="utf-8")

    archive_path = release_root / "download" / "v1.2.3" / "ankicli-1.2.3-darwin-x64.tar.gz"
    archive_path.parent.mkdir(parents=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(payload_root, arcname=payload_root.name)

    checksum_path = archive_path.parent / "ankicli-1.2.3-checksums.txt"
    checksum_path.write_text(
        f"{_write_checksum(archive_path)}  {archive_path.name}\n",
        encoding="utf-8",
    )

    install_bin_dir = tmp_path / "bin"
    install_root = tmp_path / "install"
    env = os.environ | {
        "VERSION": "1.2.3",
        "ANKICLI_TARGET": "darwin-x64",
        "ANKICLI_RELEASES_BASE": release_root.as_uri(),
        "ANKICLI_INSTALL_BIN_DIR": str(install_bin_dir),
        "ANKICLI_INSTALL_ROOT": str(install_root),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "LC_CTYPE": "C.UTF-8",
    }

    result = subprocess.run(
        ["sh", "scripts/install.sh"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    installed = install_bin_dir / "ankicli"
    assert installed.exists()
    assert "Installed ankicli 1.2.3" in result.stdout


@pytest.mark.smoke
def test_shell_installer_rejects_unsafe_version_before_install(tmp_path: Path) -> None:
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    sentinel = outside_dir / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    result = subprocess.run(
        ["sh", "scripts/install.sh"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        env=os.environ
        | {
            "VERSION": "../outside",
            "ANKICLI_TARGET": "darwin-x64",
            "ANKICLI_RELEASES_BASE": (tmp_path / "release").as_uri(),
            "ANKICLI_INSTALL_BIN_DIR": str(tmp_path / "bin"),
            "ANKICLI_INSTALL_ROOT": str(tmp_path / "install"),
        },
        check=False,
    )

    assert result.returncode != 0
    assert "invalid release version" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "keep"


@pytest.mark.smoke
def test_shell_installer_rejects_unknown_target_before_download(tmp_path: Path) -> None:
    result = subprocess.run(
        ["sh", "scripts/install.sh"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        env=os.environ
        | {
            "VERSION": "latest",
            "ANKICLI_TARGET": "../darwin-x64",
            "ANKICLI_RELEASE_API": (tmp_path / "missing-release.json").as_uri(),
            "ANKICLI_RELEASES_BASE": (tmp_path / "release").as_uri(),
            "ANKICLI_INSTALL_BIN_DIR": str(tmp_path / "bin"),
            "ANKICLI_INSTALL_ROOT": str(tmp_path / "install"),
        },
        check=False,
    )

    assert result.returncode != 0
    assert "invalid release target" in result.stderr


@pytest.mark.smoke
def test_shell_installer_fails_on_bad_checksum(tmp_path: Path) -> None:
    release_root = tmp_path / "release"
    payload_root = tmp_path / "payload" / "ankicli-1.2.3-darwin-x64"
    payload_root.mkdir(parents=True)
    _make_fake_binary(payload_root / "ankicli")

    archive_path = release_root / "download" / "v1.2.3" / "ankicli-1.2.3-darwin-x64.tar.gz"
    archive_path.parent.mkdir(parents=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(payload_root, arcname=payload_root.name)

    checksum_path = archive_path.parent / "ankicli-1.2.3-checksums.txt"
    checksum_path.write_text(
        f"{'0' * 64}  {archive_path.name}\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["sh", "scripts/install.sh"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        env=os.environ
        | {
            "VERSION": "1.2.3",
            "ANKICLI_TARGET": "darwin-x64",
            "ANKICLI_RELEASES_BASE": release_root.as_uri(),
        },
        check=False,
    )

    assert result.returncode != 0
    assert "checksum mismatch" in result.stderr


@pytest.mark.smoke
def test_powershell_installer_script_is_version_and_path_aware(tmp_path: Path) -> None:
    if shutil.which("pwsh") is None:
        pytest.skip("pwsh is not installed")

    release_root = tmp_path / "release"
    payload_root = tmp_path / "payload" / "ankicli-1.2.3-windows-x64"
    payload_root.mkdir(parents=True)
    fake_binary = payload_root / "ankicli.exe"
    fake_binary.write_text("@echo off\r\necho ankicli 9.9.9\r\n", encoding="utf-8")
    readme = payload_root / "README-install.txt"
    readme.write_text("readme", encoding="utf-8")

    archive_path = release_root / "download" / "v1.2.3" / "ankicli-1.2.3-windows-x64.zip"
    archive_path.parent.mkdir(parents=True)
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.write(fake_binary, arcname=f"{payload_root.name}/ankicli.exe")
        archive.write(readme, arcname=f"{payload_root.name}/README-install.txt")

    checksum_path = archive_path.parent / "ankicli-1.2.3-checksums.txt"
    checksum_path.write_text(
        f"{'0' * 64}  prefix-{archive_path.name}\n"
        f"{_write_checksum(archive_path)}  {archive_path.name}\n",
        encoding="utf-8",
    )

    install_root = tmp_path / "install"
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            "scripts/install.ps1",
            "-Version",
            "1.2.3",
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        env=os.environ
        | {
            "ANKICLI_TARGET": "windows-x64",
            "ANKICLI_RELEASES_BASE": release_root.as_uri(),
            "ANKICLI_INSTALL_ROOT": str(install_root),
            "ANKICLI_SKIP_VERIFY": "1",
        },
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (install_root / "1.2.3" / "ankicli.exe").exists()


@pytest.mark.smoke
def test_powershell_installer_rejects_unsafe_version_before_install(tmp_path: Path) -> None:
    if shutil.which("pwsh") is None:
        pytest.skip("pwsh is not installed")

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    sentinel = outside_dir / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            "scripts/install.ps1",
            "-Version",
            "1/../../outside",
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        env=os.environ
        | {
            "ANKICLI_TARGET": "windows-x64",
            "ANKICLI_RELEASES_BASE": (tmp_path / "release").as_uri(),
            "ANKICLI_INSTALL_ROOT": str(tmp_path / "install"),
            "ANKICLI_SKIP_VERIFY": "1",
        },
        check=False,
    )

    assert result.returncode != 0
    assert "invalid release version" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "keep"


@pytest.mark.smoke
def test_powershell_installer_rejects_unknown_target_before_download(tmp_path: Path) -> None:
    if shutil.which("pwsh") is None:
        pytest.skip("pwsh is not installed")

    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            "scripts/install.ps1",
            "-Version",
            "latest",
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        env=os.environ
        | {
            "ANKICLI_TARGET": "../windows-x64",
            "ANKICLI_RELEASE_API": (tmp_path / "missing-release.json").as_uri(),
            "ANKICLI_RELEASES_BASE": (tmp_path / "release").as_uri(),
            "ANKICLI_INSTALL_ROOT": str(tmp_path / "install"),
            "ANKICLI_SKIP_VERIFY": "1",
        },
        check=False,
    )

    assert result.returncode != 0
    assert "invalid release target" in result.stderr
