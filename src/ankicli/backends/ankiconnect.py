"""AnkiConnect backend."""

from __future__ import annotations

import base64
import http.client
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ankicli.app.catalog import (
    supported_operations_for_backend,
    supported_workflows_for_operations,
    workflow_support_for_operations,
)
from ankicli.app.credentials import SyncCredential
from ankicli.app.errors import (
    BackendOperationUnsupportedError,
    BackendUnavailableError,
    CardNotFoundError,
    DeckNotFoundError,
    MediaNotFoundError,
    ModelNotFoundError,
    NoteNotFoundError,
    TagNotFoundError,
    ValidationError,
)
from ankicli.app.models import BackendCapabilities
from ankicli.backends.base import BaseBackend


class AnkiConnectBackend(BaseBackend):
    name = "ankiconnect"
    default_api_version = 6
    _MEDIA_REFERENCE_PATTERNS = (
        re.compile(r"\[sound:([^\]\r\n]+)\]"),
        re.compile(r"""<img\b[^>]*\bsrc=["']([^"']+)["']""", re.IGNORECASE),
    )

    def __init__(self, *, url: str | None = None, version: int | None = None) -> None:
        self.url = url or os.environ.get("ANKICONNECT_URL", "http://127.0.0.1:8765")
        configured_version = version
        if configured_version is None:
            raw_version = os.environ.get("ANKICONNECT_API_VERSION", str(self.default_api_version))
            try:
                configured_version = int(raw_version)
            except ValueError:
                configured_version = self.default_api_version
        self.version = configured_version

    def supported_operations(self) -> dict[str, bool]:
        return supported_operations_for_backend(self.name, available=True)

    def _raise_unsupported(self, operation: str) -> None:
        raise BackendOperationUnsupportedError(
            f"{operation} is not supported by the ankiconnect backend",
            details={"backend": self.name, "operation": operation},
        )

    def backend_capabilities(self) -> BackendCapabilities:
        try:
            api_version = self._invoke("version")
        except BackendUnavailableError as exc:
            supported_operations = self.supported_operations()
            return BackendCapabilities(
                backend=self.name,
                available=False,
                supports_collection_reads=False,
                supports_collection_writes=False,
                supports_live_desktop=True,
                supported_operations=supported_operations,
                supported_workflows=supported_workflows_for_operations(supported_operations),
                workflow_support=workflow_support_for_operations(supported_operations),
                notes=[str(exc)],
            )

        supported_operations = self.supported_operations()
        notes = [f"AnkiConnect API version {api_version} at {self.url}"]
        notes.append("AnkiConnect supports live note, deck, tag, and media mutation flows.")
        notes.append("AnkiConnect does not expose auth, sync, backup, or orphaned-media APIs.")
        notes.append(
            "Deck and tag hierarchy actions are synthesized from name-based desktop state."
        )
        return BackendCapabilities(
            backend=self.name,
            available=True,
            supports_collection_reads=True,
            supports_collection_writes=True,
            supports_live_desktop=True,
            supported_operations=supported_operations,
            supported_workflows=supported_workflows_for_operations(supported_operations),
            workflow_support=workflow_support_for_operations(supported_operations),
            notes=notes,
        )

    def auth_status(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("auth.status")

    def login(
        self,
        collection_path: Path | None,
        *,
        username: str,
        password: str,
        endpoint: str | None,
    ) -> SyncCredential:
        del collection_path, username, password, endpoint
        self._raise_unsupported("auth.login")

    def logout(self, collection_path: Path | None) -> dict:
        del collection_path
        self._raise_unsupported("auth.logout")

    def sync_status(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("sync.status")

    def sync_run(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("sync.run")

    def sync_pull(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("sync.pull")

    def sync_push(
        self,
        collection_path: Path | None,
        *,
        credential: SyncCredential | None,
    ) -> dict:
        del collection_path, credential
        self._raise_unsupported("sync.push")

    def create_backup(
        self,
        collection_path: Path,
        *,
        backup_folder: Path,
        force: bool,
    ) -> dict:
        del collection_path, backup_folder, force
        self._raise_unsupported("backup.create")

    def restore_backup(
        self,
        collection_path: Path,
        *,
        backup_path: Path,
        media_folder: Path,
        media_db_path: Path,
    ) -> dict:
        del collection_path, backup_path, media_folder, media_db_path
        self._raise_unsupported("backup.restore")

    def _invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        payload = json.dumps(
            {
                "action": action,
                "version": self.version,
                "params": params or {},
            },
        ).encode()
        parsed = urlsplit(self.url)
        if parsed.scheme != "http" or not parsed.hostname:
            raise BackendUnavailableError(
                f"AnkiConnect backend URL is invalid: {self.url}",
                details={"url": self.url},
            )
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        try:
            connection = http.client.HTTPConnection(
                parsed.hostname,
                parsed.port or 80,
                timeout=5,
            )
            connection.request(
                "POST",
                path,
                body=payload,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            raw = response.read().decode()
        except OSError as exc:
            raise BackendUnavailableError(
                f"AnkiConnect backend is unavailable at {self.url}",
                details={"url": self.url, "reason": str(exc)},
            ) from exc
        finally:
            try:
                connection.close()
            except Exception:
                pass

        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BackendUnavailableError(
                "AnkiConnect returned invalid JSON",
                details={"url": self.url},
            ) from exc

        if decoded.get("error"):
            raise ValidationError(
                str(decoded["error"]),
                details={"action": action, "url": self.url},
            )
        return decoded.get("result")

    def _model_names(self) -> list[dict]:
        try:
            result = self._invoke("modelNamesAndIds")
        except ValidationError:
            names = self._invoke("modelNames")
            return [{"id": None, "name": str(name)} for name in names]
        return [{"id": int(model_id), "name": name} for name, model_id in result.items()]

    def _deck_items(self) -> list[dict]:
        result = self._invoke("deckNamesAndIds")
        return [
            {"id": int(deck_id), "name": name}
            for name, deck_id in sorted(result.items(), key=lambda item: item[0])
        ]

    def _deck_name_to_id(self) -> dict[str, int]:
        return {item["name"]: int(item["id"]) for item in self._deck_items()}

    def _media_dir(self) -> Path:
        return Path(str(self._invoke("getMediaDirPath"))).expanduser().resolve()

    def _normalize_media_item(self, media_dir: Path, media_name: str) -> dict:
        candidate = (media_dir / media_name).resolve()
        try:
            candidate.relative_to(media_dir)
        except ValueError as exc:
            raise ValidationError(
                f'Invalid media name "{media_name}"',
                details={"name": media_name},
            ) from exc
        size = candidate.stat().st_size if candidate.exists() and candidate.is_file() else None
        return {
            "name": media_name,
            "path": str(candidate),
            "size": size,
        }

    def _resolve_media_candidate(self, media_dir: Path, name: str) -> Path:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValidationError("--name must not be empty")
        candidate = (media_dir / normalized_name).resolve()
        try:
            candidate.relative_to(media_dir)
        except ValueError as exc:
            raise ValidationError(
                f'Invalid media name "{name}"',
                details={"name": name},
            ) from exc
        if not candidate.exists() or not candidate.is_file():
            raise MediaNotFoundError(
                f'Media file "{name}" was not found',
                details={"name": name, "media_dir": str(media_dir)},
            )
        return candidate

    def _note_infos(self, note_ids: list[int]) -> list[dict]:
        if not note_ids:
            return []
        return list(self._invoke("notesInfo", {"notes": [int(note_id) for note_id in note_ids]}))

    def _all_note_infos(self) -> list[dict]:
        note_ids = [int(note_id) for note_id in self._invoke("findNotes", {"query": ""})]
        return self._note_infos(note_ids)

    def _all_card_ids(self) -> list[int]:
        return [int(card_id) for card_id in self._invoke("findCards", {"query": ""})]

    def _cards_by_deck(self) -> dict[str, list[int]]:
        card_ids = self._all_card_ids()
        if not card_ids:
            return {}
        deck_map = self._invoke("getDecks", {"cards": card_ids})
        return {
            str(deck_name): [int(card_id) for card_id in ids]
            for deck_name, ids in deck_map.items()
        }

    def _deck_subtree(self, source_name: str) -> list[dict]:
        decks = self._deck_items()
        matching = [
            deck
            for deck in decks
            if deck["name"] == source_name or deck["name"].startswith(f"{source_name}::")
        ]
        if not matching:
            raise DeckNotFoundError(
                f'Deck "{source_name}" was not found',
                details={"deck_name": source_name},
            )
        return sorted(matching, key=lambda item: item["name"])

    def _target_deck_name(self, source_name: str, current_name: str, new_name: str) -> str:
        suffix = current_name[len(source_name) :]
        return f"{new_name}{suffix}"

    def _rename_deck_tree(
        self,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
        action: str,
        new_parent: str | None = None,
    ) -> dict:
        subtree = self._deck_subtree(name)
        subtree_names = {deck["name"] for deck in subtree}
        deck_id = next(int(deck["id"]) for deck in subtree if deck["name"] == name)
        mapping = {
            old_name: self._target_deck_name(name, old_name, new_name)
            for old_name in subtree_names
        }
        existing_names = set(self._deck_name_to_id())
        conflicts = sorted(
            target_name
            for target_name in mapping.values()
            if target_name in existing_names and target_name not in subtree_names
        )
        if conflicts:
            raise ValidationError(
                f'Deck target "{conflicts[0]}" already exists',
                details={"deck_name": name, "new_name": new_name, "conflict": conflicts[0]},
            )

        descendant_count = len(subtree_names) - 1
        cards_by_deck = self._cards_by_deck()
        affected_card_count = sum(
            len(cards_by_deck.get(deck_name, [])) for deck_name in subtree_names
        )

        if not dry_run:
            for target_name in sorted(
                set(mapping.values()), key=lambda item: (item.count("::"), item)
            ):
                if target_name not in existing_names:
                    self._invoke("createDeck", {"deck": target_name})
            for old_name, target_name in sorted(mapping.items(), key=lambda item: item[0]):
                card_ids = cards_by_deck.get(old_name, [])
                if card_ids:
                    self._invoke("changeDeck", {"cards": card_ids, "deck": target_name})
            for old_name in sorted(subtree_names, key=lambda item: (-item.count("::"), item)):
                self._invoke("deleteDecks", {"decks": [old_name], "cardsToo": True})

        payload = {
            "id": deck_id,
            "name": name,
            "new_name": new_name,
            "action": action,
            "dry_run": dry_run,
            "descendant_count": descendant_count,
            "card_count": affected_card_count,
        }
        if new_parent is not None:
            payload["new_parent"] = new_parent
        return payload

    def _extract_media_references(self, field_value: Any) -> set[str]:
        references: set[str] = set()
        text = str(field_value or "")
        for pattern in self._MEDIA_REFERENCE_PATTERNS:
            for match in pattern.findall(text):
                normalized = str(match).strip()
                if normalized:
                    references.add(normalized)
        return references

    def _referenced_media_names(self) -> set[str]:
        references: set[str] = set()
        for note in self._all_note_infos():
            for field in note.get("fields", {}).values():
                references.update(self._extract_media_references(field.get("value", "")))
        return references

    def _available_tags_map(self) -> dict[str, str]:
        return {tag.lower(): tag for tag in self.list_tags(Path("."))}

    def _require_existing_tags(self, tags: list[str]) -> list[str]:
        available = self._available_tags_map()
        normalized: list[str] = []
        for tag in tags:
            actual = available.get(tag.lower())
            if actual is None:
                raise TagNotFoundError(f'Tag "{tag}" was not found', details={"tag": tag})
            normalized.append(actual)
        return normalized

    def _ensure_non_overlapping_roots(self, names: list[str], *, detail_key: str) -> None:
        sorted_names = sorted(set(names))
        for index, left in enumerate(sorted_names):
            for right in sorted_names[index + 1 :]:
                if right == left or right.startswith(f"{left}::"):
                    raise ValidationError(
                        "Overlapping hierarchical targets are not supported",
                        details={detail_key: sorted_names},
                    )

    def _tag_tree(self, root: str) -> list[str]:
        available = self.list_tags(Path("."))
        matching = [tag for tag in available if tag == root or tag.startswith(f"{root}::")]
        if not matching:
            raise TagNotFoundError(f'Tag "{root}" was not found', details={"tag": root})
        return sorted(matching)

    def _rename_tag_tree(
        self,
        *,
        roots: list[str],
        rename_root: str | None = None,
        new_parent: str | None = None,
        dry_run: bool,
        action: str,
    ) -> dict:
        canonical_roots = self._require_existing_tags(roots)
        self._ensure_non_overlapping_roots(canonical_roots, detail_key="tags")
        available = self.list_tags(Path("."))
        source_tags: set[str] = set()
        mapping: dict[str, str] = {}

        for root in canonical_roots:
            subtree = self._tag_tree(root)
            source_tags.update(subtree)
            if rename_root is not None:
                for tag in subtree:
                    suffix = tag[len(root) :]
                    mapping[tag] = f"{rename_root}{suffix}"
            else:
                for tag in subtree:
                    leaf = tag.split("::")[-1]
                    suffix = tag[len(root) :].split("::")[1:] if tag != root else []
                    base = f"{new_parent}::{leaf}" if new_parent else leaf
                    mapping[tag] = "::".join([base, *suffix]) if suffix else base

        for source, target in mapping.items():
            if source == target:
                raise ValidationError(
                    "Tag reparent target must change the tag name",
                    details={"tag": source, "target": target},
                )

        conflicts = sorted(
            target
            for target in mapping.values()
            if target in available and target not in source_tags
        )
        if conflicts:
            raise ValidationError(
                f'Tag target "{conflicts[0]}" already exists',
                details={"conflict": conflicts[0], "tags": canonical_roots},
            )

        notes = self._all_note_infos()
        affected_note_ids = sorted(
            {
                int(note.get("noteId"))
                for note in notes
                if any(tag in mapping for tag in note.get("tags", []))
            },
        )

        if not dry_run:
            for source, target in sorted(mapping.items()):
                self._invoke(
                    "replaceTagsInAllNotes",
                    {"tag_to_replace": source, "replace_with_tag": target},
                )

        payload = {
            "action": action,
            "dry_run": dry_run,
            "affected_tag_count": len(mapping),
            "affected_note_count": len(affected_note_ids),
        }
        if rename_root is not None and len(canonical_roots) == 1:
            payload["name"] = canonical_roots[0]
            payload["new_name"] = rename_root
        else:
            payload["tags"] = canonical_roots
            payload["new_parent"] = new_parent or ""
        return payload

    def _model_field_names(self, name: str) -> list[str]:
        return [str(field) for field in self._invoke("modelFieldNames", {"modelName": name})]

    def get_collection_info(self, collection_path: Path) -> dict:
        del collection_path
        decks = self._deck_items()
        models = self._model_names()
        note_ids = self._invoke("findNotes", {"query": ""})
        card_ids = self._invoke("findCards", {"query": ""})
        return {
            "collection_path": None,
            "collection_name": "AnkiConnect",
            "exists": True,
            "backend_available": True,
            "note_count": len(note_ids),
            "card_count": len(card_ids),
            "deck_count": len(decks),
            "model_count": len(models),
            "ankiconnect_url": self.url,
            "ankiconnect_version": self._invoke("version"),
        }

    def list_decks(self, collection_path: Path) -> list[dict]:
        del collection_path
        return self._deck_items()

    def get_deck(self, collection_path: Path, *, name: str) -> dict:
        del collection_path
        for deck in self._deck_items():
            if deck["name"] == name:
                return deck
        raise DeckNotFoundError(f'Deck "{name}" was not found', details={"deck_name": name})

    def create_deck(self, collection_path: Path, *, name: str, dry_run: bool) -> dict:
        del collection_path
        if name in self._deck_name_to_id():
            raise ValidationError(
                f'Deck "{name}" already exists',
                details={"deck_name": name},
            )
        created_id = None
        if not dry_run:
            created_id = self._invoke("createDeck", {"deck": name})
        return {
            "id": int(created_id) if created_id is not None else None,
            "name": name,
            "action": "create",
            "dry_run": dry_run,
        }

    def rename_deck(
        self,
        collection_path: Path,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
    ) -> dict:
        del collection_path
        return self._rename_deck_tree(
            name=name,
            new_name=new_name,
            dry_run=dry_run,
            action="rename",
        )

    def delete_deck(self, collection_path: Path, *, name: str, dry_run: bool) -> dict:
        del collection_path
        subtree = self._deck_subtree(name)
        deck_id = next(int(deck["id"]) for deck in subtree if deck["name"] == name)
        subtree_names = {deck["name"] for deck in subtree}
        cards_by_deck = self._cards_by_deck()
        card_count = sum(len(cards_by_deck.get(deck_name, [])) for deck_name in subtree_names)
        if not dry_run:
            if card_count:
                raise ValidationError(
                    "AnkiConnect can only delete empty decks without deleting cards",
                    details={"deck_name": name, "card_count": card_count},
                )
            for deck_name in sorted(subtree_names, key=lambda item: (-item.count("::"), item)):
                self._invoke("deleteDecks", {"decks": [deck_name], "cardsToo": True})
        payload = {
            "id": int(deck_id),
            "name": name,
            "action": "delete",
            "dry_run": dry_run,
            "descendant_count": len(subtree_names) - 1,
            "card_count": card_count,
        }
        return payload

    def reparent_deck(
        self,
        collection_path: Path,
        *,
        name: str,
        new_parent: str,
        dry_run: bool,
    ) -> dict:
        del collection_path
        if new_parent:
            self.get_deck(Path("."), name=new_parent)
            if new_parent == name or new_parent.startswith(f"{name}::"):
                raise ValidationError(
                    "Deck reparent target must not be the source deck or its descendant",
                    details={"deck_name": name, "new_parent": new_parent},
                )
            target_name = f"{new_parent}::{name.split('::')[-1]}"
        else:
            target_name = name.split("::")[-1]
        return self._rename_deck_tree(
            name=name,
            new_name=target_name,
            dry_run=dry_run,
            action="reparent",
            new_parent=new_parent,
        )

    def list_models(self, collection_path: Path) -> list[dict]:
        del collection_path
        return self._model_names()

    def get_model(self, collection_path: Path, *, name: str) -> dict:
        del collection_path
        for model in self._model_names():
            if model["name"] == name:
                fields = self._model_field_names(name)
                return {
                    "id": model["id"],
                    "name": name,
                    "fields": fields,
                }
        raise ModelNotFoundError(f'Model "{name}" was not found', details={"model_name": name})

    def get_model_fields(self, collection_path: Path, *, name: str) -> dict:
        del collection_path
        for model in self._model_names():
            if model["name"] == name:
                return {
                    "id": model["id"],
                    "name": name,
                    "fields": self._model_field_names(name),
                }
        raise ModelNotFoundError(f'Model "{name}" was not found', details={"model_name": name})

    def get_model_templates(self, collection_path: Path, *, name: str) -> dict:
        del collection_path
        for model in self._model_names():
            if model["name"] == name:
                templates = self._invoke("modelTemplates", {"modelName": name})
                normalized = [{"name": str(template_name)} for template_name in templates.keys()]
                return {
                    "id": model["id"],
                    "name": name,
                    "templates": normalized,
                }
        raise ModelNotFoundError(f'Model "{name}" was not found', details={"model_name": name})

    def list_media(self, collection_path: Path) -> list[dict]:
        del collection_path
        media_dir = self._media_dir()
        names = [str(name) for name in self._invoke("getMediaFilesNames")]
        return [self._normalize_media_item(media_dir, name) for name in names]

    def check_media(self, collection_path: Path) -> dict:
        del collection_path
        media_dir = self._media_dir()
        names = [str(name) for name in self._invoke("getMediaFilesNames")]
        referenced = self._referenced_media_names()
        file_names = set(names)
        orphaned = sorted(file_names - referenced)
        missing = sorted(referenced - file_names)
        warnings = []
        if orphaned or missing:
            warnings.append("AnkiConnect media check is name-based and uses note field references.")
        return {
            "media_dir": str(media_dir),
            "exists": media_dir.exists(),
            "file_count": len(names),
            "referenced_count": len(referenced),
            "orphaned_count": len(orphaned),
            "missing_count": len(missing),
            "warnings": warnings,
        }

    def list_orphaned_media(self, collection_path: Path) -> list[dict]:
        del collection_path
        self._raise_unsupported("media.orphaned")

    def attach_media(
        self,
        collection_path: Path,
        *,
        source_path: Path,
        name: str | None,
        dry_run: bool,
    ) -> dict:
        del collection_path
        resolved_source_path = source_path.expanduser().resolve()
        if not resolved_source_path.exists() or not resolved_source_path.is_file():
            raise MediaNotFoundError(
                f"Source media path does not exist: {resolved_source_path}",
                details={"path": str(resolved_source_path)},
            )
        target_name = (name or resolved_source_path.name).strip()
        if not target_name:
            raise ValidationError("--name must not be empty")
        if Path(target_name).name != target_name:
            raise ValidationError(
                f'Invalid media name "{target_name}"',
                details={"name": target_name},
            )
        if not dry_run:
            self._invoke(
                "storeMediaFile",
                {
                    "filename": target_name,
                    "data": base64.b64encode(resolved_source_path.read_bytes()).decode(),
                },
            )
        return {
            "name": target_name,
            "source_path": str(resolved_source_path),
            "path": None,
            "size": resolved_source_path.stat().st_size,
            "action": "attach",
            "dry_run": dry_run,
        }

    def resolve_media_path(self, collection_path: Path, *, name: str) -> dict:
        del collection_path
        media_dir = self._media_dir()
        candidate = self._resolve_media_candidate(media_dir, name)
        return self._normalize_media_item(media_dir, candidate.relative_to(media_dir).as_posix())

    def list_tags(self, collection_path: Path) -> list[str]:
        del collection_path
        return [str(tag) for tag in self._invoke("getTags")]

    def rename_tag(
        self,
        collection_path: Path,
        *,
        name: str,
        new_name: str,
        dry_run: bool,
    ) -> dict:
        del collection_path
        return self._rename_tag_tree(
            roots=[name],
            rename_root=new_name,
            dry_run=dry_run,
            action="rename",
        )

    def delete_tags(
        self,
        collection_path: Path,
        *,
        tags: list[str],
        dry_run: bool,
    ) -> dict:
        del collection_path
        canonical_tags = self._require_existing_tags(tags)
        notes = self._all_note_infos()
        affected_note_ids = sorted(
            {
                int(note.get("noteId"))
                for note in notes
                if any(tag in canonical_tags for tag in note.get("tags", []))
            },
        )
        if not dry_run and affected_note_ids:
            self._invoke(
                "removeTags",
                {"notes": affected_note_ids, "tags": " ".join(canonical_tags)},
            )
        return {
            "tags": list(canonical_tags),
            "action": "delete",
            "dry_run": dry_run,
            "affected_note_count": len(affected_note_ids),
        }

    def reparent_tags(
        self,
        collection_path: Path,
        *,
        tags: list[str],
        new_parent: str,
        dry_run: bool,
    ) -> dict:
        del collection_path
        return self._rename_tag_tree(
            roots=tags,
            new_parent=new_parent,
            dry_run=dry_run,
            action="reparent",
        )

    def find_notes(
        self,
        collection_path: Path,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> dict:
        del collection_path
        note_ids = [int(note_id) for note_id in self._invoke("findNotes", {"query": query})]
        sliced_ids = note_ids[offset : offset + limit]
        return {
            "items": [{"id": note_id} for note_id in sliced_ids],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": len(note_ids),
        }

    def find_cards(
        self,
        collection_path: Path,
        query: str,
        *,
        limit: int,
        offset: int,
    ) -> dict:
        del collection_path
        card_ids = [int(card_id) for card_id in self._invoke("findCards", {"query": query})]
        sliced_ids = card_ids[offset : offset + limit]
        return {
            "items": [{"id": card_id} for card_id in sliced_ids],
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": len(card_ids),
        }

    def get_note(self, collection_path: Path, note_id: int) -> dict:
        del collection_path
        notes = self._invoke("notesInfo", {"notes": [note_id]})
        if not notes:
            raise NoteNotFoundError(f"Note {note_id} was not found", details={"note_id": note_id})
        note = notes[0]
        fields = {
            str(name): str(value.get("value", ""))
            for name, value in note.get("fields", {}).items()
        }
        return {
            "id": int(note.get("noteId", note_id)),
            "model": str(note.get("modelName", "")),
            "fields": fields,
            "tags": [str(tag) for tag in note.get("tags", [])],
        }

    def get_note_fields(self, collection_path: Path, note_id: int) -> dict:
        note = self.get_note(collection_path, note_id)
        return {
            "id": note["id"],
            "model": note["model"],
            "fields": note["fields"],
        }

    def get_card(self, collection_path: Path, card_id: int) -> dict:
        del collection_path
        cards = self._invoke("cardsInfo", {"cards": [card_id]})
        if not cards:
            raise CardNotFoundError(f"Card {card_id} was not found", details={"card_id": card_id})
        card = cards[0]
        deck_id = self._deck_name_to_id().get(str(card.get("deckName", "")))
        template = card.get("template")
        if template is None and card.get("fieldOrder") is not None:
            template = f"Card {int(card['fieldOrder']) + 1}"
        return {
            "id": int(card.get("cardId", card_id)),
            "note_id": int(card.get("note")) if card.get("note") is not None else None,
            "deck_id": deck_id,
            "template": str(template or ""),
        }

    def get_card_presentation(self, collection_path: Path, card_id: int) -> dict | None:
        del collection_path, card_id
        return None

    def add_note(
        self,
        collection_path: Path,
        *,
        deck_name: str,
        model_name: str,
        fields: dict[str, str],
        tags: list[str],
        dry_run: bool,
    ) -> dict:
        del collection_path
        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "tags": tags,
        }
        if dry_run:
            can_add = self._invoke("canAddNotes", {"notes": [note]})
            if not can_add or not can_add[0]:
                raise ValidationError(
                    "AnkiConnect rejected the candidate note for add",
                    details={"deck": deck_name, "model": model_name},
                )
            note_id = None
        else:
            note_id = self._invoke("addNote", {"note": note})
            if note_id is None:
                raise ValidationError(
                    "AnkiConnect failed to add the note",
                    details={"deck": deck_name, "model": model_name},
                )
        return {
            "id": int(note_id) if note_id is not None else None,
            "deck": deck_name,
            "model": model_name,
            "fields": fields,
            "tags": tags,
            "dry_run": dry_run,
        }

    def update_note(
        self,
        collection_path: Path,
        *,
        note_id: int,
        fields: dict[str, str],
        dry_run: bool,
    ) -> dict:
        del collection_path
        existing = self.get_note(Path("."), note_id)
        if not dry_run:
            self._invoke("updateNoteFields", {"note": {"id": note_id, "fields": fields}})
        return {
            "id": note_id,
            "model": existing["model"],
            "fields": dict(fields),
            "tags": existing["tags"],
            "dry_run": dry_run,
        }

    def delete_note(
        self,
        collection_path: Path,
        *,
        note_id: int,
        dry_run: bool,
    ) -> dict:
        del collection_path
        self.get_note(Path("."), note_id)
        if not dry_run:
            self._invoke("deleteNotes", {"notes": [int(note_id)]})
        return {
            "id": int(note_id),
            "deleted": not dry_run,
            "dry_run": dry_run,
        }

    def move_note_to_deck(
        self,
        collection_path: Path,
        *,
        note_id: int,
        deck_name: str,
        dry_run: bool,
    ) -> dict:
        del collection_path
        note = self.get_note(Path("."), note_id)
        card_ids = [
            int(card_id)
            for card_id in self._invoke("findCards", {"query": f"nid:{note_id}"})
        ]
        deck_id = self._deck_name_to_id().get(deck_name)
        if deck_id is None:
            raise DeckNotFoundError(
                f'Deck "{deck_name}" was not found',
                details={"deck_name": deck_name},
            )
        if not dry_run:
            self._invoke("changeDeck", {"cards": card_ids, "deck": deck_name})
        return {
            "id": int(note["id"]),
            "deck": deck_name,
            "card_ids": card_ids,
            "action": "move_deck",
            "dry_run": dry_run,
        }

    def add_tags_to_notes(
        self,
        collection_path: Path,
        *,
        note_ids: list[int],
        tags: list[str],
        dry_run: bool,
    ) -> list[dict]:
        del collection_path
        normalized_ids = [int(note_id) for note_id in note_ids]
        for note_id in normalized_ids:
            self.get_note(Path("."), note_id)
        if not dry_run:
            self._invoke("addTags", {"notes": normalized_ids, "tags": " ".join(tags)})
        return [
            {"id": note_id, "tags": list(tags), "action": "add", "dry_run": dry_run}
            for note_id in normalized_ids
        ]

    def remove_tags_from_notes(
        self,
        collection_path: Path,
        *,
        note_ids: list[int],
        tags: list[str],
        dry_run: bool,
    ) -> list[dict]:
        del collection_path
        normalized_ids = [int(note_id) for note_id in note_ids]
        for note_id in normalized_ids:
            self.get_note(Path("."), note_id)
        if not dry_run:
            self._invoke("removeTags", {"notes": normalized_ids, "tags": " ".join(tags)})
        return [
            {"id": note_id, "tags": list(tags), "action": "remove", "dry_run": dry_run}
            for note_id in normalized_ids
        ]

    def suspend_cards(
        self,
        collection_path: Path,
        *,
        card_ids: list[int],
        dry_run: bool,
    ) -> list[dict]:
        del collection_path
        normalized_ids = [int(card_id) for card_id in card_ids]
        for card_id in normalized_ids:
            self.get_card(Path("."), card_id)
        if not dry_run:
            self._invoke("suspend", {"cards": normalized_ids})
        return [
            {"id": card_id, "suspended": True, "dry_run": dry_run}
            for card_id in normalized_ids
        ]

    def unsuspend_cards(
        self,
        collection_path: Path,
        *,
        card_ids: list[int],
        dry_run: bool,
    ) -> list[dict]:
        del collection_path
        normalized_ids = [int(card_id) for card_id in card_ids]
        for card_id in normalized_ids:
            self.get_card(Path("."), card_id)
        if not dry_run:
            self._invoke("unsuspend", {"cards": normalized_ids})
        return [
            {"id": card_id, "suspended": False, "dry_run": dry_run}
            for card_id in normalized_ids
        ]
