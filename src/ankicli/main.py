"""CLI entrypoint."""

from __future__ import annotations

from typing import Annotated

import typer

from ankicli import __version__
from ankicli.app.catalog import catalog_snapshot
from ankicli.app.changelog import changelog_report
from ankicli.app.config import (
    active_workspace,
    list_workspaces,
    load_workspace_config,
    normalize_workspace_name,
    save_workspace_config,
    set_active_workspace,
    workspace_config_path,
    workspace_item,
    workspace_report,
)
from ankicli.app.credentials import probe_default_credential_store
from ankicli.app.errors import AnkiCliError, ValidationError
from ankicli.app.output import (
    error_envelope,
    render_human,
    render_json,
    render_ndjson,
    success_envelope,
)
from ankicli.app.profiles import ProfileResolver
from ankicli.app.services import (
    AuthService,
    BackendService,
    BackupService,
    CardService,
    CatalogService,
    CollectionService,
    DeckService,
    DoctorService,
    ExportService,
    ImportService,
    MediaService,
    NoteService,
    ProfileService,
    SearchService,
    SyncService,
    TagService,
)
from ankicli.app.skills import (
    detected_skill_targets,
    skill_list_payload,
)
from ankicli.app.skills import (
    install_skills as install_agent_skills,
)
from ankicli.app.study import StudyService
from ankicli.runtime import Settings, get_backend

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Inspect and mutate local Anki collections.",
)
doctor_app = typer.Typer(no_args_is_help=True, help="Inspect environment and backend state.")
backend_app = typer.Typer(no_args_is_help=True, help="Inspect available backends and capabilities.")
auth_app = typer.Typer(no_args_is_help=True, help="Manage sync credentials for the active backend.")
workspace_app = typer.Typer(no_args_is_help=True, help="Manage saved ankicli workspaces.")
skill_app = typer.Typer(no_args_is_help=True, help="Install bundled ankicli agent skills.")
profile_app = typer.Typer(no_args_is_help=True, help="Inspect and resolve local Anki profiles.")
backup_app = typer.Typer(no_args_is_help=True, help="Create, inspect, and restore local backups.")
collection_app = typer.Typer(no_args_is_help=True, help="Inspect collection-level metadata.")
deck_app = typer.Typer(no_args_is_help=True, help="Inspect decks in a collection.")
model_app = typer.Typer(no_args_is_help=True, help="Inspect note types in a collection.")
media_app = typer.Typer(no_args_is_help=True, help="Inspect collection media files.")
search_app = typer.Typer(
    no_args_is_help=True,
    help="Search notes and cards with Anki-style queries.",
)
export_app = typer.Typer(no_args_is_help=True, help="Export collection data in normalized JSON.")
import_app = typer.Typer(
    no_args_is_help=True,
    help="Import normalized JSON data into a collection.",
)
sync_app = typer.Typer(no_args_is_help=True, help="Inspect and run collection sync flows.")
note_app = typer.Typer(no_args_is_help=True, help="Inspect and mutate notes.")
card_app = typer.Typer(no_args_is_help=True, help="Inspect and mutate cards.")
tag_app = typer.Typer(no_args_is_help=True, help="Inspect tags in a collection.")
study_app = typer.Typer(
    no_args_is_help=True,
    help="Run local tutor-style study sessions over a collection.",
)
catalog_app = typer.Typer(
    no_args_is_help=True,
    help="Export the authoritative capability and workflow catalog.",
)

app.add_typer(doctor_app, name="doctor")
app.add_typer(backend_app, name="backend")
app.add_typer(auth_app, name="auth")
app.add_typer(workspace_app, name="workspace")
app.add_typer(skill_app, name="skill")
app.add_typer(profile_app, name="profile")
app.add_typer(backup_app, name="backup")
app.add_typer(collection_app, name="collection")
app.add_typer(deck_app, name="deck")
app.add_typer(model_app, name="model")
app.add_typer(media_app, name="media")
app.add_typer(search_app, name="search")
app.add_typer(export_app, name="export")
app.add_typer(import_app, name="import")
app.add_typer(sync_app, name="sync")
app.add_typer(note_app, name="note")
app.add_typer(card_app, name="card")
app.add_typer(tag_app, name="tag")
app.add_typer(study_app, name="study")
app.add_typer(catalog_app, name="catalog")


def emit(
    settings: Settings,
    *,
    data: dict | None = None,
    error: AnkiCliError | None = None,
) -> None:
    backend_name = settings.backend_name
    envelope = error_envelope(error, backend=backend_name) if error else success_envelope(
        backend=backend_name,
        data=data or {},
    )
    text = render_json(envelope) if settings.json_output else render_human(envelope)
    typer.echo(text)
    if error:
        raise typer.Exit(error.exit_code)


def get_settings(ctx: typer.Context) -> Settings:
    return ctx.obj


