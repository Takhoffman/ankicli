#!/usr/bin/env python3
"""Audit the current CLI surface against the beta scope and broader roadmap."""

from __future__ import annotations

import argparse
import json
from typing import Any

from ankicli.main import app
from ankicli.runtime import get_backend

CURRENT_BETA_COMMANDS = {
    "doctor.env",
    "doctor.backend",
    "doctor.capabilities",
    "doctor.collection",
    "doctor.safety",
    "backend.list",
    "backend.info",
    "backend.capabilities",
    "backend.test-connection",
    "auth.status",
    "auth.login",
    "auth.logout",
    "profile.list",
    "profile.get",
    "profile.default",
    "profile.resolve",
    "backup.status",
    "backup.list",
    "backup.create",
    "backup.get",
    "backup.restore",
    "collection.info",
    "collection.stats",
    "collection.validate",
    "collection.lock-status",
    "deck.list",
    "deck.get",
    "deck.stats",
    "deck.create",
    "deck.rename",
    "deck.delete",
    "deck.reparent",
    "model.list",
    "model.get",
    "model.fields",
    "model.templates",
    "model.validate-note",
    "media.list",
    "media.check",
    "media.attach",
    "media.orphaned",
    "media.resolve-path",
    "search.notes",
    "search.cards",
    "search.count",
    "search.preview",
    "export.notes",
    "export.cards",
    "import.notes",
    "import.patch",
    "sync.status",
    "sync.run",
    "sync.pull",
    "sync.push",
    "note.get",
    "note.fields",
    "note.add",
    "note.update",
    "note.delete",
    "note.move-deck",
    "note.add-tags",
    "note.remove-tags",
    "card.get",
    "card.suspend",
    "card.unsuspend",
    "tag.list",
    "tag.apply",
    "tag.remove",
    "tag.rename",
    "tag.delete",
    "tag.reparent",
}

ULTIMATE_ROADMAP_COMMANDS = {
    "doctor.env",
    "doctor.collection",
    "doctor.backend",
    "doctor.safety",
    "doctor.capabilities",
    "backend.list",
    "backend.info",
    "backend.capabilities",
    "backend.test-connection",
    "auth.status",
    "auth.login",
    "auth.logout",
    "profile.list",
    "profile.get",
    "profile.default",
    "profile.resolve",
    "backup.status",
    "backup.list",
    "backup.create",
    "backup.get",
    "backup.restore",
    "collection.info",
    "collection.stats",
    "collection.validate",
    "collection.lock-status",
    "deck.list",
    "deck.get",
    "deck.stats",
    "deck.create",
    "deck.rename",
    "deck.delete",
    "deck.reparent",
    "model.list",
    "model.get",
    "model.fields",
    "model.templates",
    "model.validate-note",
    "search.notes",
    "search.cards",
    "search.preview",
    "search.count",
    "export.notes",
    "export.cards",
    "import.notes",
    "import.patch",
    "sync.status",
    "sync.run",
    "sync.pull",
    "sync.push",
    "note.get",
    "note.add",
    "note.update",
    "note.delete",
    "note.fields",
    "note.move-deck",
    "note.add-tags",
    "note.remove-tags",
    "card.get",
    "card.suspend",
    "card.unsuspend",
    "tag.list",
    "tag.rename",
    "tag.delete",
    "tag.apply",
    "tag.remove",
    "media.list",
    "media.check",
    "media.attach",
    "media.orphaned",
    "media.resolve-path",
}

