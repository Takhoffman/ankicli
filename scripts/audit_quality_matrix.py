#!/usr/bin/env python3
"""Audit command proof coverage against the unified matrix policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ankicli.app.quality_matrix import build_report, render_markdown, render_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the ankicli proof matrix.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--markdown", action="store_true", help="Emit a Markdown report.")
    parser.add_argument(
        "--phase",
        choices=("phase1", "phase2", "phase3"),
        help="Override the enforcement phase from the matrix file.",
    )
    parser.add_argument(
        "--matrix",
        default="ops/test-matrix.yaml",
        help="Path to the matrix YAML file.",
    )
    parser.add_argument(
        "--tests-root",
        default="tests",
        help="Path to the tests root to scan for proof annotations.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        matrix_path=Path(args.matrix).resolve(),
        tests_root=Path(args.tests_root).resolve(),
        phase_override=args.phase,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.markdown:
        print(render_markdown(report))
    else:
        print(render_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
