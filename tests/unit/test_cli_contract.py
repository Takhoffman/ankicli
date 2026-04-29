from __future__ import annotations

import json
from pathlib import PurePath

import pytest

from ankicli import __version__
from tests.proof import proves


@pytest.mark.unit
@proves("doctor.env", "unit", "cli_contract")
def test_doctor_env_json_contract(runner) -> None:
    result = runner.invoke(args=["--json", "doctor", "env"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["backend"] == "python-anki"
    assert "anki_source_path" in payload["data"]
    assert "anki_source_import_path" in payload["data"]
    assert "anki_import_available" in payload["data"]
    assert "anki_module_path" in payload["data"]
    assert "anki_version" in payload["data"]
    assert "default_anki2_root" in payload["data"]
    assert "supported_runtime" in payload["data"]
    assert "runtime_failure_reason" in payload["data"]
    assert "credential_storage_backend" in payload["data"]
    assert "credential_storage_available" in payload["data"]
    assert "credential_storage_fallback" in payload["data"]
    assert "config_path" in payload["data"]


@pytest.mark.unit
def test_version_reports_package_version(runner) -> None:
    result = runner.invoke(args=["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


@pytest.mark.unit
def test_changelog_reports_latest_section_for_humans(runner) -> None:
    result = runner.invoke(args=["changelog"])

    assert result.exit_code == 0
    assert result.stdout.startswith("## 0.1.3")
    assert "# Changelog" not in result.stdout
    assert "Enforced the quality-matrix audit" in result.stdout


@pytest.mark.unit
def test_changelog_json_contract(runner) -> None:
    result = runner.invoke(args=["--json", "changelog"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["title"].startswith("0.1.3")
    assert payload["data"]["full"] is False
    assert payload["data"]["content"].startswith("## 0.1.3")
    assert payload["data"]["source"]


@pytest.mark.unit
def test_changelog_all_includes_full_markdown(runner) -> None:
    result = runner.invoke(args=["--json", "changelog", "--all"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["title"] == "Changelog"
    assert payload["data"]["full"] is True
    assert payload["data"]["content"].startswith("# Changelog")


@pytest.mark.unit
@proves("workspace.set", "unit", "cli_contract", "safety")
@proves("workspace.show", "unit", "cli_contract")
def test_workspace_set_and_show_contract(runner, tmp_path) -> None:
    env = {"ANKICLI_CONFIG_HOME": str(tmp_path)}

    set_result = runner.invoke(
        args=["--json", "workspace", "set", "--profile", "User 1"],
        env=env,
    )
    show_result = runner.invoke(args=["--json", "workspace", "show"], env=env)

    assert set_result.exit_code == 0
    assert show_result.exit_code == 0
    payload = json.loads(show_result.stdout)
    assert payload["data"]["config_path"] == str(
        tmp_path / "workspaces/default/config.json"
    )
    assert payload["data"]["active_workspace"] == "default"
    assert payload["data"]["selected_workspace"] == "default"
    assert payload["data"]["workspace_config"] == {
        "anki_profile": "User 1",
        "collection": None,
        "backend": None,
    }
    assert payload["data"]["active_target_source"] is None


@pytest.mark.unit
@proves("workspace.set", "unit", "cli_contract", "safety")
@proves("workspace.use", "unit", "cli_contract", "safety")
@proves("workspace.list", "unit", "cli_contract")
def test_workspace_supports_multiple_roots(runner, tmp_path) -> None:
    env = {"ANKICLI_CONFIG_HOME": str(tmp_path)}
    collection_path = tmp_path / "travel.anki2"

    set_result = runner.invoke(
        args=[
            "--json",
            "workspace",
            "set",
            "--name",
            "travel",
            "--collection",
            str(collection_path),
        ],
        env=env,
    )
    use_result = runner.invoke(
        args=["--json", "workspace", "use", "--name", "travel"],
        env=env,
    )
    list_result = runner.invoke(args=["--json", "workspace", "list"], env=env)

    assert set_result.exit_code == 0
    assert use_result.exit_code == 0
    assert list_result.exit_code == 0
    payload = json.loads(list_result.stdout)
    assert payload["data"]["active_workspace"] == "travel"
    assert payload["data"]["items"] == [
        {
            "name": "travel",
            "active": True,
            "root": str(tmp_path / "workspaces/travel"),
            "config_path": str(tmp_path / "workspaces/travel/config.json"),
            "config_exists": True,
            "anki_profile": None,
            "collection": str(collection_path),
            "backend": None,
        }
    ]


@pytest.mark.unit
@proves("workspace.clear", "unit", "cli_contract", "safety")
def test_workspace_clear_removes_saved_defaults(runner, tmp_path) -> None:
    env = {"ANKICLI_CONFIG_HOME": str(tmp_path)}

    set_result = runner.invoke(
        args=[
            "--json",
            "workspace",
            "set",
            "--profile",
            "User 1",
            "--backend",
            "ankiconnect",
        ],
        env=env,
    )
    clear_result = runner.invoke(
        args=["--json", "workspace", "clear", "--all"],
        env=env,
    )

    assert set_result.exit_code == 0
    assert clear_result.exit_code == 0
    payload = json.loads(clear_result.stdout)
    assert payload["data"]["workspace_config"] == {
        "anki_profile": None,
        "collection": None,
        "backend": None,
    }


@pytest.mark.unit
@proves("workspace.path", "unit", "cli_contract")
def test_workspace_path_json_contract(runner, tmp_path) -> None:
    env = {"ANKICLI_CONFIG_HOME": str(tmp_path)}

    result = runner.invoke(args=["--json", "workspace", "path"], env=env)

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["workspace_root"] == str(tmp_path / "workspaces/default")
    assert payload["data"]["config_path"] == str(tmp_path / "workspaces/default/config.json")


@pytest.mark.unit
def test_saved_collection_is_used_as_default_target(runner, tmp_path) -> None:
    env = {"ANKICLI_CONFIG_HOME": str(tmp_path)}
    collection_path = tmp_path / "missing.anki2"

    runner.invoke(
        args=["--json", "workspace", "set", "--collection", str(collection_path)],
        env=env,
    )
    result = runner.invoke(args=["--json", "collection", "info"], env=env)

    assert result.exit_code == 5
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_NOT_FOUND"
    assert payload["error"]["details"]["path"] == str(collection_path)


@pytest.mark.unit
def test_workspace_global_option_selects_named_target(runner, tmp_path) -> None:
    env = {"ANKICLI_CONFIG_HOME": str(tmp_path)}
    collection_path = tmp_path / "travel.anki2"

    runner.invoke(
        args=[
            "--json",
            "workspace",
            "set",
            "--name",
            "travel",
            "--collection",
            str(collection_path),
        ],
        env=env,
    )
    result = runner.invoke(
        args=["--json", "--workspace", "travel", "collection", "info"],
        env=env,
    )

    assert result.exit_code == 5
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_NOT_FOUND"
    assert payload["error"]["details"]["path"] == str(collection_path)


@pytest.mark.unit
def test_configure_reports_config_and_steps(runner, tmp_path) -> None:
    result = runner.invoke(
        args=["--json", "configure"],
        env={"ANKICLI_CONFIG_HOME": str(tmp_path)},
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["workspace"]["config_path"] == str(
        tmp_path / "workspaces/default/config.json"
    )
    assert payload["data"]["credential_storage"]["backend"]
    assert any("collection info" in step for step in payload["data"]["steps"])


@pytest.mark.unit
def test_configure_json_output_is_structured(runner, tmp_path) -> None:
    result = runner.invoke(
        args=["--json", "configure"],
        env={"ANKICLI_CONFIG_HOME": str(tmp_path)},
    )

    assert result.exit_code == 0
    assert "A N K I C L I" not in result.stdout
    assert "┌" not in result.stdout
    json.loads(result.stdout)


@pytest.mark.unit
def test_configure_human_output_is_walkthrough(runner, tmp_path) -> None:
    result = runner.invoke(
        args=["configure", "--skip-sync", "--skip-skills"],
        env={
            "ANKICLI_CONFIG_HOME": str(tmp_path),
            "ANKICLI_ANKI2_ROOT": str(tmp_path / "missing-anki-root"),
        },
        input="\n",
    )

    assert result.exit_code == 0
    assert "ankicli configure" in result.stdout
    assert "Recommended: skip collection setup for now." in result.stdout
    assert "Skipped. You can do this later by running: ankicli configure" in result.stdout
    assert "Collection target" in result.stdout
    assert "Try next" in result.stdout
    assert "Configure later" in result.stdout
    assert not result.stdout.lstrip().startswith("{")


@pytest.mark.unit
@proves("skill.list", "unit", "cli_contract")
def test_skill_list_json_contract(runner) -> None:
    result = runner.invoke(args=["--json", "skill", "list"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert [item["name"] for item in payload["data"]["items"]] == ["ankicli"]
    assert PurePath(payload["data"]["targets"]["codex"]).parts[-2:] == (".codex", "skills")
    assert PurePath(payload["data"]["targets"]["claude"]).parts[-2:] == (".claude", "skills")
    assert PurePath(payload["data"]["targets"]["openclaw"]).parts[-2:] == (
        ".openclaw",
        "skills",
    )


@pytest.mark.unit
@proves("skill.install", "unit", "cli_contract", "safety")
def test_skill_install_copies_bundled_bundle_to_custom_path(runner, tmp_path) -> None:
    skill_root = tmp_path / "agent-skills"

    result = runner.invoke(
        args=[
            "--json",
            "skill",
            "install",
            "--path",
            str(skill_root),
        ],
    )
    second_result = runner.invoke(
        args=[
            "--json",
            "skill",
            "install",
            "--path",
            str(skill_root),
        ],
    )

    assert result.exit_code == 0
    assert (skill_root / "ankicli" / "SKILL.md").exists()
    assert (skill_root / "ankicli" / "references" / "study.md").exists()
    payload = json.loads(result.stdout)
    assert payload["data"]["targets"][0]["target"] == "custom"
    assert payload["data"]["targets"][0]["bundle"]["status"] == "installed"
    second_payload = json.loads(second_result.stdout)
    assert second_payload["data"]["targets"][0]["bundle"]["status"] == "skipped"
    assert second_payload["data"]["targets"][0]["bundle"]["reason"] == "already_exists"


@pytest.mark.unit
def test_skill_install_help_does_not_expose_removed_skill_selector(runner) -> None:
    result = runner.invoke(args=["skill", "install", "--help"])

    assert result.exit_code == 0
    assert "--skill" not in result.stdout


@pytest.mark.unit
def test_configure_can_install_skills_to_custom_path(runner, tmp_path) -> None:
    skill_root = tmp_path / "agent-skills"
    result = runner.invoke(
        args=[
            "configure",
            "--skip-sync",
            "--install-skills",
            "--skill-path",
            str(skill_root),
        ],
        env={
            "ANKICLI_CONFIG_HOME": str(tmp_path / "config"),
            "ANKICLI_ANKI2_ROOT": str(tmp_path / "missing-anki-root"),
        },
        input="\n",
    )

    assert result.exit_code == 0
    assert "ankicli skill" in result.stdout
    assert "installed: custom" in result.stdout
    assert (skill_root / "ankicli" / "SKILL.md").exists()
    assert (skill_root / "ankicli" / "references" / "diagnostics.md").exists()


@pytest.mark.unit
def test_configure_default_skill_prompt_installs_detected_agent_homes(runner, tmp_path) -> None:
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    (home / ".claude").mkdir(parents=True)
    (home / ".openclaw").mkdir(parents=True)

    result = runner.invoke(
        args=["configure", "--skip-sync"],
        env={
            "HOME": str(home),
            "USERPROFILE": str(home),
            "ANKICLI_CONFIG_HOME": str(tmp_path / "config"),
            "ANKICLI_ANKI2_ROOT": str(tmp_path / "missing-anki-root"),
        },
        input="\n\n",
    )

    assert result.exit_code == 0
    assert "Install the ankicli skill?" in result.stdout
    assert "codex" in result.stdout
    assert "claude" in result.stdout
    assert "openclaw" in result.stdout
    assert "installed: codex" in result.stdout
    assert "installed: claude" in result.stdout
    assert "installed: openclaw" in result.stdout
    assert (home / ".codex/skills/ankicli/SKILL.md").exists()
    assert (home / ".claude/skills/ankicli/SKILL.md").exists()
    assert (home / ".openclaw/skills/ankicli/SKILL.md").exists()
    assert (home / ".codex/skills/ankicli/references/study.md").exists()


@pytest.mark.unit
@proves("collection.info", "unit", "cli_contract", "failure")
def test_collection_info_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "collection", "info"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_collection_and_profile_are_mutually_exclusive(runner, tmp_path) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "--profile",
            "User 1",
            "collection",
            "info",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_collection_info_missing_file_is_structured_error(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "collection", "info"],
    )

    assert result.exit_code == 5
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_NOT_FOUND"


@pytest.mark.unit
@proves("backend.capabilities", "unit", "cli_contract")
def test_ankiconnect_backend_capabilities_expose_operation_matrix(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "capabilities"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    operations = payload["data"]["supported_operations"]
    assert operations["note.add"] is True
    assert operations["deck.create"] is True
    assert operations["deck.rename"] is True
    assert operations["deck.delete"] is True
    assert operations["deck.reparent"] is True
    assert operations["media.attach"] is True
    assert operations["note.delete"] is True
    assert operations["tag.rename"] is True
    assert operations["tag.delete"] is True
    assert operations["tag.reparent"] is True
    assert operations["collection.validate"] is False
    assert operations["media.list"] is True
    assert operations["media.check"] is True
    assert operations["media.resolve_path"] is True
    assert operations["auth.status"] is False
    assert operations["sync.run"] is False
    assert operations["profile.list"] is False
    assert operations["backup.restore"] is False


@pytest.mark.unit
@proves("backend.list", "unit", "cli_contract")
def test_backend_list_reports_supported_backends(runner) -> None:
    result = runner.invoke(args=["--json", "backend", "list"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["items"] == ["python-anki", "ankiconnect"]


@pytest.mark.unit
@proves("backend.info", "unit", "cli_contract")
def test_backend_info_reports_active_backend(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "info"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["name"] == "ankiconnect"
    assert payload["data"]["capabilities"]["backend"] == "ankiconnect"


@pytest.mark.unit
@proves("backend.test-connection", "unit", "cli_contract")
def test_backend_test_connection_reports_probe_result(runner) -> None:
    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "backend", "test-connection"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["name"] == "ankiconnect"
    assert "available" in payload["data"]
    assert "ok" in payload["data"]


@pytest.mark.unit
@proves("doctor.backend", "unit", "cli_contract")
def test_doctor_backend_reports_backend_summary(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "doctor", "backend"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["name"] == "ankiconnect"
    assert "supported_runtime" in payload["data"]


@pytest.mark.unit
@proves("doctor.capabilities", "unit", "cli_contract")
def test_doctor_capabilities_reports_operation_summary(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "doctor", "capabilities"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert "supported_operation_count" in payload["data"]
    assert "unsupported_operation_count" in payload["data"]


@pytest.mark.unit
@proves("auth.status", "unit", "cli_contract", "failure")
def test_auth_status_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "auth", "status"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "auth.status",
    }


@pytest.mark.unit
@proves("auth.login", "unit", "cli_contract", "failure")
def test_auth_login_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "--backend",
            "ankiconnect",
            "auth",
            "login",
            "--username",
            "user",
            "--password",
            "secret",
        ],
    )

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "auth.login",
    }


@pytest.mark.unit
@proves("auth.logout", "unit", "cli_contract", "failure")
def test_auth_logout_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "auth", "logout"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "auth.logout",
    }


@pytest.mark.unit
@proves("profile.list", "unit", "cli_contract", "failure")
def test_profile_list_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "profile", "list"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "profile.list",
    }


@pytest.mark.unit
@proves("profile.get", "unit", "cli_contract", "failure")
def test_profile_get_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "profile", "get", "--name", "User 1"],
    )

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "profile.get",
    }


@pytest.mark.unit
@proves("profile.default", "unit", "cli_contract", "failure")
def test_profile_default_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "profile", "default"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "profile.default",
    }


@pytest.mark.unit
@proves("profile.resolve", "unit", "cli_contract", "failure")
def test_profile_resolve_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "profile", "resolve", "--name", "User 1"],
    )

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "profile.resolve",
    }


@pytest.mark.unit
@proves("backup.status", "unit", "cli_contract", "failure")
def test_backup_status_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backup", "status"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "backup.status",
    }


@pytest.mark.unit
@proves("backup.list", "unit", "cli_contract", "failure")
def test_backup_list_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backup", "list"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "backup.list",
    }


@pytest.mark.unit
@proves("backup.create", "unit", "cli_contract", "failure")
def test_backup_create_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backup", "create"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "backup.create",
    }


