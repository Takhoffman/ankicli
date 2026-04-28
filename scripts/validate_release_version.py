"""Validate that a release tag matches the packaged project version."""

from __future__ import annotations

import argparse
import ast
import os
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tag_version(tag_name: str) -> str:
    tag = tag_name.removeprefix("refs/tags/")
    if not tag.startswith("v") or tag == "v":
        raise ValueError(f"release tag must be formatted as v<version>; got {tag_name!r}")
    return tag[1:]


def _pyproject_version(root: Path) -> str:
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def _package_version(root: Path) -> str:
    module = ast.parse(
        (root / "src" / "ankicli" / "__init__.py").read_text(encoding="utf-8"),
        filename="src/ankicli/__init__.py",
    )
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        ):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise ValueError("src/ankicli/__init__.py does not define a string __version__")


def validate_release_version(*, root: Path, tag_name: str) -> list[str]:
    tag_version = _tag_version(tag_name)
    versions = {
        "tag": tag_version,
        "pyproject.toml": _pyproject_version(root),
        "src/ankicli/__init__.py": _package_version(root),
    }
    mismatches = [
        f"{name} declares {version!r}; expected {tag_version!r}"
        for name, version in versions.items()
        if version != tag_version
    ]
    return mismatches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tag",
        default=os.environ.get("GITHUB_REF_NAME", ""),
        help="Release tag name, for example v0.1.2.",
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    if not args.tag:
        print("Release tag is required via --tag or GITHUB_REF_NAME.", file=sys.stderr)
        return 2

    try:
        mismatches = validate_release_version(root=args.repo_root, tag_name=args.tag)
    except (KeyError, ValueError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f"Release version validation failed: {exc}", file=sys.stderr)
        return 1

    if mismatches:
        print("Release version validation failed:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"- {mismatch}", file=sys.stderr)
        print(
            "Update the project version files or create a tag that matches them exactly.",
            file=sys.stderr,
        )
        return 1

    print(f"Release version validation passed for {args.tag}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
