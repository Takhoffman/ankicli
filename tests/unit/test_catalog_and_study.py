from __future__ import annotations

import json
from pathlib import Path

import pytest

from ankicli.app.catalog import supported_operations_for_backend, supported_workflows_for_operations
from ankicli.app.study import StudyService
from tests.proof import proves

EXPECTED_ANSWER = 'Reading: hola\nBack: hello\nExample: <img src="hola.png">example sentence'
EXPECTED_BACK_CARD_TEXT = "Reading: hola\nBack: hello\nExample: example sentence"


class _StudyBackend:
    name = "python-anki"

    def find_cards(self, collection_path: Path, query: str, *, limit: int, offset: int) -> dict:
        del collection_path
        items = [{"id": 201}, {"id": 202}]
        sliced = items[offset : offset + limit]
        return {
            "items": sliced,
            "query": query,
            "limit": limit,
            "offset": offset,
            "total": len(items),
        }

    def get_card(self, collection_path: Path, card_id: int) -> dict:
        del collection_path
        mapping = {
            201: {"id": 201, "note_id": 101, "deck_id": 55, "template": "Card 1"},
            202: {"id": 202, "note_id": 102, "deck_id": 55, "template": "Card 1"},
        }
        return mapping[card_id]

    def get_note(self, collection_path: Path, note_id: int) -> dict:
        del collection_path
        mapping = {
            101: {
                "id": 101,
                "model": "Basic",
                "fields": {
                    "Front": "hola [sound:hola.mp3]",
                    "Reading": "hola",
                    "Back": "hello",
                    "Example": '<img src="hola.png">example sentence',
                },
                "tags": ["spanish"],
            },
            102: {
                "id": 102,
                "model": "Basic",
                "fields": {"Front": "adios", "Back": "goodbye"},
                "tags": ["spanish"],
            },
        }
        return mapping[note_id]

    def get_model_fields(self, collection_path: Path, *, name: str) -> dict:
        del collection_path, name
        return {"fields": ["Front", "Reading", "Back", "Example"]}

    def get_card_presentation(self, collection_path: Path, card_id: int) -> dict | None:
        del collection_path
        mapping = {
            201: {
                "front_html": "<div>hola [sound:hola.mp3]</div>",
                "back_html": (
                    "<div>Reading: hola</div><div>Back: hello</div>"
                    '<div>Example: <img src="hola.png">example sentence</div>'
                ),
            },
            202: None,
        }
        return mapping[card_id]


@pytest.mark.unit
@proves("backend.capabilities", "unit")
def test_catalog_derives_backend_operations_and_workflows() -> None:
    ankiconnect_ops = supported_operations_for_backend("ankiconnect", available=True)
    workflows = supported_workflows_for_operations(ankiconnect_ops)

    assert ankiconnect_ops["note.add"] is True
    assert ankiconnect_ops["note.delete"] is True
    assert workflows["study.start"] is True
    assert workflows["collection.status"] is True
    assert workflows["study.grade.backend"] is False