@pytest.mark.unit
@proves("backup.get", "unit", "cli_contract", "failure")
def test_backup_get_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "backup", "get", "--name", "backup.colpkg"],
    )

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "backup.get",
    }


@pytest.mark.unit
@proves("backup.restore", "unit", "cli_contract", "failure", "safety")
def test_backup_restore_requires_yes(runner, tmp_path) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "backup",
            "restore",
            "--name",
            "backup-2026.colpkg",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("sync.pull", "unit", "cli_contract", "failure")
def test_sync_pull_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "sync", "pull"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "sync.pull",
    }


@pytest.mark.unit
@proves("sync.push", "unit", "cli_contract", "failure")
def test_sync_push_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "sync", "push"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "sync.push",
    }


@pytest.mark.unit
@proves("sync.status", "unit", "cli_contract", "failure")
def test_sync_status_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "sync", "status"])

    payload = json.loads(result.stdout)
    assert result.exit_code in {4, 14}
    assert payload["error"]["code"] in {"COLLECTION_REQUIRED", "BACKEND_OPERATION_UNSUPPORTED"}


@pytest.mark.unit
@proves("sync.run", "unit", "cli_contract", "failure")
def test_sync_run_on_ankiconnect_is_structured_unsupported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "sync", "run"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "sync.run",
    }


