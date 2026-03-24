#!/usr/bin/env python3
"""Prepare a wheel-backed real python-anki validation environment."""

from __future__ import annotations

import argparse
import importlib
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare env vars and a real collection for backend_python_anki_real.",
    )
    parser.add_argument(
        "--anki-version",
        default="25.9.2",
        help="Official anki wheel version to install into the current environment.",
    )
    parser.add_argument(
        "--collection-path",
        default="/tmp/ankicli-real-validation.anki2",
        help="Path to the real collection file to create or reuse.",
    )
    parser.add_argument(
        "--shim-root",
        default="/tmp/anki-wheel",
        help="Root path used for the ANKI_SOURCE_PATH shim.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete any existing collection before preparing the validation fixture.",
    )
    parser.add_argument(
        "--front",
        default="hello",
        help="Front field value for the seed note when a new collection is created.",
    )
    parser.add_argument(
        "--back",
        default="world",
        help="Back field value for the seed note when a new collection is created.",
    )
    parser.add_argument(
        "--tag",
        default="tag1",
        help="Seed tag value to apply to the prepared validation note.",
    )
    return parser.parse_args()


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def install_anki(version: str) -> None:
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            f"anki=={version}",
        ],
    )


def import_anki_module():
    importlib.invalidate_caches()
    return importlib.import_module("anki")


def create_shim(shim_root: Path, package_dir: Path) -> Path:
    pylib_dir = shim_root / "pylib"
    pylib_dir.mkdir(parents=True, exist_ok=True)
    target = pylib_dir / "anki"
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)
    target.symlink_to(package_dir, target_is_directory=True)
    return shim_root.resolve()


def prepare_collection(
    collection_path: Path,
    front: str,
    back: str,
    tag: str,
) -> dict[str, int | str]:
    from anki.collection import Collection

    collection_path.parent.mkdir(parents=True, exist_ok=True)
    col = Collection(str(collection_path))
    try:
        note_ids = [int(note_id) for note_id in col.find_notes("")]
        if not note_ids:
            model = col.models.by_name("Basic")
            if model is None:
                raise RuntimeError('Expected stock model "Basic" to exist')
            deck_id = None
            for deck in col.decks.all_names_and_ids():
                if deck.name == "Default":
                    deck_id = int(deck.id)
                    break
            if deck_id is None:
                raise RuntimeError('Expected stock deck "Default" to exist')

            note = col.new_note(model)
            note["Front"] = front
            note["Back"] = back
            if tag:
                note.add_tag(tag)
            col.add_note(note, deck_id)
            note_ids = [int(note.id)]
        elif tag:
            note = col.get_note(note_ids[0])
            if note is None:
                raise RuntimeError("Expected prepared note to be readable")
            existing_tags = {str(existing_tag) for existing_tag in getattr(note, "tags", [])}
            if tag not in existing_tags:
                note.add_tag(tag)
                note.flush()

        card_ids = [int(card_id) for card_id in col.find_cards("")]
        if not card_ids:
            raise RuntimeError("Expected at least one card in prepared collection")

        return {
            "note_id": note_ids[0],
            "card_id": card_ids[0],
            "deck": "Default",
            "model": "Basic",
            "tag": tag,
        }
    finally:
        col.close()


def main() -> int:
    args = parse_args()
    collection_path = Path(args.collection_path).expanduser()
    media_path = collection_path.with_suffix(".media")
    shim_root = Path(args.shim_root).expanduser()

    if args.reset:
        if collection_path.exists():
            collection_path.unlink()
        if media_path.exists():
            shutil.rmtree(media_path)

    install_anki(args.anki_version)
    anki_module = import_anki_module()
    package_dir = Path(anki_module.__path__[0]).resolve()
    shim_path = create_shim(shim_root, package_dir)
    prepared = prepare_collection(collection_path, args.front, args.back, args.tag)

    print("# Export these in your shell before running the real backend suite.")
    print(f'export ANKI_SOURCE_PATH="{shim_path}"')
    print(f'export ANKICLI_REAL_COLLECTION="{collection_path.resolve()}"')
    print(f'export ANKICLI_REAL_NOTE_ID="{prepared["note_id"]}"')
    print(f'export ANKICLI_REAL_CARD_ID="{prepared["card_id"]}"')
    print(f'export ANKICLI_REAL_DECK="{prepared["deck"]}"')
    print(f'export ANKICLI_REAL_MODEL="{prepared["model"]}"')
    print(f'export ANKICLI_REAL_TAG="{prepared["tag"]}"')
    print("UV_CACHE_DIR=.uv-cache uv run pytest -m backend_python_anki_real")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