@pytest.mark.unit
@proves("study.start", "unit")
def test_study_service_tracks_local_session_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    media_root = tmp_path / "collection.media"
    media_root.mkdir()
    (media_root / "hola.mp3").write_text("audio")
    monkeypatch.setenv("ANKICLI_STATE_DIR", str(state_dir))
    service = StudyService(_StudyBackend())

    started = service.start(
        str(collection_path),
        deck="Spanish",
        query="is:due",
        scope_preset="custom",
        limit=2,
    )

    session_id = started["session"]["id"]
    assert started["session"]["schema_version"]
    assert started["session"]["card_count"] == 2
    assert started["session"]["scope"]["query"] == 'deck:"Spanish" is:due'
    assert started["session"]["scope"]["preset"] == "custom"
    assert started["session"]["backend_mode"] == "local-only"
    assert started["session"]["writes_back_to_anki"] is False
    assert started["current_card"]["prompt"] == "hola [sound:hola.mp3]"
    assert started["current_card"]["study_view"]["prompt"] == "hola [sound:hola.mp3]"
    assert started["current_card"]["study_view"]["answer"] is None
    assert (
        started["current_card"]["study_view"]["rendered_front_html"]
        == "<div>hola [sound:hola.mp3]</div>"
    )
    assert started["current_card"]["study_view"]["rendered_back_html"] is None
    assert (
        started["current_card"]["study_view"]["rendered_front_telegram_html"]
        == "hola [sound:hola.mp3]"
    )
    assert started["current_card"]["study_view"]["rendered_back_telegram_html"] is None
    assert started["current_card"]["study_view"]["front_card_text"] == "hola"
    assert started["current_card"]["study_view"]["back_card_text"] is None
    assert started["current_card"]["study_view"]["raw_fields_available"] is True
    assert started["current_card"]["preview_spec"]["kind"] == "anki_card_preview"
    assert started["current_card"]["preview_spec"]["revealState"] == "prompt_only"
    assert "back" not in started["current_card"]["preview_spec"]
    assert '<div class="oc-preview-root">' in started["current_card"]["preview_spec"]["front"]
    assert started["current_card"]["preview_spec"]["assets"][0]["logicalPath"] == (
        "collection.media/hola.mp3"
    )
    assert started["current_card"]["study_media_spec"]["audio"][0]["logicalPath"] == (
        "collection.media/hola.mp3"
    )
    assert started["current_card"]["study_media_spec"]["audio"][0]["role"] == "prompt_audio"
    assert started["current_card"]["study_media_spec"]["images"][0]["logicalPath"] == (
        "collection.media/hola.png"
    )
    assert started["current_card"]["tutoring_summary"]["template"] == "Card 1"
    assert started["current_card"]["tutoring_summary"]["prompt"] == "hola"
    assert started["current_card"]["tutoring_summary"]["reveal_state"] == "front_only"
    assert started["current_card"]["media"]["audio"][0]["tag"] == "[sound:hola.mp3]"
    assert started["current_card"]["media"]["audio"][0]["path"] == str(media_root / "hola.mp3")
    assert started["current_card"]["media"]["audio"][0]["exists"] is True
    assert started["current_card"]["media"]["images"][0]["error_code"] == "MEDIA_FILE_MISSING"
    assert started["current_card"]["raw_fields"]["Back"] == "hello"
    assert "answer" not in started["current_card"]

    next_card = service.next(session_id=session_id)
    assert next_card["current_card"]["card_id"] == 201
    assert next_card["current_card"]["revealed"] is False

    details = service.details(session_id=session_id)
    assert details["current_card"]["revealed"] is False
    assert details["current_card"]["tutoring_summary"]["reveal_state"] == "front_only"
    assert details["current_card"]["study_view"]["answer"] is None
    assert details["current_card"]["study_view"]["rendered_back_html"] is None
    assert details["current_card"]["preview_spec"]["revealState"] == "prompt_only"
    assert "answer" not in details["current_card"]

    revealed = service.reveal(session_id=session_id)
    assert revealed["current_card"]["revealed"] is True
    assert revealed["current_card"]["answer"] == EXPECTED_ANSWER
    assert revealed["current_card"]["study_view"]["answer"] == EXPECTED_ANSWER
    assert (
        revealed["current_card"]["study_view"]["rendered_front_html"]
        == "<div>hola [sound:hola.mp3]</div>"
    )
    assert revealed["current_card"]["study_view"]["rendered_back_html"] == (
        "<div>Reading: hola</div><div>Back: hello</div>"
        '<div>Example: <img src="hola.png">example sentence</div>'
    )
    assert revealed["current_card"]["study_view"]["rendered_front_telegram_html"] == (
        "hola [sound:hola.mp3]"
    )
    assert revealed["current_card"]["study_view"]["rendered_back_telegram_html"] == (
        "Reading: hola\nBack: hello\nExample: example sentence"
    )
    assert revealed["current_card"]["study_view"]["front_card_text"] == "hola"
    assert revealed["current_card"]["study_view"]["back_card_text"] == EXPECTED_BACK_CARD_TEXT
    assert revealed["current_card"]["preview_spec"]["revealState"] == "answer_revealed"
    assert '<div class="oc-preview-root">' in revealed["current_card"]["preview_spec"]["back"]
    assert "file:///" not in revealed["current_card"]["preview_spec"]["front"]
    assert (
        "Image unavailable (MEDIA_FILE_MISSING)"
        in revealed["current_card"]["preview_spec"]["back"]
    )
    assert revealed["current_card"]["study_media_spec"]["images"][0]["logicalPath"] == (
        "collection.media/hola.png"
    )
    assert revealed["current_card"]["preview_spec"]["degraded"][0]["errorCode"] == (
        "MEDIA_FILE_MISSING"
    )
    assert revealed["current_card"]["tutoring_summary"]["reveal_state"] == "answer_revealed"
    assert revealed["current_card"]["tutoring_summary"]["answer"] == EXPECTED_BACK_CARD_TEXT
    assert "fields" not in revealed["current_card"]
    supporting = revealed["current_card"]["study_view"]["supporting"]
    assert any(entry["field"] == "Reading" for entry in supporting)

    graded = service.grade(session_id=session_id, rating="good")
    assert graded["graded_card"]["rating"] == "good"
    assert graded["next_card"]["card_id"] == 202
    assert graded["session"]["completed_count"] == 1

    summary = service.summary(session_id=session_id)
    assert summary["session"]["remaining_count"] == 1
    assert summary["session"]["grade_counts"]["good"] == 1
    assert summary["session"]["queue_summary"]["completed"] == 1

    persisted = json.loads((state_dir / "study-sessions.json").read_text())
    assert persisted["active_session_id"] == session_id