@pytest.mark.unit
@proves("deck.list", "unit", "cli_contract", "failure")
def test_deck_list_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "deck", "list"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("media.orphaned", "unit", "cli_contract", "failure")
def test_media_orphaned_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "media", "orphaned"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("media.list", "unit", "cli_contract", "failure")
def test_media_list_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "media", "list"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("media.resolve-path", "unit", "cli_contract", "failure")
def test_media_resolve_path_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "media", "resolve-path", "--name", "used.png"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("media.check", "unit", "cli_contract", "failure")
def test_media_check_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "media", "check"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("media.check", "unit", "cli_contract")
def test_ankiconnect_media_check_is_supported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "capabilities"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["supported_operations"]["media.check"] is True


@pytest.mark.unit
@proves("media.attach", "unit", "cli_contract", "failure")
def test_media_attach_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "media", "attach", "--source", "/tmp/file.txt", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("media.attach", "cli_contract", "safety")
def test_media_attach_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    source_path = tmp_path / "file.txt"
    source_path.write_text("hello")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "media",
            "attach",
            "--source",
            str(source_path),
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("tag.apply", "unit", "cli_contract", "failure")
def test_tag_apply_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "tag", "apply", "--id", "101", "--tag", "review", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("tag.remove", "cli_contract", "failure")
def test_tag_remove_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "tag", "remove", "--id", "101", "--tag", "review", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("tag.remove", "unit", "cli_contract", "safety")
def test_tag_remove_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "remove",
            "--id",
            "101",
            "--tag",
            "review",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("deck.get", "unit", "cli_contract", "failure")
