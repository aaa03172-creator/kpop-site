from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_static_ui_exposes_review_assistant_draft_controls() -> None:
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

    assert "/assistant-draft" in html
    assert "assistant-review-draft" in html
    assert "renderAssistantReviewDraft" in html
    assert "function loadAssistantReviewDraft" in html
    assert "Load Assistant Draft" in html
    assert "function fillReviewResolutionFromAssistantDraft" in html
    assert "apply-assistant-review-draft" in html
    assert "Apply Draft To Form" in html
    assert "Assistant draft unavailable" in html
    assert "Review source evidence directly; no canonical state was changed." in html

    start = html.index("function fillReviewResolutionFromAssistantDraft")
    end = html.index("async function loadAssistantReviewDraft", start)
    fill_function = html[start:end]
    assert ".review-resolved-value" in fill_function
    assert ".review-resolution-note" in fill_function
    assert "Assistant draft copied into the form" in fill_function
    assert "submitReviewResolution" not in fill_function
    assert "api(" not in fill_function

    start = html.index("async function loadAssistantReviewDraft")
    end = html.index("function attachReviewAuditHandler", start)
    load_function = html[start:end]
    assert "try {" in load_function
    assert "catch (error)" in load_function
    assert 'panel.dataset.stateKind = "error"' in load_function
    assert "apiErrorMessage(error)" in load_function
    assert "return null;" in load_function


def test_review_assistant_draft_is_local_read_only_and_traceable(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_assistant_draft",
                    "assistant-draft-card.jpg",
                    "data/photos/test/assistant-draft-card.jpg",
                    "2026-05-12T10:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "parse_assistant_draft",
                    "photo_assistant_draft",
                    "ai_photo_extraction",
                    json.dumps({"confidence": 42, "rawStrain": "ApoM ?", "sexRaw": "M?"}, ensure_ascii=False),
                    "2026-05-12T10:01:00Z",
                    "review",
                    42,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO card_note_item_log
                    (note_item_id, parse_id, photo_id, raw_line_text, parsed_type,
                     interpreted_status, parsed_mouse_display_id, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "note_assistant_draft",
                    "parse_assistant_draft",
                    "photo_assistant_draft",
                    "MT901 R0 male? verify",
                    "mouse_item",
                    "active",
                    "MT901",
                    0.42,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value,
                     suggested_value, review_reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_assistant_draft",
                    "parse_assistant_draft",
                    "High",
                    "AI-extracted photo transcription needs review",
                    "ApoM ? / M?",
                    "Confirm MT901 strain and sex from source photo.",
                    "Low-confidence OCR draft needs focused review before export.",
                    "open",
                    "2026-05-12T10:02:00Z",
                ),
            )
            before_actions = conn.execute("SELECT COUNT(*) FROM action_log").fetchone()[0]
            before_corrections = conn.execute("SELECT COUNT(*) FROM correction_log").fetchone()[0]

        client = TestClient(app)
        response = client.get("/api/review-items/review_assistant_draft/assistant-draft")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_layer"] == "review item"
        assert payload["boundary"] == "review item"
        assert payload["draft_kind"] == "assistant_review_draft"
        assert payload["external_payload_policy"] == "local_only_until_approved"
        assert payload["writes_canonical_state"] is False
        assert payload["requires_operator_approval"] is True
        assert payload["review"]["review_id"] == "review_assistant_draft"
        assert payload["evidence_refs"]["source_photo_id"] == "photo_assistant_draft"
        assert payload["evidence_refs"]["note_item_ids"] == ["note_assistant_draft"]
        assert payload["draft"]["resolution_payload"]["resolved_value"] == "Confirm MT901 strain and sex from source photo."
        assert payload["draft"]["resolution_payload"]["correction_entity_type"] == "review_item"
        assert payload["draft"]["resolution_payload"]["correction_entity_id"] == "review_assistant_draft"
        assert payload["draft"]["resolution_payload"]["correction_before_value"] == "ApoM ? / M?"
        assert payload["draft"]["resolution_payload"]["correction_after_value"] == "Confirm MT901 strain and sex from source photo."
        assert "MT901 R0 male? verify" in payload["draft"]["evidence_summary"]
        assert "operator" in payload["draft"]["operator_note"].lower()

        with db.connection() as conn:
            after_actions = conn.execute("SELECT COUNT(*) FROM action_log").fetchone()[0]
            after_corrections = conn.execute("SELECT COUNT(*) FROM correction_log").fetchone()[0]
        assert after_actions == before_actions
        assert after_corrections == before_corrections
    finally:
        db.DB_PATH = old_db_path


def test_review_assistant_draft_404_for_missing_review(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()
        client = TestClient(app)

        response = client.get("/api/review-items/missing_review/assistant-draft")

        assert response.status_code == 404
    finally:
        db.DB_PATH = old_db_path
