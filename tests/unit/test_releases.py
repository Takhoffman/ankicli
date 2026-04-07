from __future__ import annotations

import pytest

from ankicli.app.releases import (
    RELEASE_TARGETS,
    artifact_filename,
    checksums_filename,
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