def test_deck_get_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "deck", "get", "--name", "Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("deck.stats", "unit", "cli_contract", "failure")
def test_deck_stats_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "deck", "stats", "--name", "Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("deck.create", "unit", "cli_contract", "failure")
def test_deck_create_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "deck", "create", "--name", "French", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("deck.rename", "unit", "cli_contract", "failure")
def test_deck_rename_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "deck", "rename", "--name", "Default", "--to", "French", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("deck.delete", "unit", "cli_contract", "failure")
def test_deck_delete_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "deck", "delete", "--name", "Default", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("deck.reparent", "unit", "cli_contract", "failure")
def test_deck_reparent_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "deck",
            "reparent",
            "--name",
            "Default",
            "--to-parent",
            "Parent",
            "--dry-run",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("deck.create", "cli_contract", "safety")
def test_deck_create_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "deck", "create", "--name", "French"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("deck.rename", "cli_contract", "safety")
def test_deck_rename_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "deck",
            "rename",
            "--name",
            "Default",
            "--to",
            "French",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("deck.delete", "cli_contract", "safety")
def test_deck_delete_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "deck",
            "delete",
            "--name",
            "Default",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("deck.reparent", "cli_contract", "safety")
def test_deck_reparent_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "deck",
            "reparent",
            "--name",
            "Default",
            "--to-parent",
            "Parent",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("deck.create", "cli_contract")