COMMAND_TO_OPERATION = {
    "doctor.backend": "doctor.backend",
    "doctor.capabilities": "doctor.capabilities",
    "doctor.collection": "doctor.collection",
    "doctor.safety": "doctor.safety",
    "backend.test-connection": "backend.test_connection",
    "auth.status": "auth.status",
    "auth.login": "auth.login",
    "auth.logout": "auth.logout",
    "profile.list": "profile.list",
    "profile.get": "profile.get",
    "profile.default": "profile.default",
    "profile.resolve": "profile.resolve",
    "backup.status": "backup.status",
    "backup.list": "backup.list",
    "backup.create": "backup.create",
    "backup.get": "backup.get",
    "backup.restore": "backup.restore",
    "collection.info": "collection.info",
    "collection.stats": "collection.stats",
    "collection.validate": "collection.validate",
    "collection.lock-status": "collection.lock_status",
    "deck.list": "deck.list",
    "deck.get": "deck.get",
    "deck.stats": "deck.stats",
    "deck.create": "deck.create",
    "deck.rename": "deck.rename",
    "deck.delete": "deck.delete",
    "deck.reparent": "deck.reparent",
    "model.list": "model.list",
    "model.get": "model.get",
    "model.fields": "model.fields",
    "model.templates": "model.templates",
    "model.validate-note": "model.validate_note",
    "tag.list": "tag.list",
    "tag.apply": "note.add_tags",
    "tag.remove": "note.remove_tags",
    "tag.rename": "tag.rename",
    "tag.delete": "tag.delete",
    "tag.reparent": "tag.reparent",
    "media.list": "media.list",
    "media.check": "media.check",
    "media.attach": "media.attach",
    "media.orphaned": "media.orphaned",
    "media.resolve-path": "media.resolve_path",
    "search.notes": "search.notes",
    "search.cards": "search.cards",
    "search.count": "search.count",
    "search.preview": "search.preview",
    "export.notes": "export.notes",
    "export.cards": "export.cards",
    "import.notes": "import.notes",
    "import.patch": "import.patch",
    "sync.status": "sync.status",
    "sync.run": "sync.run",
    "sync.pull": "sync.pull",
    "sync.push": "sync.push",
    "note.get": "note.get",
    "note.fields": "note.fields",
    "note.add": "note.add",
    "note.update": "note.update",
    "note.delete": "note.delete",
    "note.move-deck": "note.move_deck",
    "note.add-tags": "note.add_tags",
    "note.remove-tags": "note.remove_tags",
    "card.get": "card.get",
    "card.suspend": "card.suspend",
    "card.unsuspend": "card.unsuspend",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the ankicli command surface.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def actual_commands() -> list[str]:
    commands: list[str] = []
    for group in app.registered_groups:
        group_name = group.name
        for command in group.typer_instance.registered_commands:
            commands.append(f"{group_name}.{command.name}")
    return sorted(commands)


def summarize_backend_support(commands: list[str]) -> dict[str, dict[str, bool]]:
    summary: dict[str, dict[str, bool]] = {}
    for backend_name in ("python-anki", "ankiconnect"):
        capabilities = get_backend(backend_name).backend_capabilities()
        backend_summary: dict[str, bool] = {}
        for command in commands:
            operation = COMMAND_TO_OPERATION.get(command)
            if operation is None:
                backend_summary[command] = True
                continue
            backend_summary[command] = capabilities.supported_operations.get(operation, False)
        summary[backend_name] = backend_summary
    return summary


def build_report() -> dict[str, Any]:
    commands = actual_commands()
    backend_support = summarize_backend_support(commands)
    current_beta_missing = sorted(CURRENT_BETA_COMMANDS - set(commands))
    current_extra = sorted(set(commands) - CURRENT_BETA_COMMANDS)
    ultimate_missing = sorted(ULTIMATE_ROADMAP_COMMANDS - set(commands))
    return {
        "actual_commands": commands,
        "current_beta": {
            "expected_count": len(CURRENT_BETA_COMMANDS),
            "implemented_count": len([cmd for cmd in commands if cmd in CURRENT_BETA_COMMANDS]),
            "missing": current_beta_missing,
            "extra": current_extra,
            "complete": not current_beta_missing,
        },
        "ultimate_roadmap": {
            "expected_count": len(ULTIMATE_ROADMAP_COMMANDS),
            "implemented_count": len([cmd for cmd in commands if cmd in ULTIMATE_ROADMAP_COMMANDS]),
            "missing": ultimate_missing,
            "complete": not ultimate_missing,
        },
        "backend_support": backend_support,
        "ankiconnect_unsupported": sorted(
            command
            for command, supported in backend_support["ankiconnect"].items()
            if not supported
        ),
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "CLI Audit",
        "",
        f"Implemented commands: {len(report['actual_commands'])}",
        "",
        "Current beta scope:",
        f"  complete: {report['current_beta']['complete']}",
        f"  missing: {len(report['current_beta']['missing'])}",
    ]
    if report["current_beta"]["missing"]:
        lines.extend(f"    - {item}" for item in report["current_beta"]["missing"])
    lines.extend(
        [
            "",
            "Ultimate roadmap scope:",
            f"  complete: {report['ultimate_roadmap']['complete']}",
            f"  missing: {len(report['ultimate_roadmap']['missing'])}",
        ],
    )
    if report["ultimate_roadmap"]["missing"]:
        preview = report["ultimate_roadmap"]["missing"][:15]
        lines.extend(f"    - {item}" for item in preview)
        if len(report["ultimate_roadmap"]["missing"]) > len(preview):
            lines.append(
                f"    ... and {len(report['ultimate_roadmap']['missing']) - len(preview)} more",
            )
    lines.extend(
        [
            "",
            "AnkiConnect unsupported implemented commands:",
        ],
    )
    lines.extend(f"  - {item}" for item in report["ankiconnect_unsupported"])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
