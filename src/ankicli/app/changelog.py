"""Load and slice the project changelog for CLI display."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from ankicli.app.errors import ValidationError


@dataclass(frozen=True, slots=True)
class ChangelogSelection:
    title: str
    content: str
    full: bool


def _source_tree_changelog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "CHANGELOG.md"


def _read_changelog_text() -> tuple[str, str]:
    package_changelog = resources.files("ankicli").joinpath("CHANGELOG.md")
    try:
        return package_changelog.read_text(encoding="utf-8"), "package"
    except FileNotFoundError:
        source_changelog = _source_tree_changelog_path()
        if source_changelog.exists():
            return source_changelog.read_text(encoding="utf-8"), str(source_changelog)
    raise ValidationError("CHANGELOG.md is not available in this installation")


def _latest_section(markdown: str) -> ChangelogSelection:
    lines = markdown.splitlines()
    start = next((index for index, line in enumerate(lines) if line.startswith("## ")), None)
    if start is None:
        return ChangelogSelection(title="Changelog", content=markdown.strip(), full=True)
    end = next(
        (
            index
            for index, line in enumerate(lines[start + 1 :], start=start + 1)
            if line.startswith("## ")
        ),
        len(lines),
    )
    title = lines[start].lstrip("#").strip()
    content = "\n".join(lines[start:end]).strip()
    return ChangelogSelection(title=title, content=content, full=False)


def changelog_report(*, include_all: bool) -> dict:
    markdown, source = _read_changelog_text()
    if include_all:
        selection = ChangelogSelection(title="Changelog", content=markdown.strip(), full=True)
    else:
        selection = _latest_section(markdown)
    return {
        "title": selection.title,
        "content": selection.content,
        "full": selection.full,
        "source": source,
    }