@proves("deck.rename", "cli_contract")
def test_ankiconnect_deck_create_and_rename_are_supported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "capabilities"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    operations = payload["data"]["supported_operations"]
    assert operations["deck.create"] is True
    assert operations["deck.rename"] is True


@pytest.mark.unit
@proves("deck.delete", "cli_contract")
def test_ankiconnect_deck_delete_is_supported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "capabilities"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["supported_operations"]["deck.delete"] is True


@pytest.mark.unit
@proves("model.list", "unit", "cli_contract", "failure")
def test_model_list_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "model", "list"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("model.get", "unit", "cli_contract", "failure")
def test_model_get_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "model", "get", "--name", "Basic"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("model.fields", "unit", "cli_contract", "failure")
def test_model_fields_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "model", "fields", "--name", "Basic"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("model.templates", "unit", "cli_contract", "failure")
def test_model_templates_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "model", "templates", "--name", "Basic"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("model.validate-note", "unit", "cli_contract", "failure")
def test_model_validate_note_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "model",
            "validate-note",
            "--model",
            "Basic",
            "--field",
            "Front=hello",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("tag.list", "unit", "cli_contract", "failure")
def test_tag_list_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "tag", "list"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("tag.rename", "unit", "cli_contract", "failure")
def test_tag_rename_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "tag",
            "rename",
            "--name",
            "tag1",
            "--to",
            "tag2",
            "--dry-run",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("tag.delete", "unit", "cli_contract", "failure")
