from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app.main import app, create_card_snapshot, write_note_items_and_mouse_candidates


def seed_focus_review_card(tmp_path: Path) -> None:
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    db.init_db()
    photo_id = "photo_focus_review"
    parse_id = "parse_focus_review"
    created_at = "2026-05-09T10:17:00Z"
    record = {
        "type": "Separated",
        "rawStrain": "C57BL/6J",
        "matchedStrain": "C57BL/6J",
        "sexRaw": "mixed",
        "dobRaw": "2025-02-10",
        "mouseCount": "3 total",
        "confidence": 82,
        "notes": [
            {"raw": "MT318 R'", "strike": "none"},
            {"raw": "MT319 L'", "strike": "none"},
            {"raw": "MT320", "strike": "none"},
        ],
    }
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO photo_log
                (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                photo_id,
                "focus-review-card.jpg",
                "data/photos/test/focus-review-card.jpg",
                "2026-05-09T10:15:30Z",
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
                parse_id,
                photo_id,
                "manual_photo_transcription",
                json.dumps(record, ensure_ascii=False),
                created_at,
                "review",
                82,
                1,
            ),
        )
        snapshot_id = create_card_snapshot(conn, parse_id, photo_id, record, created_at)
        write_note_items_and_mouse_candidates(conn, parse_id, {**record, "cardSnapshotId": snapshot_id}, "review")
        conn.execute(
            """
            INSERT INTO review_queue
                (review_id, parse_id, severity, issue, current_value,
                 suggested_value, review_reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "review_duplicate_mt319",
                parse_id,
                "High",
                "Duplicate active mouse",
                "MT319 active in two card snapshots",
                "Resolve duplicate active mouse before export.",
                "MT319 appears to duplicate an existing active mouse. Review before canonical apply.",
                "open",
                "2026-05-09T10:18:00Z",
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
                "review_unlabeled_numeric_parse_focus_review",
                parse_id,
                "Medium",
                "Unlabeled numeric note needs review",
                "MT320",
                "Confirm note-line interpretation.",
                "Needs quick confirmation from source photo.",
                "open",
                "2026-05-09T10:19:00Z",
            ),
        )


def test_focus_review_groups_db_backed_review_items_by_photo_card(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        seed_focus_review_card(tmp_path)
        client = TestClient(app)

        response = client.get("/api/ui/focus-review")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_layer"] == "export or view"
        assert payload["workload_summary"]["must_review"] == 1
        assert payload["workload_summary"]["quick_check"] >= 1
        assert payload["empty_state"]["fabricated_records"] is False
        [card] = payload["cards"]
        assert card["source_photo"]["photo_id"] == "photo_focus_review"
        assert card["source_photo"]["source_photo_role"] == "primary_evidence"
        assert card["source_photo"]["open_source_photo_label"] == "Open source photo"
        assert card["card_snapshot"]["card_type"] == "Separated"
        assert card["review_count"] >= 2
        review_ids = {item["review_id"] for item in card["review_items"]}
        assert {"review_duplicate_mt319", "review_unlabeled_numeric_parse_focus_review"}.issubset(review_ids)
        assert any(item["attention_level"] == "must_review" for item in card["review_items"])
        assert any(item["attention_level"] == "quick_check" for item in card["review_items"])
        assert [row["mouse_id"] for row in card["mouse_rows"]] == ["MT318", "MT319"]
        assert card["collapsed_sections"]["note_lines"] == 2
        assert card["collapsed_sections"]["evidence"] >= 1
        assert card["actions"] == ["Apply confirmed rows only", "Hold card", "Open source photo"]
    finally:
        db.DB_PATH = old_db_path


def test_focus_review_empty_state_does_not_fabricate_colony_data(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()
        client = TestClient(app)

        response = client.get("/api/ui/focus-review")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_layer"] == "export or view"
        assert payload["workload_summary"] == {"must_review": 0, "quick_check": 0}
        assert payload["cards"] == []
        assert payload["empty_state"] == {
            "message": "No Focus Review items are currently open.",
            "fabricated_records": False,
        }
    finally:
        db.DB_PATH = old_db_path
