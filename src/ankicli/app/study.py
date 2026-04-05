"""Study-session domain helpers."""

from __future__ import annotations

import os
import re
import uuid
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ankicli.app.errors import (
    StudySessionNotFoundError,
    StudySessionRequiredError,
    ValidationError,
)
from ankicli.app.services import _resolve_collection_arg
from ankicli.backends.base import BaseBackend

GRADE_VALUES = ("again", "hard", "good", "easy")
STUDY_SCOPE_PRESETS = ("due", "new", "all", "custom")
STUDY_SESSION_SCHEMA_VERSION = "2026-03-27.1"
STUDY_BACKEND_MODE_LOCAL = "local-only"
SOUND_RE = re.compile(r"\[sound:([^\]\r\n]+)\]")
ANKI_PLAY_RE = re.compile(r"\[anki:play:([qa]):(\d+)\]")
IMAGE_RE = re.compile(r"""<img\b[^>]*\bsrc=["']([^"']+)["']""", re.IGNORECASE)
ASSET_ATTR_RE = re.compile(
    r"""(?P<prefix>\b(?:src|href)=["'])(?P<value>[^"']+)(?P<suffix>["'])""",
    re.IGNORECASE,
)
CSS_URL_RE = re.compile(r"""url\((?P<quote>['"]?)(?P<value>[^)'"]+)(?P=quote)\)""", re.IGNORECASE)
MEDIA_REFERENCE_UNRESOLVED = "MEDIA_REFERENCE_UNRESOLVED"
MEDIA_FILE_MISSING = "MEDIA_FILE_MISSING"
MEDIA_PROVIDER_UNCONFIGURED = "MEDIA_PROVIDER_UNCONFIGURED"
MEDIA_PROVIDER_QUOTA_EXCEEDED = "MEDIA_PROVIDER_QUOTA_EXCEEDED"
MEDIA_INPUT_INVALID = "MEDIA_INPUT_INVALID"
PREVIEW_DEFAULT_HEIGHT = 420
MEDIA_KIND_CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
    "aac": "audio/aac",
    "mp4": "video/mp4",
    "webm": "video/webm",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "svg": "image/svg+xml",
    "webp": "image/webp",
}


class StudyGrade(BaseModel):
    card_id: int
    rating: str


class StudyCard(BaseModel):
    card_id: int
    note_id: int | None = None
    deck_id: int | None = None
    template: str = ""
    model: str = ""
    tags: list[str] = Field(default_factory=list)
    field_order: list[str] = Field(default_factory=list)
    prompt_fields: list[str] = Field(default_factory=list)
    answer_fields: list[str] = Field(default_factory=list)
    prompt: str = ""
    answer: str = ""
    fields: dict[str, str] = Field(default_factory=dict)
    raw_fields: dict[str, str] = Field(default_factory=dict)
    study_view: dict[str, object] = Field(default_factory=dict)
    media: dict[str, list[dict[str, object]]] = Field(
        default_factory=lambda: {"audio": [], "images": []}
    )


class StudyScope(BaseModel):
    preset: Literal["due", "new", "all", "custom"] = "all"
    deck: str | None = None
    query: str = ""
    limit: int = 20
    total_available: int = 0


class StudySession(BaseModel):
    schema_version: str = STUDY_SESSION_SCHEMA_VERSION
    id: str
    backend: str
    backend_mode: str = STUDY_BACKEND_MODE_LOCAL
    writes_back_to_anki: bool = False
    collection_path: str
    scope: StudyScope
    cards: list[StudyCard] = Field(default_factory=list)
    current_index: int = 0
    revealed: bool = False
    grades: list[StudyGrade] = Field(default_factory=list)
    status: str = "active"


class StudyStore(BaseModel):
    schema_version: str = STUDY_SESSION_SCHEMA_VERSION
    active_session_id: str | None = None
    sessions: dict[str, StudySession] = Field(default_factory=dict)