def test_tag_delete_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "tag", "delete", "--tag", "tag1", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("tag.reparent", "unit", "cli_contract", "failure")
def test_tag_reparent_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "tag", "reparent", "--tag", "tag1", "--to-parent", "tag2", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("note.delete", "unit", "cli_contract")
def test_ankiconnect_note_delete_is_supported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "capabilities"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["supported_operations"]["note.delete"] is True


@pytest.mark.unit
@proves("tag.rename", "cli_contract")
def test_ankiconnect_tag_rename_is_supported(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "backend", "capabilities"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["supported_operations"]["tag.rename"] is True


@pytest.mark.unit
@proves("search.notes", "unit", "cli_contract", "failure")
def test_search_notes_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "search", "notes", "--query", "deck:Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("search.cards", "unit", "cli_contract", "failure")
def test_search_cards_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "search", "cards", "--query", "deck:Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("search.count", "unit", "cli_contract", "failure")
def test_search_count_invalid_kind_is_validation_error(runner) -> None:
    result = runner.invoke(args=["--json", "search", "count", "--kind", "bogus", "--query", ""])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
@proves("search.preview", "unit", "cli_contract", "failure")
def test_search_preview_invalid_kind_is_validation_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "search", "preview", "--kind", "bogus", "--query", ""],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
@proves("collection.stats", "unit", "cli_contract", "failure")
def test_collection_stats_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "collection", "stats"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("doctor.collection", "unit", "cli_contract", "failure")
def test_doctor_collection_unsupported_on_ankiconnect_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "doctor", "collection"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "doctor.collection",
    }


@pytest.mark.unit
@proves("doctor.safety", "unit", "cli_contract", "failure")
def test_doctor_safety_unsupported_on_ankiconnect_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "doctor", "safety"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "doctor.safety",
    }


@pytest.mark.unit
@proves("collection.validate", "unit", "cli_contract", "failure")
def test_collection_validate_unsupported_on_ankiconnect_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "collection", "validate"])

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "collection.validate",
    }


@pytest.mark.unit
@proves("collection.lock-status", "unit", "cli_contract", "failure")
def test_collection_lock_status_unsupported_on_ankiconnect_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "--backend", "ankiconnect", "collection", "lock-status"],
    )

    assert result.exit_code == 14
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "BACKEND_OPERATION_UNSUPPORTED"
    assert payload["error"]["details"] == {
        "backend": "ankiconnect",
        "operation": "collection.lock_status",
    }


