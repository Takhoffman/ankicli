"""Install bundled ankicli agent skill bundles into local agent homes."""

from __future__ import annotations

import importlib.resources
import shutil
from dataclasses import dataclass
from pathlib import Path

from ankicli.app.errors import ValidationError


@dataclass(frozen=True, slots=True)
class SkillBundleSpec:
    name: str
    description: str


SKILL_BUNDLE = SkillBundleSpec(
    name="ankicli",
    description=(
        "Umbrella ankicli agent skill with progressive-disclosure references for setup, "
        "study, note authoring, collection management, diagnostics, sync, and learning plans."
    ),
)


def _source_skills_root() -> Path:
    packaged = importlib.resources.files("ankicli").joinpath("skills")
    if packaged.is_dir():
        return Path(str(packaged))
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "skills"
        if candidate.is_dir():
            return candidate
    raise ValidationError("Bundled ankicli skills are not available")


def _bundle_source_dir() -> Path:
    source = _source_skills_root() / SKILL_BUNDLE.name
    if not source.is_dir():
        raise ValidationError("Bundled ankicli skill bundle is missing")
    return source


def _bundle_files(root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    )


def _agent_home(target: str) -> Path:
    if target == "codex":
        return Path.home() / ".codex" / "skills"
    if target == "claude":
        return Path.home() / ".claude" / "skills"
    if target == "openclaw":
        return Path.home() / ".openclaw" / "skills"
    raise ValidationError(
        f"Unsupported skill target: {target}",
        details={"supported_targets": ["codex", "claude", "openclaw", "all"]},
    )


def detected_skill_targets() -> list[str]:
    targets: list[str] = []
    if (Path.home() / ".codex").exists():
        targets.append("codex")
    if (Path.home() / ".claude").exists():
        targets.append("claude")
    if (Path.home() / ".openclaw").exists():
        targets.append("openclaw")
    return targets


def skill_list_payload() -> dict:
    return {
        "items": [
            {
                "name": SKILL_BUNDLE.name,
                "description": SKILL_BUNDLE.description,
                "source": f"skills/{SKILL_BUNDLE.name}/SKILL.md",
            }
        ],
        "targets": {
            "codex": str(_agent_home("codex")),
            "claude": str(_agent_home("claude")),
            "openclaw": str(_agent_home("openclaw")),
        },
        "detected_targets": detected_skill_targets(),
    }


def _install_one_bundle(*, root: Path, overwrite: bool) -> dict:
    source = _bundle_source_dir()
    destination = root / SKILL_BUNDLE.name
    if destination.exists():
        if not overwrite:
            return {
                "bundle": SKILL_BUNDLE.name,
                "status": "skipped",
                "reason": "already_exists",
                "path": str(destination),
                "files": _bundle_files(destination),
            }
        shutil.rmtree(destination)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    for path in destination.rglob("*"):
        if path.is_file():
            try:
                path.chmod(0o600)
            except OSError:
                pass
        elif path.is_dir():
            try:
                path.chmod(0o700)
            except OSError:
                pass
    return {
        "bundle": SKILL_BUNDLE.name,
        "status": "installed",
        "path": str(destination),
        "files": _bundle_files(destination),
    }


def install_skills(
    *,
    target: str | None = None,
    path: str | None = None,
    overwrite: bool = False,
) -> dict:
    if path and target == "all":
        raise ValidationError("--target all cannot be combined with --path")
    if path:
        roots = [{"target": "custom", "root": Path(path).expanduser()}]
    elif target == "all":
        roots = [
            {"target": "codex", "root": _agent_home("codex")},
            {"target": "claude", "root": _agent_home("claude")},
            {"target": "openclaw", "root": _agent_home("openclaw")},
        ]
    else:
        selected_target = target or "codex"
        roots = [{"target": selected_target, "root": _agent_home(selected_target)}]
    installed_targets = []
    for item in roots:
        installed_targets.append(
            {
                "target": item["target"],
                "root": str(item["root"]),
                "bundle": _install_one_bundle(root=item["root"], overwrite=overwrite),
            }
        )
    return {
        "bundle": SKILL_BUNDLE.name,
        "targets": installed_targets,
        "overwrite": overwrite,
    }
