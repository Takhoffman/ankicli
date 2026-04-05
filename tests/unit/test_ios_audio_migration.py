from __future__ import annotations

import json
from pathlib import Path

from ankicli.app.ios_audio_migration import (
    SOUND_RE,
    SoundUsage,
    apply_manifest,
    build_manifest,
    create_backup_bundle,
    deterministic_target_filename,
    find_sound_usages,
    manifest_hash,
    replace_sound_reference,
    verify_manifest,
)


class _FakeExecutor:
    def __init__(self, notes: dict[int, dict]) -> None:
        self.notes = {note_id: json.loads(json.dumps(note)) for note_id, note in notes.items()}
        self.updated: list[tuple[int, dict[str, str]]] = []

    def iter_notes(self, *, query: str, page_size: int = 500) -> list[dict]:
        del query, page_size
        return [json.loads(json.dumps(self.notes[note_id])) for note_id in sorted(self.notes)]

    def get_note(self, note_id: int) -> dict:
        return json.loads(json.dumps(self.notes[note_id]))

    def update_note_fields(self, *, note_id: int, field_updates: dict[str, str]) -> dict:
        self.updated.append((note_id, dict(field_updates)))
        for field_name, value in field_updates.items():
            self.notes[note_id]["fields"][field_name] = value
        return {"id": note_id, "updated_fields": sorted(field_updates)}


def test_find_sound_usages_filters_to_ogg_and_opus() -> None:
    note = {
        "id": 10,
        "fields": {
            "Front": "a [sound:keep.mp3] b [sound:move.ogg]",
            "Back": "[sound:voice.opus]",
        },
    }

    usages = find_sound_usages(note)

    assert usages == [
        SoundUsage(
            note_id=10,
            field_name="Back",
            source_filename="voice.opus",
            original_field_value="[sound:voice.opus]",
        ),
        SoundUsage(
            note_id=10,
            field_name="Front",
            source_filename="move.ogg",
            original_field_value="a [sound:keep.mp3] b [sound:move.ogg]",
        ),
    ]


def test_replace_sound_reference_only_replaces_exact_token() -> None:
    value = "[sound:a.ogg] [sound:a.ogg] [sound:ab.ogg]"

    replaced = replace_sound_reference(
        value=value,
        source_filename="a.ogg",
        target_filename="a.ogg.ios.m4a",
    )

    assert replaced == "[sound:a.ogg.ios.m4a] [sound:a.ogg.ios.m4a] [sound:ab.ogg]"


def test_deterministic_target_filename_is_stable_and_unique_by_extension() -> None:
    assert deterministic_target_filename("clip.ogg") == "clip.ogg.ios.m4a"
    assert deterministic_target_filename("clip.opus") == "clip.opus.ios.m4a"


def test_build_manifest_is_sorted_and_collapses_shared_source(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "b.opus").write_text("opus")
    (media_dir / "a.ogg").write_text("ogg")
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    notes = {
        2: {
            "id": 2,
            "fields": {
                "Back": "[sound:b.opus]",
                "Front": "[sound:a.ogg]",
            },
        },
        1: {
            "id": 1,
            "fields": {
                "Front": "[sound:a.ogg]",
            },
        },
    }

    manifest = build_manifest(
        profile_name="User 1",
        media_dir=media_dir,
        backup_dir=backup_dir,
        collection_path=collection_path,
        backend="ankiconnect",
        query="",
        executor=_FakeExecutor(notes),
        probe_fn=lambda path: {"codec_name": "opus", "format_name": "ogg"},
    )

    assert [entry["source_filename"] for entry in manifest["entries"]] == ["a.ogg", "b.opus"]
    assert manifest["entries"][0]["usages"] == [
        {
            "field_name": "Front",
            "note_id": 1,
            "original_field_value": "[sound:a.ogg]",
        },
        {
            "field_name": "Front",
            "note_id": 2,
            "original_field_value": "[sound:a.ogg]",
        },
    ]
    assert manifest["manifest_hash"] == manifest_hash(manifest)


