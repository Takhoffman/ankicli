"""Unified command proof and quality matrix helpers."""

from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ankicli.main import app
from ankicli.runtime import get_backend

PROOF_TYPES = frozenset(
    {
        "unit",
        "cli_contract",
        "backend_unit",
        "fixture_integration",
        "real_python_anki",
        "real_ankiconnect",
        "failure",
        "safety",
        "parity",
    },
)
BACKEND_SCOPES = frozenset({"python-anki", "ankiconnect", "both"})
RISKS = frozenset({"read", "write", "destructive", "sync", "restore"})
PHASES = ("phase1", "phase2", "phase3")
PROOF_EXECUTION_HINTS = {
    "fixture_integration": {
        "runner": (
            "PYTEST_PLUGINS=ankicli.pytest_plugin uv run pytest -c pyproject.toml "
            "tests/integration/test_python_anki_backend.py --proof-report /tmp/fixture.json"
        ),
        "requires_env": [],
        "tier": "fixture integration",
    },
    "real_python_anki": {
        "runner": (
            "PYTEST_PLUGINS=ankicli.pytest_plugin uv run pytest -c pyproject.toml "
            "-m backend_python_anki_backup_real --proof-report /tmp/real-python-anki.json"
        ),
        "requires_env": ["ANKI_SOURCE_PATH"],
        "tier": "real python-anki backup",
    },
    "safety": {
        "runner": (
            "PYTEST_PLUGINS=ankicli.pytest_plugin uv run pytest -c pyproject.toml "
            "tests/integration/test_python_anki_backend.py --proof-report /tmp/fixture.json"
        ),
        "requires_env": [],
        "tier": "fixture integration",
    },
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


@dataclass(frozen=True, slots=True)
class MatrixEntry:
    command: str
    backend_scope: str
    risk: str
    required_proofs: tuple[str, ...]
    not_applicable_proofs: tuple[str, ...]
    waived_proofs: tuple[str, ...]
    waiver_reason: str | None
    waiver_phase: str | None
    waiver_expires: str | None


@dataclass(frozen=True, slots=True)
class ProofAnnotation:
    command: str
    proofs: tuple[str, ...]
    file: str
    test_name: str


@dataclass(frozen=True, slots=True)
class CollectedProof:
    source: str
    nodeid: str
    command: str
    proofs: tuple[str, ...]
    file: str
    test_name: str


def implemented_commands() -> list[str]:
    commands: list[str] = []
    for group in app.registered_groups:
        for command in group.typer_instance.registered_commands:
            commands.append(f"{group.name}.{command.name}")
    return sorted(commands)


def summarize_backend_support(commands: list[str]) -> dict[str, dict[str, bool]]:
    summary: dict[str, dict[str, bool]] = {}
    for backend_name in ("python-anki", "ankiconnect"):
        capabilities = get_backend(backend_name).backend_capabilities()
        summary[backend_name] = {
            command: capabilities.supported_operations.get(
                COMMAND_TO_OPERATION.get(command, ""),
                True,
            )
            for command in commands
        }
    return summary


def _normalize_proofs(values: list[str], *, field_name: str, command: str) -> tuple[str, ...]:
    normalized = tuple(values)
    invalid = sorted(set(normalized) - PROOF_TYPES)
    if invalid:
        raise ValueError(
            f"{field_name} for {command} contains unknown proof types: {', '.join(invalid)}",
        )
    return normalized


def load_matrix(path: Path) -> tuple[str, dict[str, MatrixEntry]]:
    import yaml

    raw = yaml.safe_load(path.read_text()) or {}
    phase = raw.get("phase", "phase1")
    if phase not in PHASES:
        raise ValueError(f"Unknown matrix phase: {phase}")

    entries: dict[str, MatrixEntry] = {}
    for item in raw.get("commands", []):
        command = item["command"]
        backend_scope = item["backend_scope"]
        risk = item["risk"]
        if backend_scope not in BACKEND_SCOPES:
            raise ValueError(f"{command} has invalid backend_scope: {backend_scope}")
        if risk not in RISKS:
            raise ValueError(f"{command} has invalid risk: {risk}")
        required = _normalize_proofs(
            list(item.get("required_proofs", [])),
            field_name="required_proofs",
            command=command,
        )
        not_applicable = _normalize_proofs(
            list(item.get("not_applicable_proofs", [])),
            field_name="not_applicable_proofs",
            command=command,
        )
        waived = _normalize_proofs(
            list(item.get("waived_proofs", [])),
            field_name="waived_proofs",
            command=command,
        )
        if command in entries:
            raise ValueError(f"Duplicate matrix row for {command}")
        if set(required) & set(not_applicable):
            raise ValueError(f"{command} cannot require and mark the same proof as N/A")
        if not set(waived).issubset(required):
            raise ValueError(f"{command} waived_proofs must be a subset of required_proofs")
        if waived and not item.get("waiver_reason"):
            raise ValueError(f"{command} waived_proofs require waiver_reason")
        entries[command] = MatrixEntry(
            command=command,
            backend_scope=backend_scope,
            risk=risk,
            required_proofs=required,
            not_applicable_proofs=not_applicable,
            waived_proofs=waived,
            waiver_reason=item.get("waiver_reason"),
            waiver_phase=item.get("waiver_phase"),
            waiver_expires=item.get("waiver_expires"),
        )
    return phase, entries


def _decorator_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _constant_string(node: ast.AST) -> str:
    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
        raise ValueError("proof annotations must use string literal arguments")
    return node.value


def _iter_collectable_test_nodes(
    module: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    nodes: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in module.body:
        if isinstance(
            node,
            ast.FunctionDef | ast.AsyncFunctionDef,
        ) and node.name.startswith("test_"):
            nodes.append(node)
            continue
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for child in node.body:
                if isinstance(
                    child,
                    ast.FunctionDef | ast.AsyncFunctionDef,
                ) and child.name.startswith("test_"):
                    nodes.append(child)
    return nodes


def collect_proofs(tests_root: Path) -> tuple[list[ProofAnnotation], list[str]]:
    annotations: list[ProofAnnotation] = []
    errors: list[str] = []
    for path in sorted(tests_root.rglob("test_*.py")):
        module = ast.parse(path.read_text(), filename=str(path))
        for node in _iter_collectable_test_nodes(module):
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if _decorator_name(decorator.func) != "proves":
                    continue
                try:
                    if len(decorator.args) < 2:
                        raise ValueError(
                            "proves() requires a command id and at least one proof type",
                        )
                    command = _constant_string(decorator.args[0])
                    proofs = tuple(_constant_string(arg) for arg in decorator.args[1:])
                    invalid = sorted(set(proofs) - PROOF_TYPES)
                    if invalid:
                        raise ValueError(
                            f"unknown proof types in proves({command}): {', '.join(invalid)}",
                        )
                except ValueError as exc:
                    errors.append(f"{path}:{node.lineno}: {exc}")
                    continue
                annotations.append(
                    ProofAnnotation(
                        command=command,
                        proofs=proofs,
                        file=str(path),
                        test_name=node.name,
                    ),
                )
    return annotations, errors


def load_proof_report(
    path: Path,
) -> tuple[list[CollectedProof], set[str], set[tuple[str, str]], list[str]]:
    try:
        raw = json.loads(path.read_text())
    except FileNotFoundError:
        return [], set(), set(), [f"{path}: proof report not found"]
    except json.JSONDecodeError as exc:
        return [], set(), set(), [f"{path}: invalid proof report JSON: {exc}"]
    rows: list[CollectedProof] = []
    errors: list[str] = []
    source = path.name
    for item in raw.get("collected_proofs", []):
        try:
            nodeid = item["nodeid"]
            command = item["command"]
            file = item["file"]
            test_name = item["test_name"]
            proofs = _normalize_proofs(
                list(item.get("proofs", [])),
                field_name="proofs",
                command=command,
            )
            if not all(
                isinstance(value, str) and value
                for value in (nodeid, command, file, test_name)
            ):
                raise ValueError("collected proof rows require non-empty string fields")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{path}: invalid proof report row: {exc}")
            continue
        rows.append(
            CollectedProof(
                source=source,
                nodeid=nodeid,
                command=command,
                proofs=proofs,
                file=str(Path(file).resolve()),
                test_name=test_name,
            ),
        )
    collected_tests: set[tuple[str, str]] = set()
    for item in raw.get("collected_tests", []):
        try:
            file = item["file"]
            test_name = item["test_name"]
            if not all(isinstance(value, str) and value for value in (file, test_name)):
                raise ValueError("collected test rows require non-empty string fields")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{path}: invalid collected test row: {exc}")
            continue
        collected_tests.add((str(Path(file).resolve()), test_name))
    passed_nodeids = {
        nodeid
        for nodeid in raw.get("passed_nodeids", [])
        if isinstance(nodeid, str) and nodeid
    }
    return rows, passed_nodeids, collected_tests, errors


def load_proof_reports(
    paths: list[Path],
) -> tuple[list[CollectedProof], set[str], set[tuple[str, str]], list[str]]:
    all_rows: list[CollectedProof] = []
    all_passed_nodeids: set[str] = set()
    all_collected_tests: set[tuple[str, str]] = set()
    all_errors: list[str] = []
    for path in paths:
        rows, passed_nodeids, collected_tests, errors = load_proof_report(path)
        all_rows.extend(rows)
        all_passed_nodeids.update(passed_nodeids)
        all_collected_tests.update(collected_tests)
        all_errors.extend(errors)
    return all_rows, all_passed_nodeids, all_collected_tests, all_errors


def build_report(
    *,
    matrix_path: Path,
    tests_root: Path,
    proof_report_paths: list[Path] | None = None,
    phase_override: str | None = None,
) -> dict[str, Any]:
    phase, entries = load_matrix(matrix_path)
    phase = phase_override or phase
    if phase not in PHASES:
        raise ValueError(f"Unknown phase override: {phase}")

    commands = implemented_commands()
    backend_support = summarize_backend_support(commands)
    annotations, annotation_errors = collect_proofs(tests_root)
    proofs_by_command: dict[str, set[str]] = {}
    proof_sources_by_command: dict[str, set[str]] = {}
    stale_annotations: list[dict[str, str]] = []
    collected_proofs: list[CollectedProof] = []
    passed_nodeids: set[str] = set()
    collected_tests: set[tuple[str, str]] = set()
    if proof_report_paths:
        collected_proofs, passed_nodeids, collected_tests, report_errors = load_proof_reports(
            proof_report_paths,
        )
        annotation_errors.extend(report_errors)

    for annotation in annotations:
        if annotation.command not in commands:
            stale_annotations.append(
                {
                    "command": annotation.command,
                    "file": annotation.file,
                    "test_name": annotation.test_name,
                },
            )
            continue
        if proof_report_paths:
            test_key = (str(Path(annotation.file).resolve()), annotation.test_name)
            if test_key not in collected_tests:
                annotation_errors.append(
                    "non-collected proof annotation: "
                    f"{annotation.command} in {annotation.file}::{annotation.test_name}",
                )
    for row in collected_proofs:
        if row.command not in commands:
            stale_annotations.append(
                {
                    "command": row.command,
                    "file": row.file,
                    "test_name": row.test_name,
                },
            )
            continue
        if row.nodeid in passed_nodeids:
            proofs_by_command.setdefault(row.command, set()).update(row.proofs)
            proof_sources_by_command.setdefault(row.command, set()).add(row.source)

    matrix_missing = sorted(command for command in commands if command not in entries)
    stale_rows = sorted(command for command in entries if command not in commands)

    missing_required: dict[str, list[str]] = {}
    waived_gaps: dict[str, list[str]] = {}
    for command in commands:
        entry = entries.get(command)
        if entry is None:
            continue
        actual = proofs_by_command.get(command, set())
        required = set(entry.required_proofs) - set(entry.not_applicable_proofs)
        missing = sorted(required - actual)
        if not missing:
            continue
        waived = sorted(set(missing) & set(entry.waived_proofs))
        remaining = sorted(set(missing) - set(entry.waived_proofs))
        if waived:
            waived_gaps[command] = waived
        if remaining:
            missing_required[command] = remaining

    phase3_blockers_by_proof: dict[str, int] = {}
    phase3_blocking_commands_by_proof: dict[str, list[str]] = {}
    for missing in missing_required.values():
        for proof in missing:
            phase3_blockers_by_proof[proof] = phase3_blockers_by_proof.get(proof, 0) + 1
    for command, missing in missing_required.items():
        for proof in missing:
            phase3_blocking_commands_by_proof.setdefault(proof, []).append(command)
    execution_plan_groups: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for proof in sorted(phase3_blocking_commands_by_proof):
        hint = PROOF_EXECUTION_HINTS.get(proof, {})
        runner = hint.get("runner")
        tier = hint.get("tier")
        requires_env = tuple(sorted(hint.get("requires_env", [])))
        key = (tier, runner, requires_env)
        group = execution_plan_groups.setdefault(
            key,
            {
                "tier": tier,
                "runner": runner,
                "requires_env": list(requires_env),
                "proofs": [],
                "blocking_commands": set(),
            },
        )
        group["proofs"].append(proof)
        group["blocking_commands"].update(phase3_blocking_commands_by_proof[proof])
    execution_plan = [
        {
            "tier": item["tier"],
            "runner": item["runner"],
            "requires_env": item["requires_env"],
            "missing_env": [
                name for name in item["requires_env"] if not os.environ.get(name)
            ],
            "runnable": not any(
                not os.environ.get(name) for name in item["requires_env"]
            ),
            "proofs": sorted(item["proofs"]),
            "blocking_command_count": len(sorted(item["blocking_commands"])),
            "commands": sorted(item["blocking_commands"]),
        }
        for item in sorted(
            execution_plan_groups.values(),
            key=lambda value: (
                -len(value["blocking_commands"]),
                value["tier"] or "",
                value["runner"] or "",
            ),
        )
    ]
    best_next_action = execution_plan[0] if execution_plan else None
    runnable_actions = [item for item in execution_plan if item["runnable"]]
    if runnable_actions:
        best_next_action = runnable_actions[0]

    phase_failures: list[str] = []
    if annotation_errors:
        phase_failures.extend(annotation_errors)
    if stale_rows:
        phase_failures.extend(f"stale matrix row: {command}" for command in stale_rows)
    if stale_annotations:
        phase_failures.extend(
            f"stale proof annotation: {item['command']} in {item['file']}::{item['test_name']}"
            for item in stale_annotations
        )
    if phase in {"phase2", "phase3"}:
        if not proof_report_paths:
            phase_failures.append(
                "at least one proof report path is required for phase2/phase3 enforcement",
            )
        phase_failures.extend(f"missing matrix row: {command}" for command in matrix_missing)
        for command, missing in sorted(missing_required.items()):
            core_missing = [item for item in missing if item in {"unit", "cli_contract"}]
            if core_missing:
                phase_failures.append(
                    f"{command} missing core proofs: {', '.join(core_missing)}",
                )
    if phase == "phase3":
        for command, missing in sorted(missing_required.items()):
            phase_failures.append(f"{command} missing proofs: {', '.join(missing)}")

    return {
        "phase": phase,
        "implemented_commands": commands,
        "implemented_count": len(commands),
        "matrix_entry_count": len(entries),
        "commands_missing_matrix_rows": matrix_missing,
        "stale_matrix_rows": stale_rows,
        "stale_proof_annotations": stale_annotations,
        "annotation_errors": annotation_errors,
        "missing_required_proofs": missing_required,
        "waived_proof_gaps": waived_gaps,
        "backend_support": backend_support,
        "proof_report_summaries": [
            {
                "source": source,
                "passed_nodeids": len(
                    {
                        row.nodeid
                        for row in collected_proofs
                        if row.source == source
                    }
                    & passed_nodeids,
                ),
                "proved_commands": len(
                    {
                        row.command
                        for row in collected_proofs
                        if row.source == source and row.nodeid in passed_nodeids
                    },
                ),
                "proved_proofs": len(
                    {
                        (row.command, proof)
                        for row in collected_proofs
                        if row.source == source and row.nodeid in passed_nodeids
                        for proof in row.proofs
                    },
                ),
            }
            for source in sorted({row.source for row in collected_proofs})
        ],
        "proofs_by_command": {
            command: sorted(values)
            for command, values in proofs_by_command.items()
        },
        "proof_sources_by_command": {
            command: sorted(values)
            for command, values in proof_sources_by_command.items()
        },
        "phase3_readiness": {
            "ready": not missing_required,
            "blocking_command_count": len(missing_required),
            "blocking_proof_counts": {
                proof: phase3_blockers_by_proof[proof]
                for proof in sorted(phase3_blockers_by_proof)
            },
            "best_next_action": best_next_action,
            "execution_plan": execution_plan,
        },
        "phase_failures": phase_failures,
        "ok": not phase_failures,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "Quality Matrix Audit",
        "",
        f"Phase: {report['phase']}",
        f"Implemented commands: {report['implemented_count']}",
        f"Matrix entries: {report['matrix_entry_count']}",
        f"Missing matrix rows: {len(report['commands_missing_matrix_rows'])}",
        f"Commands missing required proofs: {len(report['missing_required_proofs'])}",
        f"Stale matrix rows: {len(report['stale_matrix_rows'])}",
        f"Stale proof annotations: {len(report['stale_proof_annotations'])}",
    ]
    if report["commands_missing_matrix_rows"]:
        lines.extend(
            ["", "Commands missing matrix rows:"]
            + [f"  - {command}" for command in report["commands_missing_matrix_rows"][:20]],
        )
    if report["missing_required_proofs"]:
        lines.append("")
        lines.append("Missing required proofs:")
        for command, missing in list(sorted(report["missing_required_proofs"].items()))[:20]:
            lines.append(f"  - {command}: {', '.join(missing)}")
    if report["proof_report_summaries"]:
        lines.append("")
        lines.append("Proof report summaries:")
        for item in report["proof_report_summaries"]:
            lines.append(
                "  - "
                f"{item['source']}: commands={item['proved_commands']}, "
                f"proofs={item['proved_proofs']}, passed_tests={item['passed_nodeids']}",
            )
    lines.append("")
    lines.append(
        "Phase3 readiness: "
        f"ready={report['phase3_readiness']['ready']}, "
        f"blocking_commands={report['phase3_readiness']['blocking_command_count']}",
    )
    if report["phase3_readiness"]["blocking_proof_counts"]:
        for proof, count in report["phase3_readiness"]["blocking_proof_counts"].items():
            lines.append(f"  - {proof}: {count}")
    if report["phase3_readiness"]["best_next_action"]:
        action = report["phase3_readiness"]["best_next_action"]
        lines.append(
            "Best next action: "
            f"proofs={','.join(action['proofs'])}, "
            f"tier={action['tier']}, "
            f"blocking_commands={action['blocking_command_count']}, "
            f"runnable={action['runnable']}",
        )
        if action["missing_env"]:
            lines.append(f"  missing_env={','.join(action['missing_env'])}")
        if action["runner"]:
            lines.append(f"  runner={action['runner']}")
    if report["phase3_readiness"]["execution_plan"]:
        lines.append("Phase3 execution plan:")
        for item in report["phase3_readiness"]["execution_plan"]:
            lines.append(
                "  - "
                f"proofs={','.join(item['proofs'])}: tier={item['tier']}, "
                f"blocking_commands={item['blocking_command_count']}, "
                f"runnable={item['runnable']}",
            )
            if item["missing_env"]:
                lines.append(f"    missing_env={','.join(item['missing_env'])}")
            if item["runner"]:
                lines.append(f"    runner={item['runner']}")
    if report["stale_matrix_rows"]:
        lines.extend(
            ["", "Stale matrix rows:"]
            + [f"  - {command}" for command in report["stale_matrix_rows"]],
        )
    if report["stale_proof_annotations"]:
        lines.append("")
        lines.append("Stale proof annotations:")
        for item in report["stale_proof_annotations"][:20]:
            lines.append(f"  - {item['command']} in {item['file']}::{item['test_name']}")
    if report["waived_proof_gaps"]:
        lines.append("")
        lines.append("Waived proof gaps:")
        for command, missing in list(sorted(report["waived_proof_gaps"].items()))[:20]:
            lines.append(f"  - {command}: {', '.join(missing)}")
    lines.append("")
    lines.append(f"OK: {report['ok']}")
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Quality Matrix Audit",
        "",
        f"- Phase: `{report['phase']}`",
        f"- Implemented commands: `{report['implemented_count']}`",
        f"- Matrix entries: `{report['matrix_entry_count']}`",
        f"- Missing matrix rows: `{len(report['commands_missing_matrix_rows'])}`",
        f"- Commands missing required proofs: `{len(report['missing_required_proofs'])}`",
        "",
    ]
    if report["commands_missing_matrix_rows"]:
        lines.extend(["## Commands Missing Matrix Rows", ""])
        lines.extend(f"- `{command}`" for command in report["commands_missing_matrix_rows"])
        lines.append("")
    if report["missing_required_proofs"]:
        lines.extend(["## Missing Required Proofs", ""])
        for command, missing in sorted(report["missing_required_proofs"].items()):
            lines.append(f"- `{command}`: `{', '.join(missing)}`")
        lines.append("")
    if report["proof_report_summaries"]:
        lines.extend(["## Proof Report Summaries", ""])
        for item in report["proof_report_summaries"]:
            lines.append(
                f"- `{item['source']}`: commands=`{item['proved_commands']}`, "
                f"proofs=`{item['proved_proofs']}`, passed_tests=`{item['passed_nodeids']}`",
            )
        lines.append("")
    lines.extend(["## Phase3 Readiness", ""])
    lines.append(f"- Ready: `{report['phase3_readiness']['ready']}`")
    lines.append(
        f"- Blocking commands: `{report['phase3_readiness']['blocking_command_count']}`",
    )
    if report["phase3_readiness"]["blocking_proof_counts"]:
        for proof, count in report["phase3_readiness"]["blocking_proof_counts"].items():
            lines.append(f"- `{proof}`: `{count}`")
    if report["phase3_readiness"]["best_next_action"]:
        action = report["phase3_readiness"]["best_next_action"]
        lines.append("")
        lines.append("### Best Next Action")
        lines.append("")
        lines.append(
            f"- proofs=`{', '.join(action['proofs'])}`: tier=`{action['tier']}`, "
            f"blocking_commands=`{action['blocking_command_count']}`, "
            f"runnable=`{action['runnable']}`",
        )
        if action["missing_env"]:
            lines.append(f"  missing_env: `{', '.join(action['missing_env'])}`")
        if action["runner"]:
            lines.append(f"  runner: `{action['runner']}`")
    if report["phase3_readiness"]["execution_plan"]:
        lines.append("")
        lines.append("### Execution Plan")
        lines.append("")
        for item in report["phase3_readiness"]["execution_plan"]:
            lines.append(
                f"- proofs=`{', '.join(item['proofs'])}`: tier=`{item['tier']}`, "
                f"blocking_commands=`{item['blocking_command_count']}`, "
                f"runnable=`{item['runnable']}`",
            )
            if item["missing_env"]:
                lines.append(f"  missing_env: `{', '.join(item['missing_env'])}`")
            if item["runner"]:
                lines.append(f"  runner: `{item['runner']}`")
    lines.append("")
    if report["stale_matrix_rows"]:
        lines.extend(["## Stale Matrix Rows", ""])
        lines.extend(f"- `{command}`" for command in report["stale_matrix_rows"])
        lines.append("")
    if report["stale_proof_annotations"]:
        lines.extend(["## Stale Proof Annotations", ""])
        for item in report["stale_proof_annotations"]:
            lines.append(f"- `{item['command']}` in `{item['file']}::{item['test_name']}`")
        lines.append("")
    return "\n".join(lines).rstrip()
