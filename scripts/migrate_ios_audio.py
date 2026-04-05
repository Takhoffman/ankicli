#!/usr/bin/env python3
"""Deterministically migrate iPhone-incompatible Anki audio to AAC M4A."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ankicli.app.ios_audio_migration import (
    AnkicliExecutor,
    apply_manifest,
    build_manifest,
    load_manifest,
    resolve_profile_paths,
    verify_manifest,
    write_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser(
        "inventory",
        help="Generate a deterministic migration manifest.",
    )
    inventory.add_argument("--backend", default="ankiconnect")
    inventory.add_argument("--profile", default="User 1")
    inventory.add_argument("--media-dir", help="Override the resolved media directory.")
    inventory.add_argument(
        "--output-root",
        default=str((Path.home() / "Desktop" / "ankicli-ios-audio-migration").resolve()),
    )
    inventory.add_argument("--query", default="")
    inventory.add_argument("--manifest")

    apply = subparsers.add_parser("apply", help="Apply a frozen migration manifest.")
    apply.add_argument("--backend", default="ankiconnect")
    apply.add_argument(
        "--output-root",
        default=str((Path.home() / "Desktop" / "ankicli-ios-audio-migration").resolve()),
    )
    apply.add_argument("--manifest", required=True)

    verify = subparsers.add_parser("verify", help="Verify a previously applied manifest.")
    verify.add_argument("--backend", default="ankiconnect")
    verify.add_argument("--manifest", required=True)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "inventory":
        paths = resolve_profile_paths(profile_name=args.profile)
        media_dir = (
            Path(args.media_dir).expanduser().resolve()
            if args.media_dir
            else paths["media_dir"]
        )
        output_root = Path(args.output_root).expanduser().resolve()
        executor = AnkicliExecutor(
            backend=args.backend,
            collection_path=paths["collection_path"] if args.backend == "python-anki" else None,
        )
        manifest = build_manifest(
            profile_name=args.profile,
            media_dir=media_dir,
            backup_dir=paths["backup_dir"],
            collection_path=paths["collection_path"],
            backend=args.backend,
            query=args.query,
            executor=executor,
        )
        manifest_path = (
            Path(args.manifest).expanduser().resolve()
            if args.manifest
            else output_root / "manifests" / f"{manifest['manifest_hash']}.json"
        )
        write_manifest(manifest_path, manifest)
        print(
            json.dumps(
                {
                    "manifest": str(manifest_path),
                    "manifest_hash": manifest["manifest_hash"],
                },
                indent=2,
                sort_keys=True,
            ),
        )
        return 0

    if args.command == "apply":
        manifest = load_manifest(Path(args.manifest).expanduser().resolve())
        collection_path = (
            Path(manifest["collection_path"])
            if args.backend == "python-anki"
            else None
        )
        executor = AnkicliExecutor(
            backend=args.backend,
            collection_path=collection_path,
        )
        report = apply_manifest(
            manifest=manifest,
            output_root=Path(args.output_root).expanduser().resolve(),
            executor=executor,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if not report["failed_items"] else 1

    if args.command == "verify":
        manifest = load_manifest(Path(args.manifest).expanduser().resolve())
        collection_path = (
            Path(manifest["collection_path"])
            if args.backend == "python-anki"
            else None
        )
        executor = AnkicliExecutor(
            backend=args.backend,
            collection_path=collection_path,
        )
        report = verify_manifest(manifest=manifest, executor=executor)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if not report["failed_items"] else 1

    print(f"unknown command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
