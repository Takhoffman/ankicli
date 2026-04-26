"""Generate OpenClaw plugin skills and catalog reference docs from ankicli catalog."""

from __future__ import annotations

from pathlib import Path

from ankicli.app.catalog import catalog_snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "integrations" / "openclaw-plugin" / "skills"
REFERENCE_PATH = REPO_ROOT / "docs" / "anki-catalog-reference.md"


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
    error_lines = "\n".join(
        f"- `{entry['code']}`: {entry['description']}" for entry in error_taxonomy
    )

    return (
        "# Generated Anki Catalog Reference\n\n"
        f"Schema version: `{snapshot['schema_version']}`\n\n"
        "This file is generated from `ankicli.app.catalog`.\n\n"
        "## Workflows\n\n"
        f"{workflow_lines}\n\n"
        "## Plugin Tools\n\n"
        f"{tool_lines}\n\n"
        "## Backend Workflow Support\n\n"
        f"{'\n'.join(support_lines)}\n\n"
        "## Workflow Actions\n\n"
        f"{'\n'.join(action_lines)}\n\n"
        "## Backend Action Support\n\n"
        f"{'\n'.join(action_support_lines)}\n\n"
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


def main() -> None:
    snapshot = catalog_snapshot()
    for skill in snapshot["skills"]:
        skill_dir = SKILLS_ROOT / skill["slug"]
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(render_skill(skill), encoding="utf-8")
    REFERENCE_PATH.write_text(render_reference(snapshot), encoding="utf-8")


if __name__ == "__main__":
    main()