@pytest.mark.unit
@proves("export.notes", "unit", "cli_contract", "failure")
def test_export_notes_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "export", "notes", "--query", "deck:Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("export.cards", "unit", "cli_contract", "failure")
def test_export_cards_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "export", "cards", "--query", "deck:Default"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
def test_export_notes_ndjson_emits_one_record_per_line(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "export",
            "notes",
            "--query",
            "deck:Default",
            "--ndjson",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_NOT_FOUND"


@pytest.mark.unit
def test_export_cards_ndjson_emits_one_record_per_line(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "export",
            "cards",
            "--query",
            "deck:Default",
            "--ndjson",
        ],
    )

    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_NOT_FOUND"


@pytest.mark.unit
@proves("import.notes", "unit", "cli_contract", "failure")
def test_import_notes_without_path_is_structured_error(runner, tmp_path) -> None:
    input_path = tmp_path / "notes.json"
    input_path.write_text("[]")

    result = runner.invoke(
        args=["--json", "import", "notes", "--input", str(input_path), "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("import.patch", "unit", "cli_contract", "failure")
def test_import_patch_without_path_is_structured_error(runner, tmp_path) -> None:
    input_path = tmp_path / "patches.json"
    input_path.write_text("[]")

    result = runner.invoke(
        args=["--json", "import", "patch", "--input", str(input_path), "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("note.get", "unit", "cli_contract", "failure")
def test_note_get_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "note", "get", "--id", "123"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("note.fields", "unit", "cli_contract", "failure")
def test_note_fields_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "note", "fields", "--id", "123"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("card.get", "unit", "cli_contract", "failure")
def test_card_get_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "card", "get", "--id", "123"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("card.suspend", "unit", "cli_contract", "failure")
def test_card_suspend_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "card", "suspend", "--id", "201", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("card.unsuspend", "unit", "cli_contract", "failure")
def test_card_unsuspend_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "card", "unsuspend", "--id", "201", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("card.suspend", "cli_contract", "safety")
def test_card_suspend_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "card", "suspend", "--id", "201"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("card.unsuspend", "cli_contract", "safety")
def test_card_unsuspend_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "card", "unsuspend", "--id", "201"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("note.add", "unit", "cli_contract", "failure")
def test_note_add_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "note",
            "add",
            "--deck",
            "Default",
            "--model",
            "Basic",
            "--field",
            "Front=hello",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("note.update", "unit", "cli_contract", "failure")
def test_note_update_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=[
            "--json",
            "note",
            "update",
            "--id",
            "123",
            "--field",
            "Front=hello",
        ],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("note.delete", "unit", "cli_contract", "failure")
def test_note_delete_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(args=["--json", "note", "delete", "--id", "123", "--dry-run"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("note.add-tags", "unit", "cli_contract", "failure")
def test_note_add_tags_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "note", "add-tags", "--id", "123", "--tag", "tag1", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("note.remove-tags", "unit", "cli_contract", "failure")
def test_note_remove_tags_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "note", "remove-tags", "--id", "123", "--tag", "tag1", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("note.delete", "cli_contract", "safety")
def test_note_delete_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=["--json", "--collection", str(collection_path), "note", "delete", "--id", "123"],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("note.add-tags", "cli_contract", "safety")
def test_note_add_tags_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "add-tags",
            "--id",
            "123",
            "--tag",
            "tag1",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("note.remove-tags", "cli_contract", "safety")
def test_note_remove_tags_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "remove-tags",
            "--id",
            "123",
            "--tag",
            "tag1",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("note.move-deck", "unit", "cli_contract", "failure")
def test_note_move_deck_without_path_is_structured_error(runner) -> None:
    result = runner.invoke(
        args=["--json", "note", "move-deck", "--id", "123", "--deck", "Default", "--dry-run"],
    )

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "COLLECTION_REQUIRED"


@pytest.mark.unit
@proves("note.move-deck", "cli_contract", "safety")
def test_note_move_deck_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "move-deck",
            "--id",
            "123",
            "--deck",
            "Default",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_note_tag_commands_require_a_tag_value(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    add_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "add-tags",
            "--id",
            "123",
            "--dry-run",
        ],
    )
    remove_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "note",
            "remove-tags",
            "--id",
            "123",
            "--dry-run",
        ],
    )

    assert add_result.exit_code == 2
    assert remove_result.exit_code == 2
    assert json.loads(add_result.stdout)["error"]["code"] == "VALIDATION_ERROR"
    assert json.loads(remove_result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
@proves("tag.rename", "cli_contract", "safety")
def test_tag_rename_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "rename",
            "--name",
            "tag1",
            "--to",
            "tag2",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
@proves("tag.delete", "cli_contract", "safety")
def test_tag_delete_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "delete",
            "--tag",
            "tag1",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_tag_delete_requires_a_tag_value(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "delete",
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
@proves("tag.reparent", "cli_contract", "safety")
def test_tag_reparent_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "reparent",
            "--tag",
            "tag1",
            "--to-parent",
            "tag2",
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_tag_reparent_requires_a_tag_value(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "reparent",
            "--to-parent",
            "tag2",
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_tag_rename_rejects_empty_or_same_names(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    empty_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "rename",
            "--name",
            " ",
            "--to",
            "tag2",
            "--dry-run",
        ],
    )
    same_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "rename",
            "--name",
            "tag1",
            "--to",
            "tag1",
            "--dry-run",
        ],
    )

    assert empty_result.exit_code == 2
    assert same_result.exit_code == 2
    assert json.loads(empty_result.stdout)["error"]["code"] == "VALIDATION_ERROR"
    assert json.loads(same_result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_tag_reparent_rejects_same_parent_as_tag(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "tag",
            "reparent",
            "--tag",
            "tag1",
            "--to-parent",
            "tag1",
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
@proves("import.notes", "cli_contract", "safety")
def test_import_notes_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "notes.json"
    input_path.write_text("[]")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "notes",
            "--input",
            str(input_path),
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_import_notes_rejects_missing_input(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "notes.json"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "notes",
            "--input",
            str(input_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
@proves("import.patch", "cli_contract", "safety")
def test_import_patch_requires_confirmation_or_dry_run(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "patches.json"
    input_path.write_text("[]")

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "patch",
            "--input",
            str(input_path),
        ],
    )

    assert result.exit_code == 12
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "UNSAFE_OPERATION"


@pytest.mark.unit
def test_import_patch_rejects_missing_input(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "patches.json"

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "patch",
            "--input",
            str(input_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_import_notes_accepts_stdin_json(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    payload = json.dumps(
        {
            "items": [
                {
                    "deck": "Default",
                    "model": "Basic",
                    "fields": {"Front": "hello"},
                    "tags": [],
                },
            ],
        },
    )

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "notes",
            "--stdin-json",
            "--dry-run",
        ],
        input=payload,
    )

    payload_json = json.loads(result.stdout)
    assert payload_json["error"]["code"] in {
        "COLLECTION_NOT_FOUND",
        "DECK_NOT_FOUND",
        "MODEL_NOT_FOUND",
    }


@pytest.mark.unit
def test_import_patch_accepts_stdin_json(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    payload = json.dumps({"items": [{"id": 101, "fields": {"Back": "updated"}}]})

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "patch",
            "--stdin-json",
            "--dry-run",
        ],
        input=payload,
    )

    payload_json = json.loads(result.stdout)
    assert payload_json["error"]["code"] in {"COLLECTION_NOT_FOUND", "NOTE_NOT_FOUND"}


@pytest.mark.unit
def test_import_commands_require_exactly_one_input_source(runner, tmp_path) -> None:
    collection_path = tmp_path / "missing.anki2"
    input_path = tmp_path / "notes.json"
    input_path.write_text("[]")

    notes_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "notes",
            "--input",
            str(input_path),
            "--stdin-json",
            "--dry-run",
        ],
        input="[]",
    )
    patch_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "import",
            "patch",
            "--input",
            str(input_path),
            "--stdin-json",
            "--dry-run",
        ],
        input="[]",
    )

    assert notes_result.exit_code == 2
    assert patch_result.exit_code == 2
    assert json.loads(notes_result.stdout)["error"]["code"] == "VALIDATION_ERROR"
    assert json.loads(patch_result.stdout)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.unit
def test_not_implemented_command_is_stable_error(runner) -> None:
    result = runner.invoke(args=["--json", "backend", "list", "extra"])

    assert result.exit_code != 0
