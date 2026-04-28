"""Generate OpenClaw plugin skills and catalog reference docs from ankicli catalog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ankicli.app.catalog import catalog_snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "integrations" / "openclaw-plugin" / "skills"
REFERENCE_PATH = REPO_ROOT / "docs" / "anki-catalog-reference.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate OpenClaw plugin skills and catalog reference docs.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if generated OpenClaw artifacts are not up to date.",
    )
    return parser.parse_args()


def render_skill(skill: dict) -> str:
    tool_lines = "\n".join(f"- `{tool}`" for tool in skill["tool_names"])
    rule_lines = "\n".join(f"{index}. {rule}" for index, rule in enumerate(skill["rules"], start=1))
    anti_patterns = skill.get("anti_patterns") or []
    anti_pattern_block = ""
    if anti_patterns:
        anti_pattern_block = "\n## Anti-Patterns\n\n" + "\n".join(
            f"- {line}" for line in anti_patterns
        )
    return (
        f"---\n"
        f"name: {skill['name']}\n"
        f"description: {skill['description']}\n"
        f"---\n\n"
        f"{skill['summary']}\n\n"
        f"Prefer:\n\n"
        f"{tool_lines}\n\n"
        f"## Rules\n\n"
        f"{rule_lines}\n"
        f"{anti_pattern_block}\n"
    )


def render_reference(snapshot: dict) -> str:
    workflows = snapshot["workflows"]
    plugin_tools = snapshot["plugin_tools"]
    support_matrix = snapshot["support_matrix"]
    error_taxonomy = snapshot.get("error_taxonomy", [])

    workflow_lines = "\n".join(
        f"- `{workflow['id']}` [{workflow['visibility']}]: {workflow['description']}"
        for workflow in workflows
    )
    tool_lines = "\n".join(
        f"- `{tool['name']}` [{tool['surface']}]: {tool['description']}"
        for tool in plugin_tools
    )
    support_lines = []
    for backend_name, payload in support_matrix.items():
        supported = [workflow_id for workflow_id, ok in payload["workflows"].items() if ok]
        support_lines.append(
            f"- `{backend_name}` supports {len(supported)} workflows: {', '.join(supported)}"
        )
    action_lines = []
    for workflow in workflows:
        actions = workflow.get("actions") or []
        if not actions:
            continue
        action_ids = ", ".join(action["id"] for action in actions)
        action_lines.append(f"- `{workflow['id']}` actions: {action_ids}")
    action_support_lines = []
    for backend_name, payload in support_matrix.items():
        workflow_support = payload.get("workflow_support", {})
        for workflow_id, support in workflow_support.items():
            actions = support.get("actions") or {}
            if not actions:
                continue
            supported = ", ".join(
                action_id for action_id, ok in actions.items() if ok
            ) or "none"
            unsupported = ", ".join(
                action_id for action_id, ok in actions.items() if not ok
            ) or "none"
            action_support_lines.append(
                f"- `{backend_name}` `{workflow_id}` supported: {supported}; "
                f"unsupported: {unsupported}"
            )
        action_support_lines.extend(_backend_operation_notes(backend_name, payload))
    error_lines = "\n".join(
        f"- `{entry['code']}`: {entry['description']}" for entry in error_taxonomy
    )
    support_block = "\n".join(support_lines)
    action_block = "\n".join(action_lines)
    action_support_block = "\n".join(action_support_lines)

    return (
        "# Generated Anki Catalog Reference\n\n"
        f"Schema version: `{snapshot['schema_version']}`\n\n"
        "This file is generated from `ankicli.app.catalog`.\n\n"
        "## Workflows\n\n"
        f"{workflow_lines}\n\n"
        "## Plugin Tools\n\n"
        f"{tool_lines}\n\n"
        "## Backend Workflow Support\n\n"
        f"{support_block}\n\n"
        "## Workflow Actions\n\n"
        f"{action_block}\n\n"
        "## Backend Action Support\n\n"
        f"{action_support_block}\n\n"
        "## Deck Stats Contract\n\n"
        "- `deck stats` returns `id`, `name`, `note_count`, `card_count`, "
        "`due_count`, `new_count`, `learning_count`, and `review_count`.\n\n"
        "## Study Payload Contract\n\n"
        "- Study responses expose `current_card.study_view`, "
        "`current_card.media`, and `current_card.raw_fields`.\n"
        "- `study details` and compatible reveal-style outputs may also emit "
        "a top-level `kind: \"canvas\"` payload so OpenClaw can render the "
        "current card inline while preserving structured card fields.\n"
        "- `study_view` contains `rendered_front_html`, `rendered_back_html`, "
        "`rendered_front_telegram_html`, `rendered_back_telegram_html`, "
        "`front_card_text`, `back_card_text`, `prompt`, `answer`, "
        "`supporting`, and `raw_fields_available`.\n"
        "- `rendered_front_html` is returned when backend presentation is "
        "available; `rendered_back_html` is returned by `study details` and "
        "withheld on prompt-only study reads.\n"
        "- `rendered_front_telegram_html` is a best-effort Telegram-safe "
        "projection of rendered front HTML; `rendered_back_telegram_html` is "
        "returned by `study details` and withheld on prompt-only study reads.\n"
        "- `front_card_text` is always available when the prompt side can be "
        "normalized to text; `back_card_text` is returned by `study details` "
        "and withheld on prompt-only study reads.\n"
        "- `media.audio[]` and `media.images[]` entries include `tag`, "
        "`path`, `exists`, and `error_code`.\n\n"
        "## Media And Provider Errors\n\n"
        f"{error_lines}\n"
    )


def _operation_label(operation_id: str, prefix: str) -> str:
    return operation_id.removeprefix(prefix).replace("_", "-")


def _backend_operation_notes(backend_name: str, payload: dict) -> list[str]:
    operations = payload.get("operations") or {}
    media_operations = sorted(
        operation_id for operation_id in operations if operation_id.startswith("media.")
    )
    notes: list[str] = []
    if media_operations:
        supported = [
            _operation_label(operation_id, "media.")
            for operation_id in media_operations
            if operations.get(operation_id) is True
        ]
        unsupported = [
            _operation_label(operation_id, "media.")
            for operation_id in media_operations
            if operations.get(operation_id) is False
        ]
        notes.append(
            f"- `{backend_name}` media operations supported: {', '.join(supported) or 'none'}; "
            f"unsupported: {', '.join(unsupported) or 'none'}"
        )
    remote_families = ("auth.", "sync.", "backup.")
    remote_operations = [
        operation_id
        for operation_id in operations
        if operation_id.startswith(remote_families)
    ]
    if remote_operations and not any(
        operations.get(operation_id) for operation_id in remote_operations
    ):
        notes.append(
            f"- `{backend_name}` does not support auth, sync, or backup flows; "
            "use `python-anki` for those"
        )
    return notes


def generated_artifacts(snapshot: dict) -> dict[Path, str]:
    artifacts = {
        SKILLS_ROOT / skill["slug"] / "SKILL.md": render_skill(skill)
        for skill in snapshot["skills"]
    }
    artifacts[REFERENCE_PATH] = render_reference(snapshot)
    return artifacts


def write_artifacts(artifacts: dict[Path, str]) -> None:
    for path, content in artifacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_artifacts(artifacts: dict[Path, str]) -> list[Path]:
    stale: list[Path] = []
    for path, expected in artifacts.items():
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            stale.append(path)
    return stale


def main() -> int:
    args = parse_args()
    snapshot = catalog_snapshot()
    artifacts = generated_artifacts(snapshot)
    if args.check:
        stale = check_artifacts(artifacts)
        if stale:
            print("Generated OpenClaw artifacts are out of date:", file=sys.stderr)
            for path in stale:
                print(f"  - {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            print(
                "Run `uv run python scripts/generate_openclaw_artifacts.py`.",
                file=sys.stderr,
            )
            return 1
        return 0
    write_artifacts(artifacts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
