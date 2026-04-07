"""Shared release artifact metadata for installers, docs, and packaging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReleaseTarget:
    runner_os: str
    os_slug: str
    arch_slug: str
    archive_ext: str

    @property
    def asset_suffix(self) -> str:
        return f"{self.os_slug}-{self.arch_slug}"


RELEASE_TARGETS: dict[str, ReleaseTarget] = {
    "darwin-x64": ReleaseTarget(
        runner_os="macos",
        os_slug="darwin",
        arch_slug="x64",
        archive_ext=".tar.gz",
    ),
    "darwin-arm64": ReleaseTarget(
        runner_os="macos",
        os_slug="darwin",
        arch_slug="arm64",
        archive_ext=".tar.gz",
    ),
    "linux-x64": ReleaseTarget(
        runner_os="linux",
        os_slug="linux",
        arch_slug="x64",
        archive_ext=".tar.gz",
    ),
    "windows-x64": ReleaseTarget(
        runner_os="windows",
        os_slug="windows",
        arch_slug="x64",
        archive_ext=".zip",
    ),
}


def artifact_basename(version: str, target_id: str) -> str:
    target = RELEASE_TARGETS[target_id]
    return f"ankicli-{version}-{target.asset_suffix}"


def artifact_filename(version: str, target_id: str) -> str:
    target = RELEASE_TARGETS[target_id]
    return f"{artifact_basename(version, target_id)}{target.archive_ext}"


def checksums_filename(version: str) -> str:
    return f"ankicli-{version}-checksums.txt"