def test_create_backup_bundle_copies_native_backup_and_sources(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    native_backup = backup_dir / "backup-1.colpkg"
    native_backup.write_text("backup")
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    source = media_dir / "clip.ogg"
    source.write_text("audio")
    manifest = {
        "manifest_hash": "abc123",
        "backup_dir": str(backup_dir),
        "entries": [
            {
                "source_filename": "clip.ogg",
                "source_path": str(source),
                "target_filename": "clip.ogg.ios.m4a",
                "usages": [
                    {
                        "note_id": 1,
                        "field_name": "Front",
                        "original_field_value": "[sound:clip.ogg]",
                    },
                ],
            },
        ],
    }

    backup_bundle = create_backup_bundle(manifest=manifest, output_root=tmp_path / "output")

    assert (backup_bundle / "native-backup" / native_backup.name).exists()
    assert (backup_bundle / "source-media" / "clip.ogg").exists()
    rollback_map = json.loads((backup_bundle / "rollback-map.json").read_text())
    assert rollback_map == [
        {
            "field_name": "Front",
            "note_id": 1,
            "original_field_value": "[sound:clip.ogg]",
            "replacement_filename": "clip.ogg.ios.m4a",
            "source_filename": "clip.ogg",
        },
    ]


def test_apply_manifest_converts_updates_and_verifies(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "backup-1.colpkg").write_text("backup")
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    source = media_dir / "clip.ogg"
    source.write_text("audio")
    notes = {
        1: {
            "id": 1,
            "fields": {
                "Front": "hello [sound:clip.ogg]",
            },
        },
    }
    executor = _FakeExecutor(notes)
    manifest = {
        "manifest_hash": "abc123",
        "backup_dir": str(backup_dir),
        "entries": [
            {
                "source_filename": "clip.ogg",
                "source_path": str(source),
                "target_filename": "clip.ogg.ios.m4a",
                "target_path": str(media_dir / "clip.ogg.ios.m4a"),
                "convertible": True,
                "usages": [
                    {
                        "note_id": 1,
                        "field_name": "Front",
                        "original_field_value": "hello [sound:clip.ogg]",
                    },
                ],
            },
        ],
    }

    report = apply_manifest(
        manifest=manifest,
        output_root=tmp_path / "output",
        executor=executor,
        probe_fn=lambda path: {"codec_name": "aac", "format_name": "mov,mp4,m4a,3gp,3g2,mj2"}
        if path.suffix == ".m4a"
        else {"codec_name": "opus", "format_name": "ogg"},
        convert_fn=lambda source_path, target_path: target_path.write_text(source_path.read_text()),
    )

    assert report["failed_items"] == []
    assert (media_dir / "clip.ogg.ios.m4a").exists()
    assert executor.notes[1]["fields"]["Front"] == "hello [sound:clip.ogg.ios.m4a]"


def test_apply_manifest_skips_missing_source(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "backup-1.colpkg").write_text("backup")
    executor = _FakeExecutor({})
    manifest = {
        "manifest_hash": "abc123",
        "backup_dir": str(backup_dir),
        "entries": [
            {
                "source_filename": "missing.ogg",
                "source_path": str(tmp_path / "media" / "missing.ogg"),
                "target_filename": "missing.ogg.ios.m4a",
                "target_path": str(tmp_path / "media" / "missing.ogg.ios.m4a"),
                "convertible": False,
                "usages": [],
            },
        ],
    }

    report = apply_manifest(
        manifest=manifest,
        output_root=tmp_path / "output",
        executor=executor,
        probe_fn=lambda path: {"codec_name": "aac", "format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
        convert_fn=lambda source_path, target_path: None,
    )

    assert report["skipped_items"] == [
        {
            "reason": "missing_source",
            "source_filename": "missing.ogg",
        },
    ]


def test_verify_manifest_reports_stale_references(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "clip.ogg.ios.m4a").write_text("audio")
    executor = _FakeExecutor(
        {
            1: {
                "id": 1,
                "fields": {
                    "Front": "hello [sound:clip.ogg]",
                },
            },
        },
    )
    manifest = {
        "manifest_hash": "abc123",
        "entries": [
            {
                "source_filename": "clip.ogg",
                "target_filename": "clip.ogg.ios.m4a",
                "target_path": str(media_dir / "clip.ogg.ios.m4a"),
                "usages": [
                    {
                        "note_id": 1,
                        "field_name": "Front",
                        "original_field_value": "hello [sound:clip.ogg]",
                    },
                ],
            },
        ],
    }

    report = verify_manifest(manifest=manifest, executor=executor)

    assert report["failed_items"] == [
        {
            "field_name": "Front",
            "note_id": 1,
            "reason": "stale_reference",
            "source_filename": "clip.ogg",
        },
    ]


def test_sound_regex_matches_expected_token() -> None:
    assert SOUND_RE.findall("x [sound:a.ogg] y [sound:b.mp3]") == ["a.ogg", "b.mp3"]