def _emit_startup_error(
    *,
    backend_name: str,
    json_output: bool,
    error: AnkiCliError,
) -> None:
    envelope = error_envelope(error, backend=backend_name)
    text = render_json(envelope) if json_output else render_human(envelope)
    typer.echo(text)
    raise typer.Exit(error.exit_code)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def _resolve_config_target(
    *,
    collection: str | None,
    profile: str | None,
    backend: str,
    json_output: bool,
    use_config: bool,
    workspace: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    if collection or profile or not use_config or backend == "ankiconnect":
        return collection, profile, None, None
    workspace_name = normalize_workspace_name(workspace or active_workspace())
    config_path = workspace_config_path(workspace_name).expanduser()
    try:
        workspace_config = load_workspace_config(workspace_name)
    except AnkiCliError as error:
        _emit_startup_error(
            backend_name=backend,
            json_output=json_output,
            error=error,
        )
    source_prefix = f"workspace.{workspace_name}"
    if workspace_config.collection:
        return workspace_config.collection, None, str(config_path), f"{source_prefix}.collection"
    if workspace_config.anki_profile:
        return (
            None,
            workspace_config.anki_profile,
            str(config_path),
            f"{source_prefix}.anki_profile",
        )
    return None, None, str(config_path) if config_path.exists() else None, None


def _error_dict(error: AnkiCliError) -> dict:
    return {"code": error.code, "message": error.message, "details": error.details}


def _discover_profile_items() -> tuple[list[dict], dict | None]:
    try:
        profiles = ProfileResolver().list_profiles()
    except AnkiCliError as error:
        return [], _error_dict(error)
    return [profile.to_dict() for profile in profiles], None


def _workspace_target_from_config(config) -> tuple[str | None, str | None]:
    if config.anki_profile:
        return "anki_profile", config.anki_profile
    if config.collection:
        return "collection", config.collection
    return None, None


def _configure_payload(
    settings: Settings,
    *,
    workspace_name: str,
    profiles: list[dict],
    discovery_error: dict | None,
    saved: bool,
    save_error: dict | None,
    sync_choice: str,
    detected_default_profile: dict | None = None,
    login_result: dict | None = None,
    login_error: dict | None = None,
    skill_result: dict | None = None,
    skill_error: dict | None = None,
) -> dict:
    credential_store = probe_default_credential_store()
    config = load_workspace_config(workspace_name)
    target_type, target_value = _workspace_target_from_config(config)
    if target_type:
        steps = [
            "ankicli collection info",
            "ankicli deck list",
            "ankicli search preview --kind notes --query 'deck:Default' --limit 5",
            "ankicli auth status",
            "ankicli sync status",
        ]
    else:
        steps = [
            "ankicli profile list",
            'ankicli workspace set --profile "User 1"',
            "ankicli collection info",
        ]
    return {
        "goal": (
            "find a local Anki collection, save an ankicli workspace, optionally configure "
            "AnkiWeb sync credentials, then start using ankicli"
        ),
        "workspace": workspace_report(workspace_name, config),
        "profiles": profiles,
        "profile_discovery_error": discovery_error,
        "target": {"type": target_type, "value": target_value},
        "resolved_collection": settings.collection,
        "resolved_anki_profile": settings.profile,
        "resolved_backend": settings.backend_name,
        "selected_workspace": workspace_name,
        "active_target_source": settings.workspace_target_source,
        "credential_storage": {
            "backend": credential_store.backend,
            "available": credential_store.available,
            "fallback": credential_store.fallback,
            "path": credential_store.path,
            "reason": credential_store.reason,
        },
        "sync": {
            "choice": sync_choice,
            "login_result": login_result,
            "login_error": login_error,
        },
        "skills": {
            "install_result": skill_result,
            "install_error": skill_error,
        },
        "detected_default_profile": detected_default_profile,
        "saved": saved,
        "save_error": save_error,
        "steps": steps,
        "notes": [
            "~/.ankicli/workspaces/<name>/config.json stores human-facing workspace config.",
            (
                "Sync credentials are stored separately in the OS keyring when available, "
                "with a platform file fallback."
            ),
            "Sync login uses an AnkiWeb account. You can skip sync and still use local commands.",
        ],
    }


def _render_configure(data: dict) -> str:
    lines = [
        "Workspace",
        f"  active: {data['workspace']['active_workspace']}",
        f"  selected: {data['workspace']['selected_workspace']}",
        f"  root: {data['workspace']['workspace_root']}",
        f"  config: {data['workspace']['config_path']}",
        "",
        "Collection target",
    ]
    target = data["target"]
    if target["type"] == "anki_profile":
        lines.append(f"  Anki profile: {target['value']}")
    elif target["type"] == "collection":
        lines.append(f"  collection: {target['value']}")
    else:
        lines.append("  not set yet")
    if data["profile_discovery_error"]:
        lines.extend(
            [
                "",
                "Profile discovery",
                f"  {data['profile_discovery_error']['code']}: "
                f"{data['profile_discovery_error']['message']}",
            ]
        )
    elif data["profiles"]:
        lines.extend(["", "Discovered Anki profiles"])
        for index, item in enumerate(data["profiles"], start=1):
            label = item["name"] or "(unknown)"
            exists = "found" if item["exists"] else "missing collection file"
            lines.append(f"  {index}. {label} - {exists}")
            lines.append(f"     {item['collection_path']}")
    sync = data["sync"]
    lines.extend(
        [
            "",
            "Sync",
            f"  choice: {sync['choice']}",
            f"  credential storage: {data['credential_storage']['backend']}",
        ]
    )
    if sync["login_result"]:
        lines.append("  login: saved")
    if sync["login_error"]:
        lines.append(f"  login: {sync['login_error']['code']}: {sync['login_error']['message']}")
    skills = data["skills"]
    lines.extend(["", "ankicli skill"])
    if skills["install_result"]:
        for target in skills["install_result"]["targets"]:
            lines.append(f"  installed: {target['target']} ({target['bundle']['path']})")
    elif skills["install_error"]:
        lines.append(
            f"  error: {skills['install_error']['code']}: {skills['install_error']['message']}"
        )
    else:
        lines.append("  not installed")
        lines.append("  do this later: ankicli skill install")
    lines.extend(["", "Try next"])
    lines.extend(f"  {step}" for step in data["steps"])
    if data["target"]["type"] is None:
        lines.extend(["", "Configure later", "  ankicli configure"])
    return "\n".join(lines)


def _select_configure_target(
    *,
    profiles: list[dict],
    provided_profile: str | None,
    provided_collection: str | None,
) -> tuple[str | None, str | None]:
    if provided_profile or provided_collection:
        return provided_profile, provided_collection
    if profiles:
        recommended = profiles[0]
        recommended_name = str(recommended["name"] or "this profile")
        typer.echo("I found your local Anki data.")
        typer.echo()
        typer.echo(f"Recommended: use Anki profile '{recommended_name}'.")
        typer.echo("This saves the normal local Anki collection as your default ankicli workspace.")
        typer.echo(f"Collection file: {recommended['collection_path']}")
        typer.echo()
        typer.echo("Options:")
        typer.echo("  Enter  use the recommended profile")
        typer.echo("  n      choose a different profile or collection")
        typer.echo("  skip   do this later by running: ankicli configure")
        choice = typer.prompt(
            f"Use '{recommended_name}'? (recommended)",
            default="",
            show_default=False,
        ).strip()
        if not choice or choice.lower() in {"y", "yes"}:
            return recommended_name, None
        if choice.lower() == "skip":
            return None, None
        if choice.lower() not in {"n", "no"}:
            typer.echo("I did not understand that, so I will show the advanced choices.")
        typer.echo()
        typer.echo("Advanced choices:")
        for index, item in enumerate(profiles, start=1):
            typer.echo(f"  {index}. {item['name']} ({item['collection_path']})")
        typer.echo("  skip. do this later by running: ankicli configure")
        advanced_choice = typer.prompt(
            "Choose a profile number, paste a collection path, or type skip",
            default="1",
            show_default=True,
        ).strip()
        if advanced_choice.lower() == "skip":
            typer.echo("Skipped. You can do this later by running: ankicli configure")
            return None, None
        if advanced_choice.isdigit() and 1 <= int(advanced_choice) <= len(profiles):
            return str(profiles[int(advanced_choice) - 1]["name"]), None
        return None, advanced_choice
    typer.echo("I could not find local Anki data automatically.")
    typer.echo()
    typer.echo("Recommended: skip collection setup for now.")
    typer.echo("You can still inspect diagnostics, then set a workspace later.")
    typer.echo()
    typer.echo("Options:")
    typer.echo("  Enter  skip for now; do this later by running: ankicli configure")
    typer.echo("  path   paste a collection file path manually")
    collection = typer.prompt(
        "Skip collection setup? (recommended)",
        default="",
        show_default=False,
    ).strip()
    if not collection or collection.lower() in {"y", "yes", "skip"}:
        typer.echo("Skipped. You can do this later by running: ankicli configure")
        return None, None
    if collection.lower() in {"path", "p", "n", "no"}:
        manual_path = typer.prompt(
            "Paste the collection.anki2 path",
            default="",
            show_default=False,
        )
        return None, manual_path.strip() or None
    return None, collection


def _collection_for_configure_target(
    *,
    profile: str | None,
    collection: str | None,
    config,
) -> str | None:
    if collection:
        return collection
    if profile:
        return str(ProfileResolver().resolve_profile(profile).collection_path)
    if config.collection:
        return config.collection
    if config.anki_profile:
        return str(ProfileResolver().resolve_profile(config.anki_profile).collection_path)
    return None


def _render_skill_list(data: dict) -> str:
    lines = ["Bundled ankicli agent skill"]
    for item in data["items"]:
        lines.append(f"  {item['name']}")
        lines.append(f"    {item['description']}")
    lines.extend(
        [
            "",
            "Install targets",
            f"  Codex: {data['targets']['codex']}",
            f"  Claude Code: {data['targets']['claude']}",
            f"  OpenClaw: {data['targets']['openclaw']}",
        ]
    )
    if data["detected_targets"]:
        lines.append(f"  detected: {', '.join(data['detected_targets'])}")
    else:
        lines.append("  detected: none")
    lines.extend(
        [
            "",
            "Try next",
            "  ankicli skill install --target codex",
            "  ankicli skill install --target claude",
            "  ankicli skill install --target openclaw",
            "  ankicli skill install --path /path/to/skills",
        ]
    )
    return "\n".join(lines)


def _render_skill_install(data: dict) -> str:
    lines = ["ankicli skill"]
    for target in data["targets"]:
        bundle = target["bundle"]
        reason = f" ({bundle['reason']})" if bundle.get("reason") else ""
        lines.append(f"  {target['target']}: {bundle['path']}")
        lines.append(f"    {bundle['status']}{reason}: {bundle['bundle']}")
    return "\n".join(lines)


def _emit_skill_install_result(settings: Settings, data: dict) -> None:
    if settings.json_output:
        emit(settings, data=data)
        return
    typer.echo(_render_skill_install(data))


def _maybe_install_skills(
    settings: Settings,
    *,
    install_skills: bool,
    skip_skills: bool,
    skill_target: str | None,
    skill_path: str | None,
) -> dict | None:
    if install_skills and skip_skills:
        raise ValidationError("--install-skills and --skip-skills are mutually exclusive")
    if skill_path and skill_target:
        raise ValidationError("--skill-path and --skill-target are mutually exclusive")
    if settings.json_output and not install_skills:
        return None
    target = skill_target
    path = skill_path
    if not install_skills and not skip_skills and not settings.json_output:
        detected = detected_skill_targets()
        typer.echo()
        typer.echo("ankicli skill")
        typer.echo("This installs the ankicli umbrella skill for Claude, Codex, or OpenClaw.")
        if detected:
            recommended = "all" if len(detected) > 1 else detected[0]
            target_label = ", ".join(detected)
            typer.echo(f"Detected agent skill home: {target_label}")
            typer.echo(
                f"Recommended: press Enter to install the ankicli skill into {target_label}."
            )
            typer.echo()
            typer.echo("Options:")
            typer.echo(f"  Enter  install the ankicli skill into {target_label}")
            typer.echo("  n      skip for now")
            typer.echo("  path   install to a custom skills directory")
            choice = typer.prompt(
                "Install the ankicli skill? (recommended: press Enter)",
                default="",
                show_default=False,
            ).strip()
            if choice.lower() in {"n", "no", "skip"}:
                typer.echo("Skipped. You can do this later by running: ankicli skill install")
                return None
            if choice.lower() == "path":
                path = typer.prompt("Paste the skills directory path").strip()
            else:
                target = recommended
        else:
            typer.echo("I did not find a Codex, Claude Code, or OpenClaw skill home.")
            typer.echo()
            typer.echo("Recommended: skip ankicli skill install for now.")
            typer.echo("You can do this later by running: ankicli skill install --target codex")
            typer.echo()
            typer.echo("Options:")
            typer.echo("  Enter  skip for now")
            typer.echo("  codex  install the ankicli skill into ~/.codex/skills")
            typer.echo("  claude install the ankicli skill into ~/.claude/skills")
            typer.echo("  openclaw install the ankicli skill into ~/.openclaw/skills")
            typer.echo("  path   install to a custom skills directory")
            choice = typer.prompt(
                "Skip ankicli skill install? (recommended)",
                default="",
                show_default=False,
            ).strip()
            if not choice or choice.lower() in {"y", "yes", "skip"}:
                typer.echo("Skipped. You can do this later by running: ankicli skill install")
                return None
            if choice.lower() == "path":
                path = typer.prompt("Paste the skills directory path").strip()
            else:
                target = choice
    if skip_skills:
        return None
    data = install_agent_skills(target=target or "codex", path=path)
    if not settings.json_output:
        typer.echo()
        typer.echo(_render_skill_install(data))
    return data


def _should_apply_saved_target(ctx: typer.Context) -> bool:
    return ctx.invoked_subcommand not in {
        "backend",
        "catalog",
        "changelog",
        "configure",
        "doctor",
        "profile",
        "skill",
        "workspace",
    }


@app.callback()
def main(
    ctx: typer.Context,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    backend: Annotated[str | None, typer.Option("--backend")] = None,
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            help="Use a named ~/.ankicli workspace for this command.",
        ),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    no_auto_backup: Annotated[bool, typer.Option("--no-auto-backup")] = False,
    no_config: Annotated[
        bool,
        typer.Option("--no-config", help="Ignore saved ~/.ankicli workspace defaults."),
    ] = False,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = False,
) -> None:
    del version
    selected_workspace = normalize_workspace_name(workspace or active_workspace())
    if no_config:
        workspace_config = None
    else:
        try:
            workspace_config = load_workspace_config(selected_workspace)
        except AnkiCliError as error:
            _emit_startup_error(
                backend_name=backend or "python-anki",
                json_output=json_output,
                error=error,
            )
    resolved_backend = (
        backend or (workspace_config.backend if workspace_config else None) or "python-anki"
    )
    if collection and profile:
        _emit_startup_error(
            backend_name=resolved_backend,
            json_output=json_output,
            error=ValidationError("--collection and --profile are mutually exclusive"),
        )
    resolved_collection, resolved_profile, loaded_config_path, workspace_target_source = (
        _resolve_config_target(
            collection=collection,
            profile=profile,
            backend=resolved_backend,
            json_output=json_output,
            use_config=not no_config and _should_apply_saved_target(ctx),
            workspace=selected_workspace,
        )
    )
    if profile:
        resolved_profile = profile
    if resolved_profile:
        if resolved_backend == "ankiconnect":
            _emit_startup_error(
                backend_name=resolved_backend,
                json_output=json_output,
                error=ValidationError("--profile is not supported with the ankiconnect backend"),
            )
        try:
            context = ProfileResolver().resolve_profile(resolved_profile)
        except AnkiCliError as error:
            _emit_startup_error(
                backend_name=resolved_backend,
                json_output=json_output,
                error=error,
            )
        resolved_collection = str(context.collection_path)
        resolved_profile = context.name
    ctx.obj = Settings(
        collection=resolved_collection,
        profile=resolved_profile,
        backend_name=resolved_backend,
        json_output=json_output,
        no_auto_backup=no_auto_backup,
        workspace_config_path=loaded_config_path,
        workspace_target_source=workspace_target_source,
        workspace=selected_workspace if not no_config else None,
    )


