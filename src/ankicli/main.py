"""CLI entrypoint."""

from __future__ import annotations

from typing import Annotated

import typer

from ankicli import __version__
from ankicli.app.errors import AnkiCliError, ValidationError
from ankicli.app.output import (
    error_envelope,
    render_human,
    render_json,
    render_ndjson,
    success_envelope,
)
from ankicli.app.services import (
    BackendService,
    CardService,
    CatalogService,
    CollectionService,
    DeckService,
    DoctorService,
    ExportService,
    ImportService,
    MediaService,
    NoteService,
    SearchService,
    TagService,
)
from ankicli.runtime import Settings, get_backend

app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    help="Inspect and mutate local Anki collections.",
)
doctor_app = typer.Typer(no_args_is_help=True, help="Inspect environment and backend state.")
backend_app = typer.Typer(no_args_is_help=True, help="Inspect available backends and capabilities.")
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
note_app = typer.Typer(no_args_is_help=True, help="Inspect and mutate notes.")
card_app = typer.Typer(no_args_is_help=True, help="Inspect and mutate cards.")
tag_app = typer.Typer(no_args_is_help=True, help="Inspect tags in a collection.")

app.add_typer(doctor_app, name="doctor")
app.add_typer(backend_app, name="backend")
app.add_typer(collection_app, name="collection")
app.add_typer(deck_app, name="deck")
app.add_typer(model_app, name="model")
app.add_typer(media_app, name="media")
app.add_typer(search_app, name="search")
app.add_typer(export_app, name="export")
app.add_typer(import_app, name="import")
app.add_typer(note_app, name="note")
app.add_typer(card_app, name="card")
app.add_typer(tag_app, name="tag")


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


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    backend: Annotated[str, typer.Option("--backend")] = "python-anki",
    json_output: Annotated[bool, typer.Option("--json")] = False,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True),
    ] = False,
) -> None:
    del version
    ctx.obj = Settings(collection=collection, backend_name=backend, json_output=json_output)


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
        )
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
