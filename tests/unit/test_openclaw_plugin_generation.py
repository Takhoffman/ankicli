from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.unit
def test_openclaw_plugin_catalog_generation_contract() -> None:
    node = shutil.which("node")
    if node is None:
      pytest.skip("node is required for the OpenClaw plugin generation contract test")

    repo_root = Path(__file__).resolve().parents[2]
    test_path = repo_root / "integrations" / "openclaw-plugin" / "test" / "catalog-plugin.test.mjs"
    result = subprocess.run(
        [node, "--test", str(test_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.unit
def test_generated_anki_study_skill_mentions_media_output_guidance() -> None:
    skill_path = (
        Path(__file__).resolve().parents[2]
        / "integrations"
        / "openclaw-plugin"
        / "skills"
        / "anki-study"
        / "SKILL.md"
    )
    content = skill_path.read_text()

    assert "anki_study_card_details" in content
    assert "include media in the same response when it helps the learner" in content
    assert "current_card.view" in content
    assert "present_view" not in content
    assert "current_card.tutoring_summary" in content