class _PresentationTextExtractor(HTMLParser):
    _BLOCK_TAGS = {"br", "div", "p", "li", "tr", "table", "section", "article", "ul", "ol"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self._BLOCK_TAGS:
            self._parts.append("\n")
        if tag.lower() != "img":
            return
        alt = next((value for key, value in attrs if key.lower() == "alt" and value), None)
        if alt:
            self._parts.append(alt)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def text(self) -> str:
        combined = "".join(self._parts)
        combined = SOUND_RE.sub(" ", combined)
        combined = combined.replace("\xa0", " ")
        combined = re.sub(r"\s*\n\s*", "\n", combined)
        combined = re.sub(r"[^\S\n]+", " ", combined)
        combined = re.sub(r"\n{3,}", "\n\n", combined)
        return unescape(combined).strip()


class _TelegramHtmlProjector(HTMLParser):
    _BLOCK_TAGS = {"div", "p", "li", "tr", "table", "section", "article", "ul", "ol", "blockquote"}
    _SPOILER_CLASS_RE = re.compile(r"(^|[\s_-])(spoiler|tg-spoiler)([\s_-]|$)", re.IGNORECASE)
    _SUPPORTED_INLINE_TAGS = {
        "b": "b",
        "strong": "b",
        "i": "i",
        "em": "i",
        "u": "u",
        "ins": "u",
        "s": "s",
        "strike": "s",
        "del": "s",
        "code": "code",
        "pre": "pre",
        "tg-spoiler": "tg-spoiler",
        "blockquote": "blockquote",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._stack: list[str | None] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style"}:
            self._skip_depth += 1
            self._stack.append(None)
            return
        if self._skip_depth:
            self._stack.append(None)
            return
        if lowered == "br":
            self._parts.append("\n")
            self._stack.append(None)
            return
        if lowered in self._BLOCK_TAGS:
            self._append_newline()
        if lowered == "img":
            alt = next((value for key, value in attrs if key.lower() == "alt" and value), None)
            if alt:
                self._parts.append(escape(alt, quote=False))
            self._stack.append(None)
            return
        if lowered == "a":
            href = next((value for key, value in attrs if key.lower() == "href" and value), None)
            if href:
                self._parts.append(f'<a href="{escape(href, quote=True)}">')
                self._stack.append("a")
            else:
                self._stack.append(None)
            return
        spoiler = self._spoiler_tag(attrs)
        if spoiler is not None:
            self._parts.append(f"<{spoiler}>")
            self._stack.append(spoiler)
            return
        mapped = self._SUPPORTED_INLINE_TAGS.get(lowered)
        if mapped is not None:
            self._parts.append(f"<{mapped}>")
            self._stack.append(mapped)
            return
        self._stack.append(None)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        mapped = self._stack.pop() if self._stack else None
        if lowered in {"script", "style"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if mapped:
            self._parts.append(f"</{mapped}>")
        if lowered in self._BLOCK_TAGS:
            self._append_newline()

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data:
            return
        self._parts.append(escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if self._skip_depth:
            return
        self._parts.append(escape(unescape(f"&{name};"), quote=False))

    def handle_charref(self, name: str) -> None:
        if self._skip_depth:
            return
        prefix = "&#x" if name.lower().startswith("x") else "&#"
        suffix = ";" if not name.endswith(";") else ""
        self._parts.append(escape(unescape(f"{prefix}{name}{suffix}"), quote=False))

    def text(self) -> str:
        combined = "".join(self._parts)
        combined = combined.replace("\xa0", " ")
        combined = re.sub(r"[ \t\r\f\v]+", " ", combined)
        combined = re.sub(r" *\n *", "\n", combined)
        combined = re.sub(r"\n{3,}", "\n\n", combined)
        combined = re.sub(
            r"(<(b|i|u|s|code|pre|tg-spoiler|blockquote|a)(?: [^>]*)?>)\s+", r"\1", combined
        )
        combined = re.sub(r"\s+(</(b|i|u|s|code|pre|tg-spoiler|blockquote|a)>)", r"\1", combined)
        return combined.strip()

    def _append_newline(self) -> None:
        if not self._parts or self._parts[-1].endswith("\n"):
            return
        self._parts.append("\n")

    def _spoiler_tag(self, attrs: list[tuple[str, str | None]]) -> str | None:
        for key, value in attrs:
            if key.lower() != "class" or not value:
                continue
            if self._SPOILER_CLASS_RE.search(value):
                return "tg-spoiler"
        return None


class StudyService:
    """Local tutor-session state layered over backend reads."""

    def __init__(self, backend: BaseBackend) -> None:
        self.backend = backend

    def start(
        self,
        collection_path: str | None,
        *,
        deck: str | None,
        query: str | None,
        scope_preset: str,
        limit: int,
    ) -> dict:
        if limit < 1:
            raise ValidationError("--limit must be at least 1")
        if scope_preset not in STUDY_SCOPE_PRESETS:
            raise ValidationError(
                f"--scope-preset must be one of: {', '.join(STUDY_SCOPE_PRESETS)}"
            )
        if scope_preset != "custom" and query:
            raise ValidationError("--query may only be used with --scope-preset custom")
        if scope_preset == "custom" and not query and not deck:
            raise ValidationError(
                "study start with --scope-preset custom requires --query or --deck"
            )
        resolved = _resolve_collection_arg(
            self.backend,
            collection_path,
            command_name="study start",
        )
        scoped_query = self._scoped_query(deck=deck, query=query, scope_preset=scope_preset)
        result = self.backend.find_cards(resolved, scoped_query, limit=limit, offset=0)
        cards = [self._build_study_card(resolved, int(item["id"])) for item in result["items"]]
        session = StudySession(
            id=uuid.uuid4().hex,
            backend=self.backend.name,
            collection_path=str(resolved),
            scope=StudyScope(
                preset=scope_preset,
                deck=deck,
                query=scoped_query,
                limit=limit,
                total_available=result["total"],
            ),
            cards=cards,
            status="completed" if not cards else "active",
        )
        store = self._load_store()
        store.sessions[session.id] = session
        store.active_session_id = session.id
        self._save_store(store)
        return {
            "session": self._session_payload(session),
            "current_card": self._current_card_payload(session, include_answer=False),
        }

    def next(self, *, session_id: str | None) -> dict:
        session, store = self._get_session(session_id)
        self._save_store(store)
        return {
            "session": self._session_payload(session),
            "current_card": self._current_card_payload(session, include_answer=False),
        }

    def details(self, *, session_id: str | None) -> dict:
        session, store = self._get_session(session_id)
        self._save_store(store)
        return {
            "session": self._session_payload(session),
            "current_card": self._current_card_payload(session, include_answer=False),
        }

    def reveal(self, *, session_id: str | None) -> dict:
        session, store = self._get_session(session_id)
        current = self._current_card(session)
        if current is None:
            return {
                "session": self._session_payload(session),
                "current_card": None,
            }
        session.revealed = True
        self._save_store(store)
        return {
            "session": self._session_payload(session),
            "current_card": self._card_payload(current, session, include_answer=True),
        }

    def grade(self, *, session_id: str | None, rating: str) -> dict:
        if rating not in GRADE_VALUES:
            raise ValidationError(f"--rating must be one of: {', '.join(GRADE_VALUES)}")
        session, store = self._get_session(session_id)
        current = self._current_card(session)
        if current is None:
            raise StudySessionRequiredError("No current study card is available to grade")
        if not session.revealed:
            raise ValidationError("study grade requires reveal first")
        session.grades.append(StudyGrade(card_id=current.card_id, rating=rating))
        graded = self._card_payload(current, session, include_answer=True)
        session.current_index += 1
        session.revealed = False
        if session.current_index >= len(session.cards):
            session.status = "completed"
        self._save_store(store)
        return {
            "session": self._session_payload(session),
            "graded_card": {
                **graded,
                "rating": rating,
            },
            "next_card": self._current_card_payload(session, include_answer=False),
        }

    def summary(self, *, session_id: str | None) -> dict:
        session, store = self._get_session(session_id)
        current = self._current_card_payload(session, include_answer=False)
        self._save_store(store)
        return {
            "session": self._session_payload(session),
            "current_card": current,
        }

    def _get_session(self, session_id: str | None) -> tuple[StudySession, StudyStore]:
        store = self._load_store()
        resolved_session_id = session_id or store.active_session_id
        if not resolved_session_id:
            raise StudySessionRequiredError("No active study session exists")
        session = store.sessions.get(resolved_session_id)
        if session is None:
            raise StudySessionNotFoundError(
                f"Study session {resolved_session_id} was not found",
                details={"session_id": resolved_session_id},
            )
        store.active_session_id = resolved_session_id
        return session, store

    def _build_study_card(self, collection_path: Path, card_id: int) -> StudyCard:
        card = self.backend.get_card(collection_path, card_id)
        note_id = card.get("note_id")
        note = (
            self.backend.get_note(collection_path, int(note_id))
            if note_id is not None
            else {
                "model": "",
                "fields": {},
                "tags": [],
            }
        )
        fields = dict(note.get("fields", {}))
        field_order = self._field_order(collection_path, str(note.get("model", "")), fields)
        prompt_fields = field_order[:1]
        answer_fields = field_order[1:]
        prompt = self._join_field_values(fields, prompt_fields, compact=True)
        answer = self._join_field_values(fields, answer_fields, compact=False)
        media = self._extract_media(collection_path, fields)
        presentation = self._card_presentation(collection_path, card_id)
        study_view = self._build_study_view(
            fields,
            prompt_fields,
            answer_fields,
            presentation=presentation,
        )
        return StudyCard(
            card_id=card_id,
            note_id=int(note_id) if note_id is not None else None,
            deck_id=card.get("deck_id"),
            template=str(card.get("template", "")),
            model=str(note.get("model", "")),
            tags=[str(tag) for tag in note.get("tags", [])],
            field_order=field_order,
            prompt_fields=prompt_fields,
            answer_fields=answer_fields,
            prompt=prompt,
            answer=answer,
            fields={str(name): str(value) for name, value in fields.items()},
            raw_fields={str(name): str(value) for name, value in fields.items()},
            study_view=study_view,
            media=media,
        )

    def _field_order(
        self,
        collection_path: Path,
        model_name: str,
        fields: dict[str, str],
    ) -> list[str]:
        if model_name:
            try:
                model_fields = self.backend.get_model_fields(collection_path, name=model_name)
            except Exception:
                model_fields = None
            if isinstance(model_fields, dict):
                ordered = [str(name) for name in model_fields.get("fields", []) if name in fields]
                if ordered:
                    remainder = [name for name in fields if name not in ordered]
                    return [*ordered, *remainder]
        return list(fields)

    def _current_card(self, session: StudySession) -> StudyCard | None:
        if session.current_index >= len(session.cards):
            return None
        return session.cards[session.current_index]

    def _current_card_payload(self, session: StudySession, *, include_answer: bool) -> dict | None:
        current = self._current_card(session)
        if current is None:
            return None
        return self._card_payload(current, session, include_answer=include_answer)

    def _card_payload(
        self,
        card: StudyCard,
        session: StudySession,
        *,
        include_answer: bool,
    ) -> dict:
        misses = [grade.rating for grade in session.grades if grade.card_id == card.card_id]
        collection_path = Path(session.collection_path)
        preview_spec = self._openclaw_preview(
            card,
            include_answer=include_answer,
            collection_path=collection_path,
        )
        payload = {
            "card_id": card.card_id,
            "note_id": card.note_id,
            "deck_id": card.deck_id,
            "template": card.template,
            "model": card.model,
            "tags": card.tags,
            "prompt": card.prompt,
            "revealed": include_answer or session.revealed,
            "position": min(session.current_index + 1, len(session.cards)),
            "remaining": max(len(session.cards) - session.current_index - 1, 0),
            "miss_history": misses,
            "miss_count": sum(1 for rating in misses if rating == "again"),
            "study_view": {
                **card.study_view,
                "answer": card.study_view.get("answer") if include_answer else None,
                "back_card_text": card.study_view.get("back_card_text") if include_answer else None,
                "rendered_back_html": (
                    card.study_view.get("rendered_back_html") if include_answer else None
                ),
                "rendered_back_telegram_html": (
                    card.study_view.get("rendered_back_telegram_html") if include_answer else None
                ),
            },
            "media": card.media,
            "preview_spec": preview_spec,
            "study_media_spec": self._study_media_spec(
                card,
                include_answer=include_answer,
                collection_path=collection_path,
                preview_spec=preview_spec,
            ),
            "tutoring_summary": self._tutoring_summary(
                card,
                include_answer=include_answer,
                preview_spec=preview_spec,
            ),
            "raw_fields": card.raw_fields,
        }
        if include_answer:
            payload["answer"] = card.answer
        return payload

    def _session_payload(self, session: StudySession) -> dict:
        grade_counts = {rating: 0 for rating in GRADE_VALUES}
        missed_cards: dict[int, int] = {}
        for grade in session.grades:
            grade_counts[grade.rating] = grade_counts.get(grade.rating, 0) + 1
            if grade.rating == "again":
                missed_cards[grade.card_id] = missed_cards.get(grade.card_id, 0) + 1
        weak_cards = [
            {
                "card_id": card.card_id,
                "prompt": card.prompt,
                "miss_count": missed_cards[card.card_id],
            }
            for card in session.cards
            if card.card_id in missed_cards
        ]
        weak_cards.sort(key=lambda item: (-item["miss_count"], item["card_id"]))
        recommendations = self._recommendations(session, weak_cards)
        return {
            "schema_version": session.schema_version,
            "id": session.id,
            "backend": session.backend,
            "backend_mode": session.backend_mode,
            "writes_back_to_anki": session.writes_back_to_anki,
            "collection_path": session.collection_path,
            "scope": session.scope.model_dump(),
            "status": session.status,
            "card_count": len(session.cards),
            "queue_summary": {
                "total": len(session.cards),
                "completed": len(session.grades),
                "remaining": max(len(session.cards) - session.current_index, 0),
            },
            "current_index": min(session.current_index, len(session.cards)),
            "revealed": session.revealed,
            "completed_count": len(session.grades),
            "remaining_count": max(len(session.cards) - session.current_index, 0),
            "grade_counts": grade_counts,
            "weak_cards": weak_cards[:5],
            "recommendations": recommendations,
        }

    def _recommendations(
        self,
        session: StudySession,
        weak_cards: list[dict[str, str | int]],
    ) -> list[str]:
        recommendations: list[str] = []
        if not session.cards:
            recommendations.append("No cards matched the selected scope; broaden deck or query.")
            return recommendations
        if weak_cards:
            recommendations.append("Review weak cards again before changing deck scope.")
        if session.scope.preset != "custom" and session.scope.deck:
            recommendations.append(
                "Continue studying deck "
                f"{session.scope.deck} with a narrower preset if it feels too broad."
            )
        if session.status == "completed":
            recommendations.append("Session is complete; start a new scope or review weak cards.")
        return recommendations

    def _scoped_query(
        self,
        *,
        deck: str | None,
        query: str | None,
        scope_preset: str,
    ) -> str:
        parts: list[str] = []
        if deck:
            parts.append(f'deck:"{deck}"')
        if scope_preset == "due":
            parts.append("is:due")
        elif scope_preset == "new":
            parts.append("is:new")
        elif scope_preset == "custom" and query:
            parts.append(query)
        elif scope_preset == "all" and query:
            parts.append(query)
        return " ".join(part for part in parts if part).strip()

    def _load_store(self) -> StudyStore:
        path = self._store_path()
        if not path.exists():
            return StudyStore()
        store = StudyStore.model_validate_json(path.read_text())
        if not getattr(store, "schema_version", None):
            store.schema_version = STUDY_SESSION_SCHEMA_VERSION
        return store

    def _save_store(self, store: StudyStore) -> None:
        path = self._store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(store.model_dump_json(indent=2))

    def _store_path(self) -> Path:
        root = os.environ.get("ANKICLI_STATE_DIR")
        if root:
            return Path(root).expanduser().resolve() / "study-sessions.json"
        return Path.home() / ".ankicli" / "state" / "study-sessions.json"

    def _join_field_values(
        self,
        fields: dict[str, str],
        names: list[str],
        *,
        compact: bool,
    ) -> str:
        values = [(name, fields.get(name, "").strip()) for name in names]
        non_empty = [(name, value) for name, value in values if value]
        if not non_empty:
            return ""
        if compact and len(non_empty) == 1:
            return non_empty[0][1]
        if not compact and len(non_empty) == 1:
            return non_empty[0][1]
        return "\n".join(f"{name}: {value}" for name, value in non_empty)

    def _extract_media(
        self,
        collection_path: Path,
        fields: dict[str, str],
    ) -> dict[str, list[dict[str, object]]]:
        media_root = collection_path.with_name("collection.media")
        audio: list[dict[str, object]] = []
        images: list[dict[str, object]] = []
        for value in fields.values():
            for filename in SOUND_RE.findall(value):
                audio.append(
                    self._resolve_media_entry(
                        media_root,
                        tag=f"[sound:{filename}]",
                        filename=filename,
                        kind="audio",
                    )
                )
            for filename in IMAGE_RE.findall(value):
                images.append(
                    self._resolve_media_entry(
                        media_root,
                        tag=filename,
                        filename=filename,
                        kind="images",
                    )
                )
        return {
            "audio": audio,
            "images": images,
        }

    def _resolve_media_entry(
        self,
        media_root: Path,
        *,
        tag: str,
        filename: str,
        kind: str,
    ) -> dict[str, object]:
        logical_path = f"collection.media/{filename}" if filename.strip() else None
        candidate = media_root / filename
        if not filename.strip():
            return {
                "tag": tag,
                "filename": filename,
                "logical_path": logical_path,
                "path": None,
                "exists": False,
                "error_code": MEDIA_INPUT_INVALID,
                "kind": kind,
            }
        if not media_root.exists():
            return {
                "tag": tag,
                "filename": filename,
                "logical_path": logical_path,
                "path": str(candidate),
                "exists": False,
                "error_code": MEDIA_REFERENCE_UNRESOLVED,
                "kind": kind,
            }
        return {
            "tag": tag,
            "filename": filename,
            "logical_path": logical_path,
            "path": str(candidate),
            "exists": candidate.exists(),
            "error_code": None if candidate.exists() else MEDIA_FILE_MISSING,
            "kind": kind,
        }

    def _build_study_view(
        self,
        fields: dict[str, str],
        prompt_fields: list[str],
        answer_fields: list[str],
        *,
        presentation: dict[str, str | None] | None,
    ) -> dict[str, object]:
        ordered_names = list(fields)
        prompt = self._join_field_values(fields, prompt_fields, compact=True)
        answer = self._join_field_values(fields, answer_fields, compact=False)
        rendered_front_html = presentation.get("front_html") if presentation else None
        rendered_back_html = presentation.get("back_html") if presentation else None
        front_source = rendered_front_html or prompt
        back_source = rendered_back_html or answer
        preferred_support = [
            "reading",
            "furigana",
            "meaning",
            "english",
            "example",
            "sentence",
        ]
        supporting: list[dict[str, str]] = []
        used = set(prompt_fields)
        lower_name_map = {name.lower(): name for name in ordered_names}
        for key in preferred_support:
            matched = next((name for lname, name in lower_name_map.items() if key in lname), None)
            if matched and matched not in used and fields.get(matched, "").strip():
                supporting.append({"field": matched, "value": fields[matched]})
                used.add(matched)
        for name in ordered_names:
            if name in used:
                continue
            value = fields.get(name, "").strip()
            if value:
                supporting.append({"field": name, "value": value})
        return {
            "prompt": prompt,
            "answer": answer,
            "rendered_front_html": self._optional_text(rendered_front_html),
            "rendered_back_html": self._optional_text(rendered_back_html),
            "rendered_front_telegram_html": self._telegram_html(rendered_front_html),
            "rendered_back_telegram_html": self._telegram_html(rendered_back_html),
            "front_card_text": self._presentation_text(front_source),
            "back_card_text": self._presentation_text(back_source),
            "supporting": supporting[:6],
            "raw_fields_available": True,
        }

    def _card_presentation(
        self, collection_path: Path, card_id: int
    ) -> dict[str, str | None] | None:
        provider = getattr(self.backend, "get_card_presentation", None)
        if provider is None:
            return None
        result = provider(collection_path, card_id)
        if not isinstance(result, dict):
            return None
        return {
            "front_html": self._optional_text(result.get("front_html")),
            "back_html": self._optional_text(result.get("back_html")),
        }

    def _presentation_text(self, source: str | None) -> str | None:
        normalized = self._optional_text(source)
        if normalized is None:
            return None
        parser = _PresentationTextExtractor()
        parser.feed(normalized)
        parser.close()
        text = parser.text()
        return text or None

    def _telegram_html(self, source: str | None) -> str | None:
        normalized = self._optional_text(source)
        if normalized is None:
            return None
        parser = _TelegramHtmlProjector()
        parser.feed(normalized)
        parser.close()
        projected = parser.text()
        return projected or None

    def _optional_text(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _openclaw_preview(
        self,
        card: StudyCard,
        *,
        include_answer: bool,
        collection_path: Path,
    ) -> dict[str, object]:
        study_view = card.study_view if isinstance(card.study_view, dict) else {}
        front_source = self._optional_text(
            study_view.get("rendered_front_html")
        ) or self._text_preview_html(study_view.get("prompt") or card.prompt)
        back_source = (
            self._optional_text(study_view.get("rendered_back_html"))
            or self._text_preview_html(study_view.get("answer") or card.answer)
            if include_answer
            else None
        )
        assets, degraded, asset_ref_map = self._openclaw_preview_assets(
            collection_path,
            card.media,
            [front_source, back_source],
        )
        question_audio_entries = self._ordered_audio_entries_for_fields(
            card.prompt_fields,
            card.fields,
            card.media,
        )
        answer_audio_entries = self._ordered_audio_entries_for_fields(
            card.answer_fields,
            card.fields,
            card.media,
        )
        fallback_audio_entries = self._ordered_audio_entries_for_fields(
            card.field_order or list(card.fields),
            card.fields,
            card.media,
        )
        front_html = self._openclaw_preview_fragment(
            self._rewrite_preview_html(
                front_source,
                card.media,
                degraded,
                asset_ref_map=asset_ref_map,
                question_audio_entries=question_audio_entries,
                answer_audio_entries=answer_audio_entries,
                fallback_audio_entries=fallback_audio_entries,
            )
        )
        back_html = (
            self._openclaw_preview_fragment(
                self._rewrite_preview_html(
                    back_source,
                    card.media,
                    degraded,
                    asset_ref_map=asset_ref_map,
                    question_audio_entries=question_audio_entries,
                    answer_audio_entries=answer_audio_entries,
                    fallback_audio_entries=fallback_audio_entries,
                )
            )
            if back_source
            else None
        )
        preview: dict[str, object] = {
            "kind": "anki_card_preview",
            "title": card.template or "Anki card preview",
            "preferredHeight": PREVIEW_DEFAULT_HEIGHT,
            "front": front_html,
            "revealState": "answer_revealed" if include_answer else "prompt_only",
            "assets": assets,
        }
        if back_html:
            preview["back"] = back_html
        if degraded:
            preview["degraded"] = degraded
        return preview

    def _tutoring_summary(
        self,
        card: StudyCard,
        *,
        include_answer: bool,
        preview_spec: dict[str, object],
    ) -> dict[str, object]:
        study_view = card.study_view if isinstance(card.study_view, dict) else {}
        raw_supporting = study_view.get("supporting")
        supporting = raw_supporting if isinstance(raw_supporting, list) else []

        def supporting_value(keywords: tuple[str, ...]) -> str | None:
            for entry in supporting:
                if not isinstance(entry, dict):
                    continue
                field_name = self._optional_text(entry.get("field"))
                if not field_name:
                    continue
                normalized = field_name.lower()
                if any(keyword in normalized for keyword in keywords):
                    return self._presentation_text(entry.get("value"))
            return None

        degraded_entries = preview_spec.get("degraded") if isinstance(preview_spec, dict) else None
        degraded = degraded_entries if isinstance(degraded_entries, list) else []
        front = (
            self._optional_text(preview_spec.get("front"))
            if isinstance(preview_spec, dict)
            else None
        )
        back = (
            self._optional_text(preview_spec.get("back"))
            if isinstance(preview_spec, dict)
            else None
        )
        summary: dict[str, object] = {
            "template": card.template,
            "prompt": self._presentation_text(
                study_view.get("rendered_front_html") or study_view.get("prompt") or card.prompt
            ),
            "reveal_state": "answer_revealed" if include_answer else "front_only",
            "media": {
                "audio_slots": self._count_preview_audio_slots(front, back),
                "images": len(card.media.get("images", [])),
                "degraded": [
                    self._optional_text(entry.get("errorCode"))
                    for entry in degraded
                    if isinstance(entry, dict) and self._optional_text(entry.get("errorCode"))
                ],
            },
        }
        reading = supporting_value(("reading", "furigana"))
        meaning = supporting_value(("meaning", "english", "gloss"))
        sentence = supporting_value(("sentence", "example"))
        if reading:
            summary["reading"] = reading
        if meaning:
            summary["meaning"] = meaning
        if sentence:
            summary["sentence"] = sentence
        if card.tags:
            summary["tags"] = card.tags
        if include_answer:
            answer = self._presentation_text(
                study_view.get("rendered_back_html") or study_view.get("answer") or card.answer
            )
            if answer:
                summary["answer"] = answer
        return summary

    def _study_media_spec(
        self,
        card: StudyCard,
        *,
        include_answer: bool,
        collection_path: Path,
        preview_spec: dict[str, object],
    ) -> dict[str, object]:
        assets_entries = preview_spec.get("assets") if isinstance(preview_spec, dict) else None
        asset_entries = assets_entries if isinstance(assets_entries, list) else []
        asset_index: dict[str, dict[str, object]] = {}
        for asset in asset_entries:
            if not isinstance(asset, dict):
                continue
            logical_path = self._optional_text(asset.get("logicalPath"))
            if not logical_path:
                continue
            asset_index[logical_path] = asset

        question_audio_entries = self._ordered_audio_entries_for_fields(
            card.prompt_fields,
            card.fields,
            card.media,
        )
        fallback_audio_entries = self._ordered_audio_entries_for_fields(
            card.field_order or list(card.fields),
            card.fields,
            card.media,
        )
        answer_audio_entries = (
            self._ordered_audio_entries_for_fields(
                card.answer_fields,
                card.fields,
                card.media,
            )
            if include_answer
            else []
        )
        media_root = collection_path.with_name("collection.media")
        image_specs: list[dict[str, object]] = []
        for index, entry in enumerate(card.media.get("images", []), start=1):
            logical_path = self._optional_text(entry.get("logical_path"))
            if not logical_path:
                continue
            image_specs.append(
                {
                    "role": "image",
                    "label": self._study_media_label("image", entry.get("field_name"), index),
                    "logicalPath": logical_path,
                    "contentType": self._content_type_for_path(logical_path),
                }
            )

        degraded_entries = preview_spec.get("degraded") if isinstance(preview_spec, dict) else None
        degraded = degraded_entries if isinstance(degraded_entries, list) else []
        return {
            "audio": self._study_audio_specs(
                "prompt_audio",
                question_audio_entries or fallback_audio_entries,
                asset_index,
            ),
            "answer_audio": self._study_audio_specs(
                "answer_audio",
                answer_audio_entries,
                asset_index,
            ),
            "images": image_specs,
            "degraded": [
                entry
                for entry in degraded
                if isinstance(entry, dict)
                and self._optional_text(entry.get("errorCode"))
                and self._optional_text(entry.get("logicalPath"))
            ],
            "mediaRoot": str(media_root),
        }

    def _study_audio_specs(
        self,
        role: str,
        entries: list[dict[str, object]],
        asset_index: dict[str, dict[str, object]],
    ) -> list[dict[str, object]]:
        specs: list[dict[str, object]] = []
        seen: set[str] = set()
        for index, entry in enumerate(entries, start=1):
            logical_path = self._optional_text(entry.get("logical_path"))
            if not logical_path or logical_path in seen:
                continue
            seen.add(logical_path)
            asset = asset_index.get(logical_path, {})
            field_name = self._optional_text(entry.get("field_name"))
            specs.append(
                {
                    "role": role,
                    "label": self._study_media_label(role, field_name, index),
                    "logicalPath": logical_path,
                    "contentType": self._optional_text(asset.get("contentType"))
                    or self._content_type_for_path(logical_path),
                    "field": field_name,
                }
            )
        return specs

    def _study_media_label(self, role: str, field_name: object, index: int) -> str:
        normalized_field = self._optional_text(field_name)
        if normalized_field:
            return f"{normalized_field} ({index})"
        if role == "prompt_audio":
            return f"Prompt audio {index}"
        if role == "answer_audio":
            return f"Answer audio {index}"
        if role == "image":
            return f"Image {index}"
        return f"Media {index}"

    def _openclaw_preview_assets(
        self,
        collection_path: Path,
        media: dict[str, list[dict[str, object]]],
        html_sources: list[str | None],
    ) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, str]]:
        assets: list[dict[str, object]] = []
        degraded: list[dict[str, object]] = []
        asset_ref_map: dict[str, str] = {}
        seen = set()
        degraded_seen = set()

        def append_entry(entry: dict[str, object], *, refs: list[str]) -> None:
            logical_path = self._optional_text(entry.get("logical_path"))
            source_path = self._optional_text(entry.get("path"))
            exists = entry.get("exists") is True
            if exists and logical_path and source_path:
                if logical_path not in seen:
                    seen.add(logical_path)
                    assets.append(
                        {
                            "logicalPath": logical_path,
                            "sourcePath": source_path,
                            "contentType": self._content_type_for_path(logical_path),
                        }
                    )
                for ref in refs:
                    if ref:
                        asset_ref_map[ref] = logical_path
                return
            error_code = self._optional_text(entry.get("error_code"))
            if logical_path and error_code:
                degraded_key = (
                    logical_path,
                    error_code,
                    self._optional_text(entry.get("tag")) or "",
                )
                if degraded_key in degraded_seen:
                    return
                degraded_seen.add(degraded_key)
                degraded.append(
                    {
                        "logicalPath": logical_path,
                        "kind": self._optional_text(entry.get("kind")) or "media",
                        "errorCode": error_code,
                        "tag": self._optional_text(entry.get("tag")) or logical_path,
                    }
                )

        for entries in media.values():
            for entry in entries:
                append_entry(
                    entry,
                    refs=[
                        self._optional_text(entry.get("tag")) or "",
                        self._optional_text(entry.get("filename")) or "",
                    ],
                )

        media_root = collection_path.with_name("collection.media")
        for html_source in html_sources:
            for ref in self._preview_local_asset_refs(html_source):
                append_entry(
                    self._resolve_media_entry(
                        media_root,
                        tag=ref,
                        filename=ref,
                        kind="asset",
                    ),
                    refs=[ref],
                )
        return assets, degraded, asset_ref_map

    def _rewrite_preview_html(
        self,
        html_source: str | None,
        media: dict[str, list[dict[str, object]]],
        degraded: list[dict[str, object]],
        *,
        asset_ref_map: dict[str, str],
        question_audio_entries: list[dict[str, object]],
        answer_audio_entries: list[dict[str, object]],
        fallback_audio_entries: list[dict[str, object]],
    ) -> str:
        del degraded
        source = self._optional_text(html_source) or ""
        audio_by_tag = {
            str(entry.get("tag")): entry for entry in media.get("audio", []) if entry.get("tag")
        }
        image_by_filename = {
            str(entry.get("filename")): entry
            for entry in media.get("images", [])
            if entry.get("filename")
        }

        def replace_audio(match: re.Match[str]) -> str:
            filename = match.group(1)
            tag = f"[sound:{filename}]"
            return self._render_audio_entry(audio_by_tag.get(tag), fallback_tag=tag)

        def replace_anki_play(match: re.Match[str]) -> str:
            side = match.group(1)
            index = int(match.group(2))
            audio_entries = question_audio_entries if side == "q" else answer_audio_entries
            entry = audio_entries[index] if 0 <= index < len(audio_entries) else None
            if entry is None and 0 <= index < len(fallback_audio_entries):
                entry = fallback_audio_entries[index]
            return self._render_audio_entry(entry, fallback_tag=f"[anki:play:{side}:{index}]")

        def replace_image(match: re.Match[str]) -> str:
            filename = match.group(1)
            entry = image_by_filename.get(filename)
            if not entry or entry.get("exists") is not True:
                error_code = (
                    self._optional_text(entry.get("error_code"))
                    if entry
                    else MEDIA_REFERENCE_UNRESOLVED
                )
                return (
                    '<div class="oc-missing-media" data-kind="image">'
                    f"Image unavailable ({escape(error_code or MEDIA_REFERENCE_UNRESOLVED)})"
                    "</div>"
                )
            logical_path = (
                self._optional_text(entry.get("logical_path")) or f"collection.media/{filename}"
            )
            return f'<img src="{escape(logical_path, quote=True)}" alt="" class="oc-image" />'

        def replace_asset_attr(match: re.Match[str]) -> str:
            logical_path = self._logical_preview_asset_path(match.group("value"), asset_ref_map)
            if not logical_path:
                return match.group(0)
            return (
                f"{match.group('prefix')}{escape(logical_path, quote=True)}{match.group('suffix')}"
            )

        def replace_css_url(match: re.Match[str]) -> str:
            logical_path = self._logical_preview_asset_path(match.group("value"), asset_ref_map)
            if not logical_path:
                return match.group(0)
            quote = match.group("quote") or ""
            return f"url({quote}{escape(logical_path, quote=True)}{quote})"

        rewritten = SOUND_RE.sub(replace_audio, source)
        rewritten = ANKI_PLAY_RE.sub(replace_anki_play, rewritten)
        rewritten = IMAGE_RE.sub(replace_image, rewritten)
        rewritten = ASSET_ATTR_RE.sub(replace_asset_attr, rewritten)
        rewritten = CSS_URL_RE.sub(replace_css_url, rewritten)
        return rewritten

    def _openclaw_preview_fragment(self, body_html: str) -> str:
        return f"""<style>
  .oc-preview-root {{
    background: #f8fafc;
    color: #0f172a;
    font: 16px/1.5 system-ui, sans-serif;
    padding: 16px;
    box-sizing: border-box;
  }}
  .oc-preview-root .oc-text-block {{
    white-space: pre-wrap;
  }}
  .oc-preview-root .oc-audio {{
    width: 100%;
    margin: 12px 0;
  }}
  .oc-preview-root .oc-image {{
    max-width: 100%;
    height: auto;
  }}
  .oc-preview-root .oc-missing-media {{
    padding: 10px 12px;
    margin: 12px 0;
    border: 1px solid #fecaca;
    border-radius: 10px;
    background: #fff1f2;
    color: #b91c1c;
  }}
  .oc-preview-root .oc-missing-media__tag {{
    margin-top: 4px;
    font: 12px/1.4 ui-monospace, monospace;
    opacity: 0.8;
  }}
</style>
<div class="oc-preview-root">{body_html}</div>
"""

    def _count_preview_audio_slots(self, *html_values: str | None) -> int:
        count = 0
        for html_value in html_values:
            if not html_value:
                continue
            count += len(re.findall(r"<audio\\b", html_value, flags=re.IGNORECASE))
        return count

    def _ordered_audio_entries_for_fields(
        self,
        field_names: list[str],
        fields: dict[str, str],
        media: dict[str, list[dict[str, object]]],
    ) -> list[dict[str, object]]:
        entries_by_tag: dict[str, list[dict[str, object]]] = {}
        for entry in media.get("audio", []):
            tag = self._optional_text(entry.get("tag"))
            if not tag:
                continue
            entries_by_tag.setdefault(tag, []).append(entry)
        ordered: list[dict[str, object]] = []
        for field_name in field_names:
            value = fields.get(field_name, "")
            for filename in SOUND_RE.findall(value):
                tag = f"[sound:{filename}]"
                pool = entries_by_tag.get(tag) or []
                if pool:
                    ordered.append({**pool.pop(0), "field_name": field_name})
                    continue
                ordered.append(
                    {
                        "tag": tag,
                        "filename": filename,
                        "logical_path": f"collection.media/{filename}",
                        "exists": False,
                        "error_code": MEDIA_REFERENCE_UNRESOLVED,
                        "kind": "audio",
                        "field_name": field_name,
                    }
                )
        return ordered

    def _render_audio_entry(
        self,
        entry: dict[str, object] | None,
        *,
        fallback_tag: str,
    ) -> str:
        if not entry or entry.get("exists") is not True:
            error_code = (
                self._optional_text(entry.get("error_code"))
                if entry
                else MEDIA_REFERENCE_UNRESOLVED
            )
            return (
                '<div class="oc-missing-media" data-kind="audio">'
                f"Audio unavailable ({escape(error_code or MEDIA_REFERENCE_UNRESOLVED)})"
                f'<div class="oc-missing-media__tag">{escape(fallback_tag)}</div>'
                "</div>"
            )
        logical_path = self._optional_text(entry.get("logical_path")) or "collection.media/audio"
        content_type = self._content_type_for_path(logical_path)
        return (
            '<audio controls preload="metadata" class="oc-audio">'
            f'<source src="{escape(logical_path, quote=True)}" '
            f'type="{escape(content_type, quote=True)}" />'
            "</audio>"
        )

    def _preview_local_asset_refs(self, html_source: str | None) -> list[str]:
        source = self._optional_text(html_source) or ""
        refs: list[str] = []
        for match in ASSET_ATTR_RE.finditer(source):
            value = self._normalized_preview_asset_ref(match.group("value"))
            if value:
                refs.append(value)
        for match in CSS_URL_RE.finditer(source):
            value = self._normalized_preview_asset_ref(match.group("value"))
            if value:
                refs.append(value)
        return refs

    def _logical_preview_asset_path(
        self,
        asset_ref: str,
        asset_ref_map: dict[str, str],
    ) -> str | None:
        normalized = self._normalized_preview_asset_ref(asset_ref)
        if normalized is None:
            return None
        return asset_ref_map.get(normalized)

    def _normalized_preview_asset_ref(self, asset_ref: str | None) -> str | None:
        value = self._optional_text(unescape(asset_ref or ""))
        if value is None:
            return None
        if value.startswith(("http://", "https://", "data:", "javascript:", "mailto:", "#", "/")):
            return None
        if "://" in value:
            return None
        normalized = value.split("#", 1)[0].split("?", 1)[0].strip()
        if not normalized or normalized in {".", ".."}:
            return None
        return normalized

    def _text_preview_html(self, value: object) -> str:
        text = self._optional_text(value)
        if text is None:
            return '<div class="oc-text-block"></div>'
        escaped = escape(text).replace("\n", "<br />")
        return f'<div class="oc-text-block">{escaped}</div>'

    def _content_type_for_path(self, value: str) -> str:
        suffix = Path(value).suffix.lower().lstrip(".")
        return MEDIA_KIND_CONTENT_TYPES.get(suffix, "application/octet-stream")
