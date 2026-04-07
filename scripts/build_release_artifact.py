"""Build a standalone platform archive for GitHub Releases."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

from ankicli import __version__
from ankicli.app.releases import (
    RELEASE_TARGETS,
    artifact_basename,
    artifact_filename,
    checksums_filename,
)

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist" / "release"
PYINSTALLER_DIST_DIR = ROOT / "dist" / "pyinstaller"


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _readme_text() -> str:
    return (
        "ankicli standalone install\n"
        "\n"
        "This archive contains a self-contained ankicli executable.\n"
        "Install the ankicli binary into a user-local directory on PATH.\n"
        "\n"
        "Recommended user-local install locations:\n"
        "- macOS/Linux: ~/.local/bin\n"
        "- Windows: %LOCALAPPDATA%\\Programs\\ankicli\n"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_with_pyinstaller() -> None:
    if PYINSTALLER_DIST_DIR.exists():
        shutil.rmtree(PYINSTALLER_DIST_DIR)
    command = [
        "uv",
        "run",
        "--extra",
        "dev",
        "python",
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "ankicli",
        "--distpath",
        str(PYINSTALLER_DIST_DIR),
        "--paths",
        "src",
        "--collect-all",
        "anki",
        "--collect-all",
        "keyring",
        "src/ankicli/main.py",
    ]
    _run(command)


def _copy_payload(target_id: str) -> tuple[Path, str]:
    target = RELEASE_TARGETS[target_id]
    payload_root = Path(tempfile.mkdtemp(prefix="ankicli-release-"))
    install_root = payload_root / artifact_basename(__version__, target_id)
    install_root.mkdir(parents=True, exist_ok=True)

    source_dir = PYINSTALLER_DIST_DIR / "ankicli"
    if not source_dir.exists():
        raise FileNotFoundError(f"PyInstaller output missing: {source_dir}")

    for child in source_dir.iterdir():
        destination = install_root / child.name
        if child.is_dir():
            shutil.copytree(child, destination)
        else:
            shutil.copy2(child, destination)

    executable_name = "ankicli.exe" if target.runner_os == "windows" else "ankicli"
    executable_path = install_root / executable_name
    if target.runner_os != "windows" and executable_path.exists():
        executable_path.chmod(0o755)

    (install_root / "README-install.txt").write_text(_readme_text(), encoding="utf-8")
    return install_root, executable_name


def _archive_directory(source_dir: Path, *, version: str, target_id: str) -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = DIST_DIR / artifact_filename(version, target_id)
    if archive_path.exists():
        archive_path.unlink()

    target = RELEASE_TARGETS[target_id]
    if target.archive_ext == ".zip":
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(source_dir.rglob("*")):
                archive.write(path, path.relative_to(source_dir.parent))
    else:
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(source_dir, arcname=source_dir.name)
    return archive_path


def _write_checksums(version: str, archive_path: Path) -> Path:
    checksums_path = DIST_DIR / checksums_filename(version)
    line = f"{_sha256(archive_path)}  {archive_path.name}\n"
    mode = "a" if checksums_path.exists() else "w"
    with checksums_path.open(mode, encoding="utf-8") as handle:
        handle.write(line)
    return checksums_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, choices=sorted(RELEASE_TARGETS))
    parser.add_argument("--version", default=__version__)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("PYTHONUTF8", "1")

    if not args.skip_build:
        _build_with_pyinstaller()

    install_root, _ = _copy_payload(args.target)
    archive_path = _archive_directory(install_root, version=args.version, target_id=args.target)
    checksums_path = _write_checksums(args.version, archive_path)

    print(f"archive={archive_path}")
    print(f"checksums={checksums_path}")


if __name__ == "__main__":
    main()
