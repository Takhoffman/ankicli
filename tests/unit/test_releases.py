from __future__ import annotations

import pytest

from ankicli.app.releases import (
    RELEASE_TARGETS,
    artifact_filename,
    checksums_filename,
)
from scripts.validate_release_version import validate_release_version


def _write_release_version_files(
    tmp_path,
    *,
    project_version: str,
    package_version: str,
    site_version: str,
) -> None:
    (tmp_path / "src" / "ankicli").mkdir(parents=True)
    (tmp_path / "site").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "anki-agent-toolkit"\nversion = "{project_version}"\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "ankicli" / "__init__.py").write_text(
        f'__version__ = "{package_version}"\n',
        encoding="utf-8",
    )
    (tmp_path / "site" / "package.json").write_text(
        f'{{"name":"ankicli-site","version":"{site_version}"}}\n',
        encoding="utf-8",
    )


@pytest.mark.unit
def test_release_targets_cover_expected_platforms() -> None:
    assert set(RELEASE_TARGETS) == {
        "darwin-x64",
        "darwin-arm64",
        "linux-x64",
        "windows-x64",
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    ("target_id", "expected"),
    [
        ("darwin-x64", "ankicli-0.1.0-darwin-x64.tar.gz"),
        ("darwin-arm64", "ankicli-0.1.0-darwin-arm64.tar.gz"),
        ("linux-x64", "ankicli-0.1.0-linux-x64.tar.gz"),
        ("windows-x64", "ankicli-0.1.0-windows-x64.zip"),
    ],
)
def test_artifact_filename_matches_release_contract(target_id: str, expected: str) -> None:
    assert artifact_filename("0.1.0", target_id) == expected


@pytest.mark.unit
def test_checksums_filename_matches_release_contract() -> None:
    assert checksums_filename("0.1.0") == "ankicli-0.1.0-checksums.txt"


@pytest.mark.unit
def test_release_version_validation_accepts_matching_tag(tmp_path) -> None:
    _write_release_version_files(
        tmp_path,
        project_version="0.1.2",
        package_version="0.1.2",
        site_version="0.1.2",
    )

    assert validate_release_version(root=tmp_path, tag_name="v0.1.2") == []


@pytest.mark.unit
def test_release_version_validation_reports_mismatched_project_files(tmp_path) -> None:
    _write_release_version_files(
        tmp_path,
        project_version="0.1.1",
        package_version="0.1.1",
        site_version="0.1.2",
    )

    result = validate_release_version(root=tmp_path, tag_name="v0.1.2")

    assert result == [
        "pyproject.toml declares '0.1.1'; expected '0.1.2'",
        "src/ankicli/__init__.py declares '0.1.1'; expected '0.1.2'",
    ]