@app.command("changelog", help="Show release notes from CHANGELOG.md.")
def changelog(
    ctx: typer.Context,
    include_all: Annotated[
        bool,
        typer.Option("--all", help="Show the full changelog instead of the latest section."),
    ] = False,
) -> None:
    settings = get_settings(ctx)
    try:
        data = changelog_report(include_all=include_all)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    if settings.json_output:
        emit(settings, data=data)
        return
    typer.echo(data["content"])


@doctor_app.command("env", help="Report Python, platform, and Anki import-path diagnostics.")
def doctor_env(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    report = DoctorService().env_report()
    emit(settings, data=report)


@doctor_app.command("backend", help="Summarize the active backend state and support surface.")
def doctor_backend(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        report = DoctorService().backend_report(backend)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=report)


@doctor_app.command(
    "capabilities",
    help="Summarize active backend capabilities and support counts.",
)
def doctor_capabilities(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        report = DoctorService().capabilities_report(backend)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=report)


@doctor_app.command(
    "collection",
    help="Run collection-targeted diagnostics for the active backend.",
)
def doctor_collection(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        report = DoctorService().collection_report(backend, settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=report)


@doctor_app.command(
    "safety",
    help="Report whether the current collection target looks safe for writes.",
)
def doctor_safety(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        report = DoctorService().safety_report(backend, settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=report)


@backend_app.command("list", help="List supported backends.")
def backend_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    emit(settings, data={"items": ["python-anki", "ankiconnect"]})


@backend_app.command("info", help="Show the active backend and its normalized capabilities.")
def backend_info(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    emit(settings, data=BackendService(backend).info())


@backend_app.command("capabilities", help="Show raw capability flags for the active backend.")
def backend_capabilities(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    emit(settings, data=backend.backend_capabilities().model_dump())


@backend_app.command(
    "test-connection",
    help="Probe the active backend and report whether it is reachable.",
)
def backend_test_connection(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    emit(settings, data=BackendService(backend).test_connection())


@auth_app.command(
    "status",
    help="Report whether sync credentials are stored for the active backend.",
)
def auth_status(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = AuthService(backend).status(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@auth_app.command(
    "login",
    help="Log in for sync and store credentials in the supported local credential store.",
)
def auth_login(
    ctx: typer.Context,
    username: Annotated[str, typer.Option("--username", prompt=True)],
    password: Annotated[str, typer.Option("--password", prompt=True, hide_input=True)],
    endpoint: Annotated[str | None, typer.Option("--endpoint")] = None,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = AuthService(backend).login(
            settings.collection,
            username=username,
            password=password,
            endpoint=endpoint,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@auth_app.command("logout", help="Delete stored sync credentials for the active backend.")
def auth_logout(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = AuthService(backend).logout(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@workspace_app.command("path", help="Show where ankicli keeps human-facing workspaces.")
def workspace_path(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    try:
        data = workspace_report(settings.workspace)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@workspace_app.command("show", help="Show the active or selected ankicli workspace.")
def workspace_show(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    try:
        data = workspace_report(settings.workspace)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    data["resolved_collection"] = settings.collection
    data["resolved_anki_profile"] = settings.profile
    data["resolved_backend"] = settings.backend_name
    data["selected_workspace"] = settings.workspace
    data["active_target_source"] = settings.workspace_target_source
    emit(settings, data=data)


@workspace_app.command("list", help="List saved ankicli workspaces.")
def workspace_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    active = active_workspace()
    emit(
        settings,
        data={
            "active_workspace": active,
            "items": [
                {
                    "name": name,
                    "active": name == active,
                    **workspace_item(name),
                }
                for name in list_workspaces()
            ],
        },
    )


@workspace_app.command("use", help="Set the active ankicli workspace.")
def workspace_use(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = get_settings(ctx)
    try:
        normalized_name = normalize_workspace_name(name)
        config = load_workspace_config(normalized_name)
        config_path = save_workspace_config(config, normalized_name)
        active_path = set_active_workspace(normalized_name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(
        settings,
        data={
            "saved": True,
            "active_workspace_path": str(active_path),
            "config_path": str(config_path),
            **workspace_report(normalized_name, config),
        },
    )


@workspace_app.command("set", help="Save profile, collection, or backend choices.")
def workspace_set(
    ctx: typer.Context,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Workspace to update. Defaults to the active workspace."),
    ] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    backend: Annotated[str | None, typer.Option("--backend")] = None,
    activate: Annotated[
        bool,
        typer.Option("--activate", help="Make this workspace active after saving."),
    ] = False,
) -> None:
    settings = get_settings(ctx)
    if profile and collection:
        emit(settings, error=ValidationError("--profile and --collection are mutually exclusive"))
        return
    if not any((profile, collection, backend)):
        emit(
            settings,
            error=ValidationError(
                "workspace set requires at least one of --profile, --collection, or --backend",
            ),
        )
        return
    try:
        workspace_name = normalize_workspace_name(name or active_workspace())
        config = load_workspace_config(workspace_name)
        if profile is not None:
            config.anki_profile = profile
            config.collection = None
        if collection is not None:
            config.collection = collection
            config.anki_profile = None
        if backend is not None:
            config.backend = backend
        config_path = save_workspace_config(config, workspace_name)
        if activate:
            set_active_workspace(workspace_name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(
        settings,
        data={
            "saved": True,
            "config_path": str(config_path),
            "updated_workspace": workspace_name,
            **workspace_report(workspace_name, config),
        },
    )


@workspace_app.command("clear", help="Clear saved values from an ankicli workspace.")
def workspace_clear(
    ctx: typer.Context,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Workspace to clear. Defaults to the active workspace."),
    ] = None,
    target: Annotated[
        bool,
        typer.Option("--target", help="Clear saved profile/collection."),
    ] = False,
    backend: Annotated[bool, typer.Option("--backend", help="Clear saved backend.")] = False,
    all_values: Annotated[bool, typer.Option("--all", help="Clear all saved defaults.")] = False,
) -> None:
    settings = get_settings(ctx)
    if not any((target, backend, all_values)):
        emit(
            settings,
            error=ValidationError("workspace clear requires --target, --backend, or --all"),
        )
        return
    try:
        workspace_name = normalize_workspace_name(name or active_workspace())
        config = load_workspace_config(workspace_name)
        if target or all_values:
            config.anki_profile = None
            config.collection = None
        if backend or all_values:
            config.backend = None
        config_path = save_workspace_config(config, workspace_name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(
        settings,
        data={
            "saved": True,
            "config_path": str(config_path),
            "updated_workspace": workspace_name,
            **workspace_report(workspace_name, config),
        },
    )


@skill_app.command(
    "list",
    help="List the bundled ankicli umbrella skill and known install targets.",
)
def skill_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    data = skill_list_payload()
    if settings.json_output:
        emit(settings, data=data)
        return
    typer.echo(_render_skill_list(data))


@skill_app.command(
    "install",
    help="Install the bundled ankicli umbrella skill into an agent skill home.",
)
def skill_install(
    ctx: typer.Context,
    target: Annotated[
        str | None,
        typer.Option(
            "--target",
            help=(
                "Install target: codex, claude, openclaw, or all. "
                "Defaults to codex when --path is absent."
            ),
        ),
    ] = None,
    path: Annotated[
        str | None,
        typer.Option("--path", help="Custom skills root to install into."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite an existing local ankicli skill bundle."),
    ] = False,
) -> None:
    settings = get_settings(ctx)
    try:
        data = install_agent_skills(
            target=target,
            path=path,
            overwrite=overwrite,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    _emit_skill_install_result(settings, data)


def _run_configure_wizard(
    settings: Settings,
    *,
    title: str,
    save_default_profile: bool,
    workspace: str | None,
    profile: str | None,
    collection: str | None,
    login: bool,
    skip_sync: bool,
    username: str | None,
    password: str | None,
    endpoint: str | None,
    install_skills: bool,
    skip_skills: bool,
    skill_target: str | None,
    skill_path: str | None,
) -> None:
    if profile and collection:
        emit(settings, error=ValidationError("--profile and --collection are mutually exclusive"))
        return
    if login and skip_sync:
        emit(settings, error=ValidationError("--login and --skip-sync are mutually exclusive"))
        return
    saved = False
    saved_error: dict | None = None
    login_result: dict | None = None
    login_error: dict | None = None
    skill_result: dict | None = None
    skill_error: dict | None = None
    sync_choice = "skipped"
    detected_default_profile: dict | None = None
    workspace_name = normalize_workspace_name(workspace or active_workspace())
    profiles, discovery_error = _discover_profile_items()
    try:
        if save_default_profile and not profile and not collection:
            detected_default_profile = ProfileResolver().default_profile().to_dict()
            profile = detected_default_profile["name"]
        if not settings.json_output:
            typer.echo(title)
            typer.echo()
            typer.echo("This will find your local Anki collection, save a workspace target,")
            typer.echo("and optionally store AnkiWeb sync credentials.")
            typer.echo()
            profile, collection = _select_configure_target(
                profiles=profiles,
                provided_profile=profile,
                provided_collection=collection,
            )
        if profile or collection:
            config = load_workspace_config(workspace_name)
            if profile:
                config.anki_profile = profile
                config.collection = None
            if collection:
                config.collection = collection
                config.anki_profile = None
            save_workspace_config(config, workspace_name)
            set_active_workspace(workspace_name)
            saved = True
        else:
            config = load_workspace_config(workspace_name)
    except AnkiCliError as error:
        saved_error = _error_dict(error)
        config = load_workspace_config(workspace_name)
    if saved_error is None:
        try:
            collection_for_login = _collection_for_configure_target(
                profile=profile,
                collection=collection,
                config=config,
            )
        except AnkiCliError as error:
            collection_for_login = None
            login_error = _error_dict(error)
        if collection_for_login is None:
            sync_choice = "target_required"
        elif skip_sync:
            sync_choice = "skipped"
        elif login or (
            not settings.json_output and typer.confirm("Log in to AnkiWeb sync now?", default=False)
        ):
            sync_choice = "login"
            username_value = username or typer.prompt("AnkiWeb username")
            password_value = password or typer.prompt("AnkiWeb password", hide_input=True)
            try:
                backend = get_backend(settings.backend_name)
                login_result = AuthService(backend).login(
                    collection_for_login,
                    username=username_value,
                    password=password_value,
                    endpoint=endpoint,
                )
            except AnkiCliError as error:
                login_error = _error_dict(error)
    try:
        skill_result = _maybe_install_skills(
            settings,
            install_skills=install_skills,
            skip_skills=skip_skills,
            skill_target=skill_target,
            skill_path=skill_path,
        )
    except AnkiCliError as error:
        skill_error = _error_dict(error)
    data = _configure_payload(
        settings,
        workspace_name=workspace_name,
        profiles=profiles,
        discovery_error=discovery_error,
        saved=saved,
        save_error=saved_error,
        sync_choice=sync_choice,
        detected_default_profile=detected_default_profile,
        login_result=login_result,
        login_error=login_error,
        skill_result=skill_result,
        skill_error=skill_error,
    )
    if not settings.json_output:
        typer.echo()
        typer.echo(_render_configure(data))
        return
    emit(settings, data=data)


@app.command("configure", help="Configure an ankicli workspace and optional AnkiWeb sync.")
def configure(
    ctx: typer.Context,
    save_default_profile: Annotated[
        bool,
        typer.Option("--save-default-profile", help="Detect and save the default Anki profile."),
    ] = False,
    workspace: Annotated[
        str | None,
        typer.Option(
            "--workspace",
            help="Workspace to update. Defaults to the active workspace.",
        ),
    ] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    login: Annotated[
        bool,
        typer.Option("--login", help="Log in to AnkiWeb sync during configuration."),
    ] = False,
    skip_sync: Annotated[
        bool,
        typer.Option("--skip-sync", help="Skip AnkiWeb sync login during configuration."),
    ] = False,
    username: Annotated[str | None, typer.Option("--username")] = None,
    password: Annotated[str | None, typer.Option("--password", hide_input=True)] = None,
    endpoint: Annotated[str | None, typer.Option("--endpoint")] = None,
    install_skills: Annotated[
        bool,
        typer.Option("--install-skills", help="Install bundled ankicli agent skills during setup."),
    ] = False,
    skip_skills: Annotated[
        bool,
        typer.Option("--skip-skills", help="Skip the agent skill install step during setup."),
    ] = False,
    skill_target: Annotated[
        str | None,
        typer.Option("--skill-target", help="Skill install target: codex, claude, or all."),
    ] = None,
    skill_path: Annotated[
        str | None,
        typer.Option("--skill-path", help="Custom skills root for the setup skill install step."),
    ] = None,
) -> None:
    _run_configure_wizard(
        get_settings(ctx),
        title="ankicli configure",
        save_default_profile=save_default_profile,
        workspace=workspace,
        profile=profile,
        collection=collection,
        login=login,
        skip_sync=skip_sync,
        username=username,
        password=password,
        endpoint=endpoint,
        install_skills=install_skills,
        skip_skills=skip_skills,
        skill_target=skill_target,
        skill_path=skill_path,
    )


@profile_app.command("list", help="List local Anki profiles from the Anki2 data root.")
def profile_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = ProfileService(backend).list()
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@profile_app.command("get", help="Inspect one local Anki profile by name.")
def profile_get(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = ProfileService(backend).get(name=name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@profile_app.command("default", help="Show the default local Anki profile.")
def profile_default(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = ProfileService(backend).default()
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@profile_app.command("resolve", help="Resolve a profile name into its collection and media paths.")
def profile_resolve(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = ProfileService(backend).resolve(name=name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@backup_app.command(
    "status",
    help="Show backup context and availability for the current collection.",
)
def backup_status(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = BackupService(backend).status(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@backup_app.command("list", help="List normalized backups for the current collection.")
def backup_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = BackupService(backend).list(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@backup_app.command("create", help="Create a backup now for the current collection.")
def backup_create(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = BackupService(backend).create(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@backup_app.command("get", help="Inspect one backup by name or absolute path.")
def backup_get(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name")] = None,
    path: Annotated[str | None, typer.Option("--path")] = None,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = BackupService(backend).get(settings.collection, name=name, path=path)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@backup_app.command(
    "restore",
    help="Restore a backup by name or path. Requires --yes and remains CLI-only.",
)
def backup_restore(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Option("--name")] = None,
    path: Annotated[str | None, typer.Option("--path")] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = BackupService(backend).restore(settings.collection, name=name, path=path, yes=yes)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@collection_app.command("info", help="Show high-level collection metadata and counts.")
def collection_info(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CollectionService(backend).info(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@collection_app.command("stats", help="Show collection counts in a stats-first normalized shape.")
def collection_stats(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CollectionService(backend).stats(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@collection_app.command(
    "validate",
    help="Run lightweight non-destructive validation against the collection.",
)
def collection_validate(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CollectionService(backend).validate(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@collection_app.command(
    "lock-status",
    help="Report best-effort lock/open-state information for the collection.",
)
def collection_lock_status(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CollectionService(backend).lock_status(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@sync_app.command("status", help="Report whether sync is required for the current collection.")
def sync_status(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = SyncService(
            backend,
            auto_backup_enabled=not settings.no_auto_backup,
        ).status(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@sync_app.command("run", help="Run the normal bidirectional sync flow for the current collection.")
def sync_run(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = SyncService(
            backend,
            auto_backup_enabled=not settings.no_auto_backup,
        ).run(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@sync_app.command(
    "pull",
    help="Run an explicit full download sync flow for the current collection.",
)
def sync_pull(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = SyncService(
            backend,
            auto_backup_enabled=not settings.no_auto_backup,
        ).pull(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@sync_app.command(
    "push",
    help="Run an explicit full upload sync flow for the current collection.",
)
def sync_push(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = SyncService(
            backend,
            auto_backup_enabled=not settings.no_auto_backup,
        ).push(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@deck_app.command("list", help="List decks in the selected collection.")
def deck_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).list_decks(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@deck_app.command("get", help="Fetch one deck by name.")
def deck_get(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).get_deck(settings.collection, name=name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@deck_app.command("stats", help="Show note/card counts for one deck.")
def deck_stats(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).deck_stats(settings.collection, name=name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@deck_app.command("create", help="Create a deck. Requires --yes unless using --dry-run.")
def deck_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = DeckService(backend).create(
            settings.collection,
            name=name,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@deck_app.command("rename", help="Rename a deck. Requires --yes unless using --dry-run.")
def deck_rename(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
    new_name: Annotated[str, typer.Option("--to")],
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = DeckService(backend).rename(
            settings.collection,
            name=name,
            new_name=new_name,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@deck_app.command("delete", help="Delete a deck. Requires --yes unless using --dry-run.")
def deck_delete(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = DeckService(backend).delete(
            settings.collection,
            name=name,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@deck_app.command(
    "reparent",
    help=(
        "Move a deck under a new parent. Use an empty --to-parent to move it "
        "to the top level. Requires --yes unless using --dry-run."
    ),
)
def deck_reparent(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
    to_parent: Annotated[str, typer.Option("--to-parent")] = "",
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = DeckService(backend).reparent(
            settings.collection,
            name=name,
            new_parent=to_parent,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@model_app.command("list", help="List note types in the selected collection.")
def model_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).list_models(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@model_app.command("get", help="Fetch one note type by name.")
def model_get(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).get_model(settings.collection, name=name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@model_app.command("fields", help="Show the field names for one note type.")
def model_fields(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).get_model_fields(settings.collection, name=name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@model_app.command("templates", help="Show the card templates for one note type.")
def model_templates(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).get_model_templates(settings.collection, name=name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@model_app.command(
    "validate-note",
    help="Validate field assignments against a note type without writing anything.",
)
def model_validate_note(
    ctx: typer.Context,
    model: Annotated[str, typer.Option("--model")],
    field: Annotated[list[str] | None, typer.Option("--field")] = None,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).validate_note(
            settings.collection,
            model_name=model,
            field_assignments=field or [],
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@media_app.command("list", help="List media files under the collection media directory.")
def media_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = MediaService(backend).list(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@media_app.command(
    "check",
    help="Summarize media directory presence, counts, and orphaned-file totals.",
)
def media_check(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = MediaService(backend).check(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@media_app.command(
    "attach",
    help="Copy a file into the collection media directory. Requires --yes unless using --dry-run.",
)
def media_attach(
    ctx: typer.Context,
    source: Annotated[str, typer.Option("--source")],
    name: Annotated[str | None, typer.Option("--name")] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = MediaService(backend).attach(
            settings.collection,
            source_path=source,
            name=name,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@media_app.command("orphaned", help="List media files not referenced by note content.")
def media_orphaned(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = MediaService(backend).orphaned(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@media_app.command(
    "resolve-path",
    help="Resolve one media filename to its path in the collection media directory.",
)
def media_resolve_path(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = MediaService(backend).resolve_path(settings.collection, name=name)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@tag_app.command("list", help="List tags in the selected collection.")
def tag_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).list_tags(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@tag_app.command(
    "apply",
    help="Add tags to a note by id. Requires --yes unless using --dry-run.",
)
def tag_apply(
    ctx: typer.Context,
    note_id: Annotated[int, typer.Option("--id")],
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = TagService(backend).apply(
            settings.collection,
            note_id=note_id,
            tags=tag or [],
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@tag_app.command(
    "remove",
    help="Remove tags from a note by id. Requires --yes unless using --dry-run.",
)
def tag_remove(
    ctx: typer.Context,
    note_id: Annotated[int, typer.Option("--id")],
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = TagService(backend).remove(
            settings.collection,
            note_id=note_id,
            tags=tag or [],
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@tag_app.command("rename", help="Rename a tag. Requires --yes unless using --dry-run.")
def tag_rename(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
    new_name: Annotated[str, typer.Option("--to")],
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = TagService(backend).rename(
            settings.collection,
            name=name,
            new_name=new_name,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@tag_app.command("delete", help="Delete one or more tags. Requires --yes unless using --dry-run.")
def tag_delete(
    ctx: typer.Context,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = TagService(backend).delete(
            settings.collection,
            tags=tag or [],
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@tag_app.command(
    "reparent",
    help=(
        "Move tags under a new parent. Use an empty --to-parent to move tags "
        "to top level. Requires --yes unless using --dry-run."
    ),
)
def tag_reparent(
    ctx: typer.Context,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    to_parent: Annotated[str, typer.Option("--to-parent")] = "",
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = TagService(backend).reparent(
            settings.collection,
            tags=tag or [],
            new_parent=to_parent,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)
@search_app.command("notes", help="Search notes with Anki-style query syntax.")
def search_notes(
    ctx: typer.Context,
    query: Annotated[str, typer.Option("--query")],
    limit: Annotated[int, typer.Option("--limit")] = 50,
    offset: Annotated[int, typer.Option("--offset")] = 0,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = SearchService(backend).find_notes(
            settings.collection,
            query=query,
            limit=limit,
            offset=offset,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@search_app.command("cards", help="Search cards with Anki-style query syntax.")
def search_cards(
    ctx: typer.Context,
    query: Annotated[str, typer.Option("--query")],
    limit: Annotated[int, typer.Option("--limit")] = 50,
    offset: Annotated[int, typer.Option("--offset")] = 0,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = SearchService(backend).find_cards(
            settings.collection,
            query=query,
            limit=limit,
            offset=offset,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@search_app.command("count", help="Return only the count for note or card search results.")
def search_count(
    ctx: typer.Context,
    kind: Annotated[str, typer.Option("--kind")] = "notes",
    query: Annotated[str, typer.Option("--query")] = "",
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    if kind not in {"notes", "cards"}:
        emit(
            settings,
            error=ValidationError("search count requires --kind notes or --kind cards"),
        )
        return
    try:
        data = SearchService(backend).count(settings.collection, kind=kind, query=query)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@search_app.command("preview", help="Preview normalized note or card records for a search query.")
def search_preview(
    ctx: typer.Context,
    kind: Annotated[str, typer.Option("--kind")] = "notes",
    query: Annotated[str, typer.Option("--query")] = "",
    limit: Annotated[int, typer.Option("--limit")] = 10,
    offset: Annotated[int, typer.Option("--offset")] = 0,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    if kind not in {"notes", "cards"}:
        emit(
            settings,
            error=ValidationError("search preview requires --kind notes or --kind cards"),
        )
        return
    try:
        data = SearchService(backend).preview(
            settings.collection,
            kind=kind,
            query=query,
            limit=limit,
            offset=offset,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@study_app.command("start", help="Create a local tutor-style study session from a deck or query.")
def study_start(
    ctx: typer.Context,
    deck: Annotated[str | None, typer.Option("--deck")] = None,
    query: Annotated[str | None, typer.Option("--query")] = None,
    scope_preset: Annotated[str, typer.Option("--scope-preset")] = "all",
    limit: Annotated[int, typer.Option("--limit")] = 20,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = StudyService(backend).start(
            settings.collection,
            deck=deck,
            query=query,
            scope_preset=scope_preset,
            limit=limit,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@study_app.command("next", help="Return the current or next card in the active study session.")
def study_next(
    ctx: typer.Context,
    session_id: Annotated[str | None, typer.Option("--session-id")] = None,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = StudyService(backend).next(session_id=session_id)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@study_app.command("details", help="Return the current study card details from the front side.")
def study_details(
    ctx: typer.Context,
    session_id: Annotated[str | None, typer.Option("--session-id")] = None,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = StudyService(backend).details(session_id=session_id)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@study_app.command("reveal", help="Reveal the answer for the current study card.")
def study_reveal(
    ctx: typer.Context,
    session_id: Annotated[str | None, typer.Option("--session-id")] = None,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = StudyService(backend).reveal(session_id=session_id)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@study_app.command("grade", help="Record a local study grade and advance the session.")
def study_grade(
    ctx: typer.Context,
    rating: Annotated[str, typer.Option("--rating")],
    session_id: Annotated[str | None, typer.Option("--session-id")] = None,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = StudyService(backend).grade(session_id=session_id, rating=rating)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@study_app.command("summary", help="Summarize the active study session.")
def study_summary(
    ctx: typer.Context,
    session_id: Annotated[str | None, typer.Option("--session-id")] = None,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = StudyService(backend).summary(session_id=session_id)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@catalog_app.command("export", help="Export operation/workflow metadata plus runtime support.")
def catalog_export(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    capabilities = backend.backend_capabilities().model_dump()
    data = {
        **catalog_snapshot(),
        "backend": backend.name,
        "available": capabilities["available"],
        "supported_operations": capabilities["supported_operations"],
        "supported_workflows": capabilities["supported_workflows"],
        "workflow_support": capabilities["workflow_support"],
        "notes": capabilities["notes"],
    }
    emit(settings, data=data)


@export_app.command("notes", help="Export normalized note records matching an Anki-style query.")
def export_notes(
    ctx: typer.Context,
    query: Annotated[str, typer.Option("--query")],
    limit: Annotated[int, typer.Option("--limit")] = 50,
    offset: Annotated[int, typer.Option("--offset")] = 0,
    ndjson: Annotated[bool, typer.Option("--ndjson")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = ExportService(backend).export_notes(
            settings.collection,
            query=query,
            limit=limit,
            offset=offset,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    if ndjson:
        typer.echo(render_ndjson(data["items"]))
        return
    emit(settings, data=data)


@export_app.command("cards", help="Export normalized card records matching an Anki-style query.")
def export_cards(
    ctx: typer.Context,
    query: Annotated[str, typer.Option("--query")],
    limit: Annotated[int, typer.Option("--limit")] = 50,
    offset: Annotated[int, typer.Option("--offset")] = 0,
    ndjson: Annotated[bool, typer.Option("--ndjson")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = ExportService(backend).export_cards(
            settings.collection,
            query=query,
            limit=limit,
            offset=offset,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    if ndjson:
        typer.echo(render_ndjson(data["items"]))
        return
    emit(settings, data=data)


@import_app.command(
    "notes",
    help="Import normalized note records from a JSON file. Requires --yes unless using --dry-run.",
)
def import_notes(
    ctx: typer.Context,
    input_path: Annotated[str | None, typer.Option("--input")] = None,
    stdin_json: Annotated[bool, typer.Option("--stdin-json")] = False,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = ImportService(backend).import_notes(
            settings.collection,
            input_path=input_path,
            stdin_json=stdin_json,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@import_app.command(
    "patch",
    help="Apply note field patches from a JSON file. Requires --yes unless using --dry-run.",
)
def import_patch(
    ctx: typer.Context,
    input_path: Annotated[str | None, typer.Option("--input")] = None,
    stdin_json: Annotated[bool, typer.Option("--stdin-json")] = False,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = ImportService(backend).import_patch(
            settings.collection,
            input_path=input_path,
            stdin_json=stdin_json,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@note_app.command("get", help="Fetch one note by id.")
def note_get(
    ctx: typer.Context,
    note_id: Annotated[int, typer.Option("--id")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = NoteService(backend).get(settings.collection, note_id=note_id)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@note_app.command("fields", help="Fetch only the fields for one note by id.")
def note_fields(
    ctx: typer.Context,
    note_id: Annotated[int, typer.Option("--id")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = NoteService(backend).fields(settings.collection, note_id=note_id)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@note_app.command("add", help="Add a note to a deck using a named note type.")
def note_add(
    ctx: typer.Context,
    deck: Annotated[str, typer.Option("--deck")],
    model: Annotated[str, typer.Option("--model")],
    field: Annotated[list[str] | None, typer.Option("--field")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = NoteService(backend).add(
            settings.collection,
            deck_name=deck,
            model_name=model,
            field_assignments=field or [],
            tags=tag or [],
            dry_run=dry_run,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@note_app.command("update", help="Update one or more note fields by id.")
def note_update(
    ctx: typer.Context,
    note_id: Annotated[int, typer.Option("--id")],
    field: Annotated[list[str] | None, typer.Option("--field")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = NoteService(backend).update(
            settings.collection,
            note_id=note_id,
            field_assignments=field or [],
            dry_run=dry_run,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@note_app.command("delete", help="Delete a note by id. Requires --yes unless using --dry-run.")
def note_delete(
    ctx: typer.Context,
    note_id: Annotated[int, typer.Option("--id")],
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = NoteService(backend).delete(
            settings.collection,
            note_id=note_id,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@note_app.command(
    "add-tags",
    help="Add tags to a note by id. Requires --yes unless using --dry-run.",
)
def note_add_tags(
    ctx: typer.Context,
    note_id: Annotated[int, typer.Option("--id")],
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = NoteService(backend).add_tags(
            settings.collection,
            note_id=note_id,
            tags=tag or [],
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@note_app.command(
    "remove-tags",
    help="Remove tags from a note by id. Requires --yes unless using --dry-run.",
)
def note_remove_tags(
    ctx: typer.Context,
    note_id: Annotated[int, typer.Option("--id")],
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = NoteService(backend).remove_tags(
            settings.collection,
            note_id=note_id,
            tags=tag or [],
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@note_app.command(
    "move-deck",
    help="Move a note's cards to a deck. Requires --yes unless using --dry-run.",
)
def note_move_deck(
    ctx: typer.Context,
    note_id: Annotated[int, typer.Option("--id")],
    deck: Annotated[str, typer.Option("--deck")],
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = NoteService(backend).move_deck(
            settings.collection,
            note_id=note_id,
            deck_name=deck,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@card_app.command("get", help="Fetch one card by id.")
def card_get(
    ctx: typer.Context,
    card_id: Annotated[int, typer.Option("--id")],
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CardService(backend).get(settings.collection, card_id=card_id)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@card_app.command(
    "suspend",
    help="Suspend a card by id. Requires --yes unless using --dry-run.",
)
def card_suspend(
    ctx: typer.Context,
    card_id: Annotated[int, typer.Option("--id")],
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CardService(backend).suspend(
            settings.collection,
            card_id=card_id,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@card_app.command(
    "unsuspend",
    help="Unsuspend a card by id. Requires --yes unless using --dry-run.",
)
def card_unsuspend(
    ctx: typer.Context,
    card_id: Annotated[int, typer.Option("--id")],
    yes: Annotated[bool, typer.Option("--yes")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CardService(backend).unsuspend(
            settings.collection,
            card_id=card_id,
            dry_run=dry_run,
            yes=yes,
            auto_backup_enabled=not settings.no_auto_backup,
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
