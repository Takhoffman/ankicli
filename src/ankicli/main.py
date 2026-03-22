"""CLI entrypoint."""

from __future__ import annotations

from typing import Annotated

import typer

from ankicli.app.errors import AnkiCliError, NotImplementedYetError
from ankicli.app.output import error_envelope, render_human, render_json, success_envelope
from ankicli.app.services import BackendService, CatalogService, CollectionService, DoctorService
from ankicli.runtime import Settings, get_backend

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
doctor_app = typer.Typer(no_args_is_help=True)
backend_app = typer.Typer(no_args_is_help=True)
collection_app = typer.Typer(no_args_is_help=True)
deck_app = typer.Typer(no_args_is_help=True)
model_app = typer.Typer(no_args_is_help=True)
search_app = typer.Typer(no_args_is_help=True)
note_app = typer.Typer(no_args_is_help=True)
card_app = typer.Typer(no_args_is_help=True)

app.add_typer(doctor_app, name="doctor")
app.add_typer(backend_app, name="backend")
app.add_typer(collection_app, name="collection")
app.add_typer(deck_app, name="deck")
app.add_typer(model_app, name="model")
app.add_typer(search_app, name="search")
app.add_typer(note_app, name="note")
app.add_typer(card_app, name="card")


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


@app.callback()
def main(
    ctx: typer.Context,
    collection: Annotated[str | None, typer.Option("--collection")] = None,
    backend: Annotated[str, typer.Option("--backend")] = "python-anki",
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    ctx.obj = Settings(collection=collection, backend_name=backend, json_output=json_output)


@doctor_app.command("env")
def doctor_env(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    report = DoctorService().env_report()
    emit(settings, data=report)


@backend_app.command("list")
def backend_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    emit(settings, data={"items": ["python-anki"]})


@backend_app.command("info")
def backend_info(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    emit(settings, data=BackendService(backend).info())


@backend_app.command("capabilities")
def backend_capabilities(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    emit(settings, data=backend.backend_capabilities().model_dump())


@collection_app.command("info")
def collection_info(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CollectionService(backend).info(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@deck_app.command("list")
def deck_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).list_decks(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


@model_app.command("list")
def model_list(ctx: typer.Context) -> None:
    settings = get_settings(ctx)
    backend = get_backend(settings.backend_name)
    try:
        data = CatalogService(backend).list_models(settings.collection)
    except AnkiCliError as error:
        emit(settings, error=error)
        return
    emit(settings, data=data)


def _not_implemented(ctx: typer.Context, command_name: str) -> None:
    settings = get_settings(ctx)
    emit(settings, error=NotImplementedYetError(f"{command_name} is not implemented yet"))


@search_app.command("notes")
def search_notes(ctx: typer.Context) -> None:
    _not_implemented(ctx, "search notes")


@search_app.command("cards")
def search_cards(ctx: typer.Context) -> None:
    _not_implemented(ctx, "search cards")


@note_app.command("get")
def note_get(ctx: typer.Context) -> None:
    _not_implemented(ctx, "note get")


@note_app.command("add")
def note_add(ctx: typer.Context) -> None:
    _not_implemented(ctx, "note add")


@note_app.command("update")
def note_update(ctx: typer.Context) -> None:
    _not_implemented(ctx, "note update")


@note_app.command("delete")
def note_delete(ctx: typer.Context) -> None:
    _not_implemented(ctx, "note delete")


@card_app.command("get")
def card_get(ctx: typer.Context) -> None:
    _not_implemented(ctx, "card get")


@card_app.command("suspend")
def card_suspend(ctx: typer.Context) -> None:
    _not_implemented(ctx, "card suspend")


@card_app.command("unsuspend")
def card_unsuspend(ctx: typer.Context) -> None:
    _not_implemented(ctx, "card unsuspend")


def run() -> None:
    app()


if __name__ == "__main__":
    run()