@pytest.mark.unit
def test_study_start_cli_returns_structured_payload(
    runner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from ankicli import main as main_module

    state_dir = tmp_path / "state"
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    media_root = tmp_path / "collection.media"
    media_root.mkdir()
    (media_root / "hola.mp3").write_text("audio")
    monkeypatch.setenv("ANKICLI_STATE_DIR", str(state_dir))
    monkeypatch.setattr(main_module, "get_backend", lambda backend_name: _StudyBackend())

    result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "study",
            "start",
            "--deck",
            "Spanish",
            "--scope-preset",
            "due",
            "--limit",
            "1",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["session"]["card_count"] == 1
    assert payload["data"]["session"]["scope"]["preset"] == "due"
    assert payload["data"]["current_card"]["prompt"] == "hola [sound:hola.mp3]"
    assert (
        payload["data"]["current_card"]["study_view"]["rendered_front_html"]
        == "<div>hola [sound:hola.mp3]</div>"
    )
    assert payload["data"]["current_card"]["study_view"]["rendered_back_html"] is None
    assert payload["data"]["current_card"]["study_view"]["rendered_front_telegram_html"] == (
        "hola [sound:hola.mp3]"
    )
    assert payload["data"]["current_card"]["study_view"]["rendered_back_telegram_html"] is None
    assert payload["data"]["current_card"]["study_view"]["front_card_text"] == "hola"
    assert payload["data"]["current_card"]["study_view"]["back_card_text"] is None
    assert payload["data"]["current_card"]["preview_spec"]["kind"] == "anki_card_preview"
    assert (
        '<div class="oc-preview-root">'
        in payload["data"]["current_card"]["preview_spec"]["front"]
    )
    assert payload["data"]["current_card"]["tutoring_summary"]["prompt"] == "hola"
    assert payload["data"]["current_card"]["media"]["audio"][0]["path"] == str(
        media_root / "hola.mp3"
    )


@pytest.mark.unit
def test_study_details_cli_returns_revealed_payload(
    runner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from ankicli import main as main_module

    state_dir = tmp_path / "state"
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    monkeypatch.setenv("ANKICLI_STATE_DIR", str(state_dir))
    monkeypatch.setattr(main_module, "get_backend", lambda backend_name: _StudyBackend())

    start_result = runner.invoke(
        args=[
            "--json",
            "--collection",
            str(collection_path),
            "study",
            "start",
            "--deck",
            "Spanish",
            "--scope-preset",
            "due",
            "--limit",
            "1",
        ],
    )
    assert start_result.exit_code == 0
    session_id = json.loads(start_result.stdout)["data"]["session"]["id"]

    details_result = runner.invoke(
        args=["--json", "study", "details", "--session-id", session_id],
    )

    assert details_result.exit_code == 0
    payload = json.loads(details_result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["current_card"]["revealed"] is False
    assert "answer" not in payload["data"]["current_card"]
    assert payload["data"]["current_card"]["tutoring_summary"]["reveal_state"] == "front_only"
    assert payload["data"]["current_card"]["study_view"]["rendered_back_html"] is None


@pytest.mark.unit
def test_study_service_falls_back_to_field_text_when_rendered_presentation_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    monkeypatch.setenv("ANKICLI_STATE_DIR", str(state_dir))
    service = StudyService(_StudyBackend())

    started = service.start(
        str(collection_path),
        deck="Spanish",
        query="deck:Spanish",
        scope_preset="custom",
        limit=2,
    )
    graded = service.reveal(session_id=started["session"]["id"])
    next_card = service.grade(session_id=started["session"]["id"], rating="good")["next_card"]

    assert graded["current_card"]["study_view"]["rendered_back_html"] == (
        "<div>Reading: hola</div><div>Back: hello</div>"
        '<div>Example: <img src="hola.png">example sentence</div>'
    )
    assert graded["current_card"]["study_view"]["rendered_back_telegram_html"] == (
        "Reading: hola\nBack: hello\nExample: example sentence"
    )
    assert graded["current_card"]["study_view"]["back_card_text"] == EXPECTED_BACK_CARD_TEXT
    assert next_card["card_id"] == 202
    assert next_card["study_view"]["rendered_front_html"] is None
    assert next_card["study_view"]["rendered_back_html"] is None
    assert next_card["study_view"]["rendered_front_telegram_html"] is None
    assert next_card["study_view"]["rendered_back_telegram_html"] is None
    assert next_card["study_view"]["front_card_text"] == "adios"
    assert next_card["study_view"]["back_card_text"] is None


@pytest.mark.unit
def test_study_service_normalizes_html_rich_presentation_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _HtmlBackend(_StudyBackend):
        def get_card_presentation(self, collection_path: Path, card_id: int) -> dict | None:
            del collection_path
            if card_id != 201:
                return None
            return {
                "front_html": (
                    "<section><div>Hello&nbsp;<b>there</b><br>friend</div>"
                    '<div><span class="spoiler">secret</span> '
                    '<img src="hello.png" alt="wave icon"></div></section>'
                ),
                "back_html": (
                    '<div><a href="https://example.com">link</a> '
                    '<span style="color:red">styled</span> <script>alert(1)</script>'
                    "<pre>mono</pre></div>"
                ),
            }

    state_dir = tmp_path / "state"
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    monkeypatch.setenv("ANKICLI_STATE_DIR", str(state_dir))
    service = StudyService(_HtmlBackend())

    started = service.start(
        str(collection_path),
        deck="Spanish",
        query="deck:Spanish",
        scope_preset="custom",
        limit=1,
    )
    revealed = service.reveal(session_id=started["session"]["id"])

    assert started["current_card"]["study_view"]["rendered_front_html"] == (
        "<section><div>Hello&nbsp;<b>there</b><br>friend</div>"
        '<div><span class="spoiler">secret</span> '
        '<img src="hello.png" alt="wave icon"></div></section>'
    )
    assert started["current_card"]["study_view"]["rendered_back_html"] is None
    assert started["current_card"]["study_view"]["rendered_front_telegram_html"] == (
        "Hello <b>there</b>\nfriend\n<tg-spoiler>secret</tg-spoiler> wave icon"
    )
    assert started["current_card"]["study_view"]["rendered_back_telegram_html"] is None
    assert started["current_card"]["study_view"]["front_card_text"] == (
        "Hello there\nfriend\nsecret wave icon"
    )
    assert started["current_card"]["study_view"]["back_card_text"] is None
    assert revealed["current_card"]["study_view"]["rendered_back_html"] == (
        '<div><a href="https://example.com">link</a> '
        '<span style="color:red">styled</span> <script>alert(1)</script>'
        "<pre>mono</pre></div>"
    )
    assert revealed["current_card"]["study_view"]["rendered_back_telegram_html"] == (
        '<a href="https://example.com">link</a> styled <pre>mono</pre>'
    )
    assert revealed["current_card"]["study_view"]["back_card_text"] == "link styled alert(1)mono"


@pytest.mark.unit
def test_preview_spec_rewrites_anki_play_macros_and_local_asset_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _AnkiPlayBackend(_StudyBackend):
        def get_card(self, collection_path: Path, card_id: int) -> dict:
            del collection_path, card_id
            return {"id": 201, "note_id": 101, "deck_id": 55, "template": "Listen"}

        def get_note(self, collection_path: Path, note_id: int) -> dict:
            del collection_path, note_id
            return {
                "id": 101,
                "model": "Basic",
                "fields": {
                    "Front": "listen",
                    "AudioOne": "[sound:q0.mp3]",
                    "AudioTwo": "[sound:q1.mp3]",
                    "Back": "answer",
                },
                "tags": ["audio"],
            }

        def get_model_fields(self, collection_path: Path, *, name: str) -> dict:
            del collection_path, name
            return {"fields": ["Front", "AudioOne", "AudioTwo", "Back"]}

        def get_card_presentation(self, collection_path: Path, card_id: int) -> dict | None:
            del collection_path, card_id
            return {
                "front_html": (
                    '<style>@import url("_deck.css");</style>'
                    "<div>[anki:play:q:0]</div><div>[anki:play:q:1]</div>"
                ),
                "back_html": None,
            }

    state_dir = tmp_path / "state"
    collection_path = tmp_path / "collection.anki2"
    collection_path.write_text("fixture")
    media_root = tmp_path / "collection.media"
    media_root.mkdir()
    (media_root / "q0.mp3").write_text("audio-0")
    (media_root / "q1.mp3").write_text("audio-1")
    (media_root / "_deck.css").write_text(".card { color: red; }")
    monkeypatch.setenv("ANKICLI_STATE_DIR", str(state_dir))
    service = StudyService(_AnkiPlayBackend())

    started = service.start(
        str(collection_path),
        deck="Audio",
        query="deck:Audio",
        scope_preset="custom",
        limit=1,
    )

    preview = started["current_card"]["preview_spec"]
    study_media_spec = started["current_card"]["study_media_spec"]
    assert "[anki:play:q:0]" not in preview["front"]
    assert "[anki:play:q:1]" not in preview["front"]
    assert preview["front"].count("<audio controls") == 2
    assert "collection.media/q0.mp3" in preview["front"]
    assert "collection.media/q1.mp3" in preview["front"]
    assert "collection.media/_deck.css" in preview["front"]
    assert study_media_spec["audio"][0]["logicalPath"] == "collection.media/q0.mp3"
    assert study_media_spec["audio"][1]["logicalPath"] == "collection.media/q1.mp3"
    assert study_media_spec["answer_audio"] == []
    logical_paths = [asset["logicalPath"] for asset in preview["assets"]]
    assert "collection.media/_deck.css" in logical_paths


@pytest.mark.unit
def test_catalog_export_cli_returns_runtime_support(runner) -> None:
    result = runner.invoke(args=["--json", "--backend", "ankiconnect", "catalog", "export"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["schema_version"]
    assert "operations" in payload["data"]
    assert "workflows" in payload["data"]
    assert "plugin_tools" in payload["data"]
    assert "skills" in payload["data"]
    assert "supported_workflows" in payload["data"]
    assert "workflow_support" in payload["data"]
    assert payload["data"]["error_taxonomy"]
