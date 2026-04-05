"""Deterministic iPhone-safe audio migration helpers."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ankicli.app.profiles import ProfileResolver
from ankicli.backends.ankiconnect import AnkiConnectBackend

SOUND_RE = re.compile(r"\[sound:([^\]\r\n]+)\]")
TARGET_CODEC = "aac"
TARGET_CONTAINER = "m4a"
TARGET_BITRATE = "128k"
TARGET_SAMPLE_RATE = "44100"
SUPPORTED_SOURCE_EXTENSIONS = {".ogg", ".opus"}
ANKICLI_COMMAND = ["uv", "run", "ankicli"]


@dataclass(frozen=True, slots=True)
class SoundUsage:
    note_id: int
    field_name: str
    source_filename: str
    original_field_value: str


def find_sound_usages(note: dict[str, Any]) -> list[SoundUsage]:
    note_id = int(note["id"])
    usages: list[SoundUsage] = []
    for field_name, field_value in sorted(note["fields"].items()):
        if not isinstance(field_value, str):
            continue
        for match in SOUND_RE.finditer(field_value):
            filename = match.group(1)
            if Path(filename).suffix.lower() not in SUPPORTED_SOURCE_EXTENSIONS:
                continue
            usages.append(
                SoundUsage(
                    note_id=note_id,
                    field_name=field_name,
                    source_filename=filename,
                    original_field_value=field_value,
                ),
            )
    return usages


def replace_sound_reference(*, value: str, source_filename: str, target_filename: str) -> str:
    source_token = f"[sound:{source_filename}]"
    target_token = f"[sound:{target_filename}]"
    return value.replace(source_token, target_token)


def deterministic_target_filename(source_filename: str) -> str:
    source_path = Path(source_filename)
    source_ext = source_path.suffix.lower().lstrip(".")
    stem = (
        source_path.name[: -len(source_path.suffix)]
        if source_path.suffix
        else source_path.name
    )
    return f"{stem}.{source_ext}.ios.{TARGET_CONTAINER}"


def _json_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _canonical_manifest_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    payload.pop("generated_at", None)
    payload.pop("manifest_hash", None)
    return payload


def manifest_hash(manifest: dict[str, Any]) -> str:
    return _json_hash(_canonical_manifest_payload(manifest))


class AnkicliExecutor:
    def __init__(
        self,
        *,
        backend: str,
        collection_path: Path | None = None,
        ankicli_command: list[str] | None = None,
        cwd: Path | None = None,
    ) -> None:
        self.backend = backend
        self.collection_path = collection_path
        self.ankicli_command = ankicli_command or list(ANKICLI_COMMAND)
        self.cwd = cwd

    def _run(self, args: list[str], *, input_text: str | None = None) -> dict[str, Any]:
        command = [*self.ankicli_command, "--json", "--backend", self.backend]
        if self.collection_path is not None:
            command.extend(["--collection", str(self.collection_path)])
        command.extend(args)
        result = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            cwd=self.cwd,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ankicli command failed ({result.returncode}): {' '.join(command)}\n"
                f"stdout={result.stdout}\nstderr={result.stderr}",
            )
        payload = self._decode_payload(result.stdout, command=command)
        if not payload.get("ok"):
            raise RuntimeError(
                "ankicli returned error payload: "
                f"{json.dumps(payload, sort_keys=True)}",
            )
        return payload["data"]

    @staticmethod
    def _decode_payload(stdout: str, *, command: list[str]) -> dict[str, Any]:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            start = stdout.find("{")
            if start != -1:
                try:
                    return json.loads(stdout[start:])
                except json.JSONDecodeError:
                    pass
        raise RuntimeError(
            "ankicli returned non-JSON stdout: "
            f"{' '.join(command)}\nstdout={stdout}",
        )

    def search_note_ids(self, *, query: str, page_size: int = 500) -> list[int]:
        first_page = self._run(
            [
                "search",
                "notes",
                "--query",
                query,
                "--limit",
                str(page_size),
                "--offset",
                "0",
            ],
        )
        total = int(first_page["total"])
        note_ids = [int(item["id"]) for item in first_page["items"]]
        for offset in range(page_size, total, page_size):
            page = self._run(
                [
                    "search",
                    "notes",
                    "--query",
                    query,
                    "--limit",
                    str(page_size),
                    "--offset",
                    str(offset),
                ],
            )
            note_ids.extend(int(item["id"]) for item in page["items"])
        return sorted(set(note_ids))

    def iter_notes(self, *, query: str, page_size: int = 500) -> list[dict[str, Any]]:
        if self.backend == "ankiconnect":
            note_ids = self.search_note_ids(query=query, page_size=page_size)
            return self._iter_notes_via_ankiconnect(note_ids=note_ids)

        first_page = self._run(
            [
                "search",
                "preview",
                "--kind",
                "notes",
                "--query",
                query,
                "--limit",
                str(page_size),
                "--offset",
                "0",
            ],
        )
        total = int(first_page["total"])
        notes = [dict(item) for item in first_page["items"]]
        for offset in range(page_size, total, page_size):
            page = self._run(
                [
                    "search",
                    "preview",
                    "--kind",
                    "notes",
                    "--query",
                    query,
                    "--limit",
                    str(page_size),
                    "--offset",
                    str(offset),
                ],
            )
            notes.extend(dict(item) for item in page["items"])
        return sorted(notes, key=lambda item: int(item["id"]))

    def _iter_notes_via_ankiconnect(
        self,
        *,
        note_ids: list[int],
        batch_size: int = 250,
    ) -> list[dict[str, Any]]:
        backend = AnkiConnectBackend()
        notes: list[dict[str, Any]] = []
        for offset in range(0, len(note_ids), batch_size):
            batch_ids = note_ids[offset : offset + batch_size]
            raw_notes = backend._invoke("notesInfo", {"notes": batch_ids})
            for raw_note in raw_notes:
                notes.append(
                    {
                        "id": int(raw_note.get("noteId", 0)),
                        "model": str(raw_note.get("modelName", "")),
                        "fields": {
                            str(name): str(value.get("value", ""))
                            for name, value in raw_note.get("fields", {}).items()
                        },
                        "tags": [str(tag) for tag in raw_note.get("tags", [])],
                    },
                )
        return sorted(notes, key=lambda item: int(item["id"]))

    def get_note(self, note_id: int) -> dict[str, Any]:
        return self._run(["note", "get", "--id", str(note_id)])

    def update_note_fields(self, *, note_id: int, field_updates: dict[str, str]) -> dict[str, Any]:
        args = ["note", "update", "--id", str(note_id)]
        for field_name, value in sorted(field_updates.items()):
            args.extend(["--field", f"{field_name}={value}"])
        return self._run(args)


def probe_media(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,codec_type,sample_rate,channels",
            "-show_entries",
            "format=format_name,duration",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    payload = json.loads(result.stdout)
    streams = payload.get("streams", [])
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    format_payload = payload.get("format", {})
    return {
        "codec_name": audio_stream.get("codec_name"),
        "sample_rate": audio_stream.get("sample_rate"),
        "channels": audio_stream.get("channels"),
        "format_name": format_payload.get("format_name"),
        "duration": format_payload.get("duration"),
    }


def convert_to_m4a(*, source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f"{target_path.stem}.",
        suffix=f".{target_path.suffix.lstrip('.')}",
        dir=str(target_path.parent),
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source_path),
                "-vn",
                "-c:a",
                TARGET_CODEC,
                "-b:a",
                TARGET_BITRATE,
                "-ar",
                TARGET_SAMPLE_RATE,
                str(tmp_path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed for {source_path}: {result.stderr.strip()}")
        tmp_path.replace(target_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def build_manifest(
    *,
    profile_name: str,
    media_dir: Path,
    backup_dir: Path,
    collection_path: Path,
    backend: str,
    query: str,
    executor: AnkicliExecutor,
    probe_fn=probe_media,
) -> dict[str, Any]:
    notes = executor.iter_notes(query=query)
    usages_by_source: dict[str, list[SoundUsage]] = {}
    for note in notes:
        for usage in find_sound_usages(note):
            usages_by_source.setdefault(usage.source_filename, []).append(usage)

    entries: list[dict[str, Any]] = []
    for source_filename in sorted(usages_by_source):
        source_path = media_dir / source_filename
        target_filename = deterministic_target_filename(source_filename)
        target_path = media_dir / target_filename
        codec_info: dict[str, Any] | None = None
        convertible = source_path.exists()
        if convertible:
            try:
                codec_info = probe_fn(source_path)
            except Exception:
                convertible = False
        usages = sorted(
            usages_by_source[source_filename],
            key=lambda item: (item.note_id, item.field_name, item.source_filename),
        )
        entries.append(
            {
                "source_filename": source_filename,
                "source_path": str(source_path),
                "source_extension": source_path.suffix.lower(),
                "target_filename": target_filename,
                "target_path": str(target_path),
                "target_exists": target_path.exists(),
                "source_exists": source_path.exists(),
                "convertible": convertible,
                "codec": codec_info,
                "usages": [
                    {
                        "note_id": usage.note_id,
                        "field_name": usage.field_name,
                        "original_field_value": usage.original_field_value,
                    }
                    for usage in usages
                ],
            },
        )

    manifest = {
        "profile": profile_name,
        "backend": backend,
        "query": query,
        "collection_path": str(collection_path),
        "media_dir": str(media_dir),
        "backup_dir": str(backup_dir),
        "target_format": {
            "container": TARGET_CONTAINER,
            "codec": TARGET_CODEC,
            "bitrate": TARGET_BITRATE,
            "sample_rate": TARGET_SAMPLE_RATE,
        },
        "generated_at": datetime.now(UTC).isoformat(),
        "entries": entries,
        "summary": {
            "note_count": len(notes),
            "referenced_source_count": len(entries),
            "convertible_count": sum(1 for entry in entries if entry["convertible"]),
            "missing_source_count": sum(1 for entry in entries if not entry["source_exists"]),
            "target_exists_count": sum(1 for entry in entries if entry["target_exists"]),
            "usage_count": sum(len(entry["usages"]) for entry in entries),
        },
    }
    manifest["manifest_hash"] = manifest_hash(manifest)
    return manifest


def write_manifest(path: Path, manifest: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return path


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _latest_native_backup(backup_dir: Path) -> Path:
    backups = sorted(
        backup_dir.glob("*.colpkg"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        raise RuntimeError(f"no native .colpkg backup found in {backup_dir}")
    return backups[0]


def create_backup_bundle(*, manifest: dict[str, Any], output_root: Path) -> Path:
    backup_dir = output_root / "backup" / manifest["manifest_hash"]
    backup_dir.mkdir(parents=True, exist_ok=True)
    native_dir = backup_dir / "native-backup"
    media_copy_dir = backup_dir / "source-media"
    native_dir.mkdir(exist_ok=True)
    media_copy_dir.mkdir(exist_ok=True)

    latest_backup = _latest_native_backup(Path(manifest["backup_dir"]))
    native_backup_copy = native_dir / latest_backup.name
    if not native_backup_copy.exists():
        shutil.copy2(latest_backup, native_backup_copy)

    manifest_copy = backup_dir / "manifest.json"
    if not manifest_copy.exists():
        manifest_copy.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    rollback_entries: list[dict[str, Any]] = []
    for entry in manifest["entries"]:
        source_path = Path(entry["source_path"])
        if source_path.exists():
            media_copy = media_copy_dir / entry["source_filename"]
            media_copy.parent.mkdir(parents=True, exist_ok=True)
            if not media_copy.exists():
                shutil.copy2(source_path, media_copy)
        for usage in entry["usages"]:
            rollback_entries.append(
                {
                    "note_id": usage["note_id"],
                    "field_name": usage["field_name"],
                    "original_field_value": usage["original_field_value"],
                    "source_filename": entry["source_filename"],
                    "replacement_filename": entry["target_filename"],
                },
            )

    rollback_map = backup_dir / "rollback-map.json"
    sorted_rollbacks = sorted(
        rollback_entries,
        key=lambda item: (
            item["note_id"],
            item["field_name"],
            item["source_filename"],
        ),
    )
    rollback_map.write_text(
        json.dumps(sorted_rollbacks, indent=2, sort_keys=True) + "\n",
    )
    return backup_dir


def _target_matches_expected(target_path: Path, probe_fn=probe_media) -> bool:
    if not target_path.exists():
        return False
    try:
        info = probe_fn(target_path)
    except Exception:
        return False
    format_name = str(info.get("format_name") or "")
    return info.get("codec_name") == TARGET_CODEC and TARGET_CONTAINER in format_name


def apply_manifest(
    *,
    manifest: dict[str, Any],
    output_root: Path,
    executor: AnkicliExecutor,
    probe_fn=probe_media,
    convert_fn=convert_to_m4a,
) -> dict[str, Any]:
    backup_bundle = create_backup_bundle(manifest=manifest, output_root=output_root)
    report = {
        "manifest_hash": manifest["manifest_hash"],
        "backup_bundle": str(backup_bundle),
        "converted_files": [],
        "updated_notes": [],
        "skipped_items": [],
        "failed_items": [],
    }

    for entry in manifest["entries"]:
        source_path = Path(entry["source_path"])
        target_path = Path(entry["target_path"])
        if not source_path.exists():
            report["skipped_items"].append(
                {
                    "source_filename": entry["source_filename"],
                    "reason": "missing_source",
                },
            )
            continue
        if not entry["convertible"]:
            report["skipped_items"].append(
                {
                    "source_filename": entry["source_filename"],
                    "reason": "non_convertible",
                },
            )
            continue
        try:
            if not _target_matches_expected(target_path, probe_fn=probe_fn):
                convert_fn(source_path=source_path, target_path=target_path)
                report["converted_files"].append(
                    {
                        "source_filename": entry["source_filename"],
                        "target_filename": entry["target_filename"],
                    },
                )
        except Exception as exc:
            report["failed_items"].append(
                {
                    "source_filename": entry["source_filename"],
                    "reason": "conversion_failed",
                    "error": str(exc),
                },
            )
            continue

        note_updates: dict[int, dict[str, str]] = {}
        for usage in entry["usages"]:
            note_updates.setdefault(int(usage["note_id"]), {})[usage["field_name"]] = (
                replace_sound_reference(
                    value=usage["original_field_value"],
                    source_filename=entry["source_filename"],
                    target_filename=entry["target_filename"],
                )
            )

        for note_id in sorted(note_updates):
            updated = executor.update_note_fields(
                note_id=note_id,
                field_updates=note_updates[note_id],
            )
            verified_note = executor.get_note(note_id)
            for field_name, expected_value in sorted(note_updates[note_id].items()):
                actual_value = verified_note["fields"][field_name]
                if actual_value != expected_value:
                    report["failed_items"].append(
                        {
                            "source_filename": entry["source_filename"],
                            "note_id": note_id,
                            "field_name": field_name,
                            "reason": "verification_failed",
                        },
                    )
                    break
            else:
                report["updated_notes"].append(
                    {
                        "note_id": note_id,
                        "fields": sorted(note_updates[note_id]),
                        "result": updated,
                    },
                )

    return report


def verify_manifest(*, manifest: dict[str, Any], executor: AnkicliExecutor) -> dict[str, Any]:
    report = {
        "manifest_hash": manifest["manifest_hash"],
        "converted_files": [],
        "updated_notes": [],
        "skipped_items": [],
        "failed_items": [],
    }
    for entry in manifest["entries"]:
        target_path = Path(entry["target_path"])
        if not target_path.exists():
            report["failed_items"].append(
                {
                    "source_filename": entry["source_filename"],
                    "reason": "missing_target",
                },
            )
            continue
        report["converted_files"].append(
            {
                "source_filename": entry["source_filename"],
                "target_filename": entry["target_filename"],
            },
        )
        note_ids = sorted({int(usage["note_id"]) for usage in entry["usages"]})
        for note_id in note_ids:
            note = executor.get_note(note_id)
            for usage in sorted(
                (usage for usage in entry["usages"] if int(usage["note_id"]) == note_id),
                key=lambda item: item["field_name"],
            ):
                field_name = usage["field_name"]
                value = note["fields"][field_name]
                expected = f"[sound:{entry['target_filename']}]"
                old_token = f"[sound:{entry['source_filename']}]"
                if expected not in value or old_token in value:
                    report["failed_items"].append(
                        {
                            "source_filename": entry["source_filename"],
                            "note_id": note_id,
                            "field_name": field_name,
                            "reason": "stale_reference",
                        },
                    )
                else:
                    report["updated_notes"].append(
                        {
                            "note_id": note_id,
                            "field_name": field_name,
                            "target_filename": entry["target_filename"],
                        },
                    )
    return report


def resolve_profile_paths(*, profile_name: str) -> dict[str, Path]:
    profile = ProfileResolver().resolve_profile(profile_name)
    return {
        "collection_path": profile.collection_path,
        "media_dir": profile.media_dir,
        "backup_dir": profile.backup_dir,
    }
