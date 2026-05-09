from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app import db
from app.main import PhotoManualTranscriptionCreate, create_photo_manual_transcription, review_item_audit_view


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
            link_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(review_evidence_link)").fetchall()
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
            assert {
                "link_id",
                "review_id",
                "photo_evidence_id",
                "link_reason",
                "created_at",
            }.issubset(link_columns)

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


def test_manual_transcription_creates_photo_evidence_items(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_transcription_evidence",
                    "transcription-card.jpg",
                    "data/photos/test/transcription-card.jpg",
                    "2026-05-09T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )

        result = create_photo_manual_transcription(
            "photo_transcription_evidence",
            PhotoManualTranscriptionCreate(
                card_type="Separated",
                raw_strain="ApoM Tg/Tg",
                sex_raw="F",
                mouse_count="2 total",
                confidence=64,
                uncertain_fields=["sex_raw"],
                raw_visible_text_lines=["ApoM Tg/Tg", "F 2 total", "318 R0"],
                extraction_regions=[
                    {
                        "label": "raw_strain",
                        "target_fields": ["raw_strain", "matched_strain"],
                        "mode": "single_line_field",
                    },
                    {
                        "label": "notes",
                        "target_fields": ["notes", "raw_visible_text_lines"],
                        "mode": "multi_line_evidence",
                    },
                ],
                notes=[
                    {"raw": "318 R0", "meaning": "possible mouse", "strike": "none"},
                    {"raw": "319 L'", "meaning": "mouse", "strike": "none"},
                ],
            ),
        )

        with db.connection() as conn:
            rows = conn.execute(
                """
                SELECT source_photo_id, parse_id, note_item_id, card_type,
                       evidence_kind, roi_label, observed_raw_text,
                       ocr_text, parsed_value, confidence, needs_review,
                       review_reason, status
                FROM photo_evidence_item
                WHERE parse_id = ?
                ORDER BY evidence_kind, roi_label, observed_raw_text
                """,
                (result["parse_id"],),
            ).fetchall()

        payloads = [dict(row) for row in rows]
        assert any(
            item["evidence_kind"] == "card_field"
            and item["roi_label"] == "raw_strain"
            and item["observed_raw_text"] == "ApoM Tg/Tg"
            and item["parsed_value"] == "ApoM Tg/Tg"
            and item["needs_review"] == 0
            for item in payloads
        )
        assert any(
            item["evidence_kind"] == "card_field"
            and item["roi_label"] == "sex_raw"
            and item["observed_raw_text"] == "F"
            and item["needs_review"] == 1
            and "uncertain" in item["review_reason"].lower()
            for item in payloads
        )
        assert any(
            item["evidence_kind"] == "note_line"
            and item["note_item_id"] == f"note_{result['parse_id']}_1"
            and item["observed_raw_text"] == "318 R0"
            and item["needs_review"] == 1
            for item in payloads
        )
        assert all(item["source_photo_id"] == "photo_transcription_evidence" for item in payloads)
        assert all(item["status"] in {"draft", "review_open"} for item in payloads)
    finally:
        db.DB_PATH = old_db_path


def test_manual_transcription_links_review_to_photo_evidence_and_audit(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_review_evidence",
                    "review-evidence-card.jpg",
                    "data/photos/test/review-evidence-card.jpg",
                    "2026-05-09T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )

        result = create_photo_manual_transcription(
            "photo_review_evidence",
            PhotoManualTranscriptionCreate(
                card_type="Separated",
                raw_strain="ApoM Tg/Tg",
                sex_raw="F",
                mouse_count="1 total",
                confidence=58,
                uncertain_fields=["mouse_count"],
                notes=[{"raw": "318 R0", "meaning": "possible mouse", "strike": "none"}],
            ),
        )

        with db.connection() as conn:
            linked_rows = conn.execute(
                """
                SELECT link.review_id, evidence.photo_evidence_id,
                       evidence.evidence_kind, evidence.observed_raw_text,
                       evidence.needs_review
                FROM review_evidence_link link
                JOIN photo_evidence_item evidence
                  ON evidence.photo_evidence_id = link.photo_evidence_id
                WHERE link.review_id = ?
                ORDER BY evidence.evidence_kind, evidence.observed_raw_text
                """,
                (result["review_id"],),
            ).fetchall()
            audit = review_item_audit_view(conn, result["review_id"])

        linked_payloads = [dict(row) for row in linked_rows]
        assert any(
            item["evidence_kind"] == "card_field"
            and item["observed_raw_text"] == "1 total"
            and item["needs_review"] == 1
            for item in linked_payloads
        )
        assert any(
            item["evidence_kind"] == "note_line"
            and item["observed_raw_text"] == "318 R0"
            for item in linked_payloads
        )
        assert audit["summary"]["photo_evidence_count"] == len(linked_payloads)
        assert any(
            item["evidence_kind"] == "card_field"
            and item["observed_raw_text"] == "1 total"
            and item["needs_review"] == 1
            for item in audit["photo_evidence_items"]
        )
        assert any(
            item["evidence_kind"] == "note_line"
            and item["observed_raw_text"] == "318 R0"
            for item in audit["photo_evidence_items"]
        )
    finally:
        db.DB_PATH = old_db_path
