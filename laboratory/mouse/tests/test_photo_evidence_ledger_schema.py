from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app import db


def test_photo_evidence_item_schema_links_photo_parse_and_note(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(photo_evidence_item)").fetchall()
            }

            assert {
                "photo_evidence_id",
                "source_photo_id",
                "parse_id",
                "card_snapshot_id",
                "note_item_id",
                "card_type",
                "evidence_kind",
                "roi_label",
                "bbox_json",
                "observed_raw_text",
                "ocr_text",
                "parsed_value",
                "confidence",
                "interpretation",
                "needs_review",
                "review_reason",
                "linked_mouse_id",
                "linked_cage_id",
                "linked_event_id",
                "status",
                "created_at",
                "updated_at",
            }.issubset(columns)

            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_evidence",
                    "evidence-card.jpg",
                    "data/photos/test/evidence-card.jpg",
                    "2026-05-09T00:00:00Z",
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
                    "parse_evidence",
                    "photo_evidence",
                    "manual_photo_transcription",
                    "{}",
                    "2026-05-09T00:00:01Z",
                    "review",
                    0.75,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO card_note_item_log
                    (note_item_id, photo_id, parse_id, raw_line_text, parsed_type,
                     interpreted_status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "note_evidence",
                    "photo_evidence",
                    "parse_evidence",
                    "318 R0",
                    "mouse_item",
                    "active",
                    0.6,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO photo_evidence_item
                    (photo_evidence_id, source_photo_id, parse_id, note_item_id,
                     card_type, evidence_kind, roi_label, bbox_json,
                     observed_raw_text, ocr_text, parsed_value, confidence,
                     interpretation, needs_review, review_reason, status,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "pe_ear_318",
                    "photo_evidence",
                    "parse_evidence",
                    "note_evidence",
                    "separated",
                    "ear_label",
                    "notes",
                    '{"x":10,"y":20,"w":80,"h":24}',
                    "318 R0",
                    "318 R0",
                    "R_CIRCLE",
                    0.6,
                    "R0 may be right circle and must remain reviewable.",
                    1,
                    "Ambiguous ear mark.",
                    "review_open",
                    "2026-05-09T00:00:02Z",
                    "2026-05-09T00:00:02Z",
                ),
            )

            row = conn.execute(
                """
                SELECT observed_raw_text, ocr_text, parsed_value, needs_review
                FROM photo_evidence_item
                WHERE photo_evidence_id = ?
                """,
                ("pe_ear_318",),
            ).fetchone()

            assert dict(row) == {
                "observed_raw_text": "318 R0",
                "ocr_text": "318 R0",
                "parsed_value": "R_CIRCLE",
                "needs_review": 1,
            }

            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO photo_evidence_item
                        (photo_evidence_id, source_photo_id, evidence_kind, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "pe_missing_photo",
                        "missing_photo",
                        "card_field",
                        "2026-05-09T00:00:03Z",
                        "2026-05-09T00:00:03Z",
                    ),
                )
    finally:
        db.DB_PATH = old_db_path
