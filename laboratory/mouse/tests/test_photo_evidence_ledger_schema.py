from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException

from app import db
from app.main import (
    PhotoManualTranscriptionCreate,
    apply_canonical_candidate,
    canonical_candidate_apply_preview,
    canonical_candidate_audit_view,
    create_photo_manual_transcription,
    import_sample_fixture,
    review_item_audit_view,
    void_canonical_candidate,
)


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
            photo_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(photo_log)").fetchall()
            }
            parse_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(parse_result)").fetchall()
            }
            assert "source_layer" in photo_columns
            assert "source_layer" in parse_columns
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
            boundary_row = conn.execute(
                """
                SELECT photo.source_layer AS photo_source_layer,
                       parse.source_layer AS parse_source_layer,
                       parse.source_name AS parse_source_name,
                       parse.raw_payload AS parse_raw_payload,
                       snapshot.source_layer AS snapshot_source_layer
                FROM parse_result parse
                JOIN photo_log photo ON photo.photo_id = parse.photo_id
                JOIN card_snapshot snapshot ON snapshot.parse_id = parse.parse_id
                WHERE parse.parse_id = ?
                """,
                (result["parse_id"],),
            ).fetchone()

        payloads = [dict(row) for row in rows]
        assert dict(boundary_row) == {
            "photo_source_layer": "raw source",
            "parse_source_layer": "parsed or intermediate result",
            "parse_source_name": "manual_photo_transcription",
            "parse_raw_payload": boundary_row["parse_raw_payload"],
            "snapshot_source_layer": "parsed or intermediate result",
        }
        parse_payload = json.loads(boundary_row["parse_raw_payload"])
        assert parse_payload["payload_kind"] == "manual_photo_transcription"
        assert parse_payload["source_layer"] == "parsed or intermediate result"
        assert parse_payload["schema_version"] == "parse_payload_v1"
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


def test_fixture_import_tags_parse_payload_boundary(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()

        result = import_sample_fixture()

        assert result["imported_parse_results"] > 0
        with db.connection() as conn:
            row = conn.execute(
                """
                SELECT raw_payload
                FROM parse_result
                WHERE source_name = 'fixtures/sample_parse_results.json'
                ORDER BY parsed_at, parse_id
                LIMIT 1
                """
            ).fetchone()

        payload = json.loads(row["raw_payload"])
        assert payload["payload_kind"] == "fixture_parse_import"
        assert payload["source_layer"] == "parsed or intermediate result"
        assert payload["schema_version"] == "parse_payload_v1"
    finally:
        db.DB_PATH = old_db_path


def test_manual_transcription_splits_raw_extracted_and_normalized_values(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(photo_evidence_item)").fetchall()
            }
            assert "raw_extracted_value" in columns
            assert "normalized_value" in columns
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_raw_normalized_split",
                    "raw-normalized-card.jpg",
                    "data/photos/test/raw-normalized-card.jpg",
                    "2026-05-09T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )

        result = create_photo_manual_transcription(
            "photo_raw_normalized_split",
            PhotoManualTranscriptionCreate(
                card_type="Separated",
                raw_strain="ApoMtg/tg",
                matched_strain="ApoM Tg/Tg",
                sex_raw="F",
                sex_normalized="female",
                dob_raw="2026.03.01",
                dob_normalized="2026-03-01",
                mouse_count="2 total",
                confidence=82,
            ),
        )

        with db.connection() as conn:
            rows = conn.execute(
                """
                SELECT roi_label, observed_raw_text, parsed_value,
                       raw_extracted_value, normalized_value
                FROM photo_evidence_item
                WHERE parse_id = ?
                  AND evidence_kind = 'card_field'
                ORDER BY photo_evidence_id
                """,
                (result["parse_id"],),
            ).fetchall()

        by_label = {row["roi_label"]: dict(row) for row in rows}
        assert by_label["raw_strain"]["raw_extracted_value"] == "ApoMtg/tg"
        assert by_label["raw_strain"]["normalized_value"] == "ApoM Tg/Tg"
        assert by_label["sex_raw"]["raw_extracted_value"] == "F"
        assert by_label["sex_raw"]["normalized_value"] == "female"
        assert by_label["dob_raw"]["raw_extracted_value"] == "2026.03.01"
        assert by_label["dob_raw"]["normalized_value"] == "2026-03-01"
    finally:
        db.DB_PATH = old_db_path


def test_manual_transcription_stores_confidence_source_and_evidence_reference(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(photo_evidence_item)").fetchall()
            }
            assert "confidence_source" in columns
            assert "evidence_reference_json" in columns
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_confidence_reference",
                    "confidence-reference-card.jpg",
                    "data/photos/test/confidence-reference-card.jpg",
                    "2026-05-09T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )

        result = create_photo_manual_transcription(
            "photo_confidence_reference",
            PhotoManualTranscriptionCreate(
                card_type="Separated",
                raw_strain="ApoM Tg/Tg",
                sex_raw="F",
                mouse_count="1 total",
                confidence=58,
                extraction_method="ai_photo_extraction",
                notes=[{"raw": "318 R0", "meaning": "possible mouse", "strike": "none"}],
            ),
        )

        with db.connection() as conn:
            field_row = conn.execute(
                """
                SELECT photo_evidence_id, confidence_source, evidence_reference_json
                FROM photo_evidence_item
                WHERE parse_id = ?
                  AND evidence_kind = 'card_field'
                  AND roi_label = 'raw_strain'
                """,
                (result["parse_id"],),
            ).fetchone()
            note_row = conn.execute(
                """
                SELECT photo_evidence_id, confidence_source, evidence_reference_json
                FROM photo_evidence_item
                WHERE parse_id = ?
                  AND evidence_kind = 'note_line'
                """,
                (result["parse_id"],),
            ).fetchone()
            parse_row = conn.execute(
                "SELECT raw_payload FROM parse_result WHERE parse_id = ?",
                (result["parse_id"],),
            ).fetchone()

        parse_payload = json.loads(parse_row["raw_payload"])
        field_reference = json.loads(field_row["evidence_reference_json"])
        note_reference = json.loads(note_row["evidence_reference_json"])
        assert parse_payload["payload_kind"] == "ai_photo_extraction"
        assert parse_payload["source_layer"] == "parsed or intermediate result"
        assert parse_payload["schema_version"] == "parse_payload_v1"
        assert field_row["confidence_source"] == "ai_photo_extraction:card_field"
        assert field_reference["source_layer"] == "parsed or intermediate result"
        assert field_reference["source_photo_id"] == "photo_confidence_reference"
        assert field_reference["parse_id"] == result["parse_id"]
        assert field_reference["card_snapshot_id"] == result["card_snapshot_id"]
        assert field_reference["roi_label"] == "raw_strain"
        assert note_row["confidence_source"] == "ai_photo_extraction:note_line"
        assert note_reference["note_item_id"] == f"note_{result['parse_id']}_1"
        assert note_reference["source_photo_id"] == "photo_confidence_reference"
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


def test_manual_transcription_review_item_stores_minimum_evidence_context(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(review_queue)").fetchall()
            }
            assert "source_layer" in columns
            assert "evidence_reference_json" in columns
            assert "review_trigger_json" in columns
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_review_context",
                    "review-context-card.jpg",
                    "data/photos/test/review-context-card.jpg",
                    "2026-05-09T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )

        result = create_photo_manual_transcription(
            "photo_review_context",
            PhotoManualTranscriptionCreate(
                card_type="Separated",
                raw_strain="ApoM Tg/Tg",
                sex_raw="6",
                mouse_count="",
                confidence=52,
                uncertain_fields=["sex_raw"],
                plausibility_findings=[
                    {
                        "field": "sex_raw",
                        "severity": "high",
                        "message": "Sex field looks like a count.",
                    }
                ],
            ),
        )

        with db.connection() as conn:
            review = conn.execute(
                """
                SELECT source_layer, evidence_reference_json, review_trigger_json
                FROM review_queue
                WHERE review_id = ?
                """,
                (result["review_id"],),
            ).fetchone()

        evidence_reference = json.loads(review["evidence_reference_json"])
        trigger = json.loads(review["review_trigger_json"])
        assert review["source_layer"] == "review item"
        assert evidence_reference["source_photo_id"] == "photo_review_context"
        assert evidence_reference["parse_id"] == result["parse_id"]
        assert evidence_reference["card_snapshot_id"] == result["card_snapshot_id"]
        assert evidence_reference["linked_photo_evidence_items"] == result["linked_photo_evidence_items"]
        assert trigger["reason"] == "manual_transcription_review_required"
        assert trigger["confidence"] == 52
        assert trigger["uncertain_fields"] == ["sex_raw"]
        assert trigger["plausibility_findings"][0]["field"] == "sex_raw"
    finally:
        db.DB_PATH = old_db_path


def test_manual_transcription_review_trigger_lists_required_review_conditions(tmp_path: Path) -> None:
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
                    "photo_review_conditions",
                    "review-conditions-card.jpg",
                    "data/photos/test/review-conditions-card.jpg",
                    "2026-05-09T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )
            conn.execute(
                """
                INSERT INTO mouse_master
                    (mouse_id, display_id, raw_strain_text, sex, dob_raw,
                     source_note_item_id, status, source_photo_id,
                     last_verified_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "mouse_existing_318",
                    "318",
                    "ApoM Tg/Tg",
                    "male",
                    "2026-04-01",
                    "note_existing_318",
                    "active",
                    "photo_review_conditions",
                    "2026-05-08T00:00:00Z",
                    "2026-05-08T00:00:00Z",
                    "2026-05-08T00:00:00Z",
                ),
            )

        result = create_photo_manual_transcription(
            "photo_review_conditions",
            PhotoManualTranscriptionCreate(
                card_type="Separated",
                raw_strain="ApoMtg/tg",
                matched_strain="ApoM Tg/Tg",
                sex_raw="6",
                dob_raw="2026.04.32",
                dob_normalized="2026-04-32",
                mouse_count="2 total",
                confidence=48,
                uncertain_fields=["matched_strain", "dob_normalized"],
                plausibility_findings=[
                    {
                        "field": "sex_raw",
                        "severity": "high",
                        "message": "Sex field contains a count-like value.",
                    }
                ],
                notes=[
                    {"raw": "318 R0", "meaning": "possible mouse", "strike": "none"},
                    {"raw": "318 L'", "meaning": "same ID with different ear mark", "strike": "none"},
                    {"raw": "?", "meaning": "unclear source evidence", "strike": "none"},
                ],
            ),
        )

        with db.connection() as conn:
            review = conn.execute(
                """
                SELECT current_value, suggested_value, review_trigger_json
                FROM review_queue
                WHERE review_id = ?
                """,
                (result["review_id"],),
            ).fetchone()

        trigger = json.loads(review["review_trigger_json"])
        condition_keys = {condition["condition"] for condition in trigger["review_required_conditions"]}
        assert {
            "low_ocr_confidence",
            "uncertain_mouse_id_format",
            "snapshot_value_conflict",
            "canonical_state_conflict",
            "biologically_unlikely",
            "insufficient_source_evidence",
            "unconfirmed_normalization_rule",
        }.issubset(condition_keys)
        assert review["current_value"] == "2 total"
        assert "ApoM Tg/Tg" in review["suggested_value"]
        canonical_conflict = next(
            condition
            for condition in trigger["review_required_conditions"]
            if condition["condition"] == "canonical_state_conflict"
        )
        assert canonical_conflict["existing_value"] == "mouse_existing_318"
        assert canonical_conflict["new_value"] == "318"
    finally:
        db.DB_PATH = old_db_path


def test_canonical_candidate_apply_links_note_evidence_to_created_event(tmp_path: Path) -> None:
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
                    "photo_apply_evidence",
                    "apply-card.jpg",
                    "data/photos/test/apply-card.jpg",
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
                    "parse_apply_evidence",
                    "photo_apply_evidence",
                    "manual_photo_transcription",
                    "{}",
                    "2026-05-09T00:00:01Z",
                    "review",
                    88,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value,
                     suggested_value, review_reason, status, created_at, resolved_at, resolution_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_apply_evidence",
                    "parse_apply_evidence",
                    "Medium",
                    "Evidence comparison resolved",
                    json.dumps({"manual": {"display_id": "318", "strain": "ApoM Tg/Tg", "dob": "2026-04-01"}}),
                    "{}",
                    "Reviewer accepted photo-backed note line.",
                    "resolved",
                    "2026-05-09T00:00:02Z",
                    "2026-05-09T00:00:03Z",
                    "Accepted.",
                ),
            )
            conn.execute(
                """
                INSERT INTO canonical_candidate
                    (candidate_id, review_id, parse_id, proposed_mouse_display_id,
                     proposed_strain, proposed_dob, proposed_count, candidate_payload,
                     status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "candidate_apply_evidence",
                    "review_apply_evidence",
                    "parse_apply_evidence",
                    "318",
                    "ApoM Tg/Tg",
                    "2026-04-01",
                    "1",
                    json.dumps({"display_id": "318", "strain": "ApoM Tg/Tg", "dob": "2026-04-01"}),
                    "draft",
                    "2026-05-09T00:00:04Z",
                    "2026-05-09T00:00:04Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO card_note_item_log
                    (note_item_id, photo_id, parse_id, card_type, line_number,
                     raw_line_text, strike_status, parsed_type, interpreted_status,
                     parsed_mouse_display_id, parsed_ear_label_raw,
                     parsed_ear_label_confidence, parsed_ear_label_review_status,
                     confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "note_apply_evidence",
                    "photo_apply_evidence",
                    "parse_apply_evidence",
                    "Separated",
                    1,
                    "318 R0",
                    "none",
                    "mouse_item",
                    "active",
                    "318",
                    "R0",
                    92,
                    "verified",
                    92,
                    0,
                ),
            )
            conn.execute(
                """
                INSERT INTO photo_evidence_item
                    (photo_evidence_id, source_photo_id, parse_id, note_item_id,
                     card_type, evidence_kind, roi_label, observed_raw_text,
                     parsed_value, confidence, interpretation, needs_review,
                     status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "pe_apply_note",
                    "photo_apply_evidence",
                    "parse_apply_evidence",
                    "note_apply_evidence",
                    "Separated",
                    "note_line",
                    "note_line_1",
                    "318 R0",
                    "318",
                    92,
                    "Reviewer accepted mouse note line.",
                    0,
                    "review_open",
                    "2026-05-09T00:00:05Z",
                    "2026-05-09T00:00:05Z",
                ),
            )

        result = apply_canonical_candidate("candidate_apply_evidence")

        with db.connection() as conn:
            event = conn.execute(
                """
                SELECT event_id, details
                FROM mouse_event
                WHERE related_entity_id = ?
                """,
                ("candidate_apply_evidence",),
            ).fetchone()
            evidence = conn.execute(
                """
                SELECT linked_event_id, status
                FROM photo_evidence_item
                WHERE photo_evidence_id = ?
                """,
                ("pe_apply_note",),
            ).fetchone()

        details = json.loads(event["details"])
        assert result["created_events"] == 1
        assert details["photo_evidence_id"] == "pe_apply_note"
        assert details["source_photo_id"] == "photo_apply_evidence"
        assert details["canonical_apply_rule"] == {
            "source_layer": "canonical structured state",
            "requires_resolved_review": True,
            "requires_note_line_evidence": True,
            "requires_duplicate_check": True,
        }
        assert details["source_trace"] == {
            "source_photo_id": "photo_apply_evidence",
            "parse_id": "parse_apply_evidence",
            "note_item_id": "note_apply_evidence",
            "photo_evidence_id": "pe_apply_note",
        }
        assert evidence["linked_event_id"] == event["event_id"]
        assert evidence["status"] == "linked"
    finally:
        db.DB_PATH = old_db_path


def test_canonical_candidate_void_blocks_when_applied_mouse_row_is_missing(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("parse_missing_mouse_void", "manual_photo_transcription", "{}", "2026-05-09T00:00:01Z", "review", 88, 1),
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value,
                     suggested_value, review_reason, status, created_at, resolved_at, resolution_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_missing_mouse_void",
                    "parse_missing_mouse_void",
                    "Medium",
                    "Resolved canonical candidate",
                    "{}",
                    "{}",
                    "Reviewer accepted candidate.",
                    "resolved",
                    "2026-05-09T00:00:02Z",
                    "2026-05-09T00:00:03Z",
                    "Accepted.",
                ),
            )
            conn.execute(
                """
                INSERT INTO canonical_candidate
                    (candidate_id, review_id, parse_id, proposed_mouse_display_id,
                     proposed_strain, proposed_dob, proposed_count, candidate_payload,
                     status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "candidate_missing_mouse_void",
                    "review_missing_mouse_void",
                    "parse_missing_mouse_void",
                    "MISSING-318",
                    "ApoM Tg/Tg",
                    "2026-04-01",
                    "1",
                    json.dumps({"display_id": "MISSING-318"}),
                    "applied",
                    "2026-05-09T00:00:04Z",
                    "2026-05-09T00:00:04Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO mouse_event
                    (event_id, mouse_id, event_type, event_date, related_entity_type,
                     related_entity_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "event_missing_mouse_void",
                    "mouse_missing_318",
                    "canonical_candidate_applied",
                    "2026-05-09",
                    "canonical_candidate",
                    "candidate_missing_mouse_void",
                    "{}",
                    "2026-05-09T00:00:05Z",
                ),
            )

            audit = canonical_candidate_audit_view(conn, "candidate_missing_mouse_void")

        assert audit["applied_mouse_ids"] == ["mouse_missing_318"]
        assert audit["mice"] == []
        assert audit["missing_mouse_ids"] == ["mouse_missing_318"]
        assert audit["can_void"] is False
        assert "Applied mouse records are missing: mouse_missing_318." in audit["blockers"]

        with pytest.raises(HTTPException) as exc_info:
            void_canonical_candidate("candidate_missing_mouse_void")

        assert exc_info.value.status_code == 409
        detail = exc_info.value.detail
        assert detail["missing_mouse_ids"] == ["mouse_missing_318"]
        with db.connection() as conn:
            status = conn.execute(
                "SELECT status FROM canonical_candidate WHERE candidate_id = ?",
                ("candidate_missing_mouse_void",),
            ).fetchone()["status"]
            voided_events = conn.execute(
                "SELECT COUNT(*) AS count FROM mouse_event WHERE event_type = 'canonical_candidate_voided'",
            ).fetchone()["count"]

        assert status == "applied"
        assert voided_events == 0
    finally:
        db.DB_PATH = old_db_path


def test_canonical_candidate_apply_blocks_unresolved_note_review_and_missing_evidence(tmp_path: Path) -> None:
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
                    "photo_block_apply",
                    "block-apply-card.jpg",
                    "data/photos/test/block-apply-card.jpg",
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
                    "parse_block_apply",
                    "photo_block_apply",
                    "manual_photo_transcription",
                    "{}",
                    "2026-05-09T00:00:01Z",
                    "review",
                    72,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value,
                     suggested_value, review_reason, status, created_at, resolved_at, resolution_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_block_apply",
                    "parse_block_apply",
                    "Medium",
                    "Evidence comparison resolved",
                    "318 R0",
                    "{}",
                    "Reviewer resolved only the broad transcription item.",
                    "resolved",
                    "2026-05-09T00:00:02Z",
                    "2026-05-09T00:00:03Z",
                    "Accepted broad item.",
                ),
            )
            conn.execute(
                """
                INSERT INTO canonical_candidate
                    (candidate_id, review_id, parse_id, proposed_mouse_display_id,
                     proposed_strain, proposed_dob, proposed_count, candidate_payload,
                     status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "candidate_block_apply",
                    "review_block_apply",
                    "parse_block_apply",
                    "318",
                    "ApoM Tg/Tg",
                    "2026-04-01",
                    "1",
                    json.dumps({"display_id": "318", "strain": "ApoM Tg/Tg", "dob": "2026-04-01"}),
                    "draft",
                    "2026-05-09T00:00:04Z",
                    "2026-05-09T00:00:04Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO card_note_item_log
                    (note_item_id, photo_id, parse_id, card_type, line_number,
                     raw_line_text, strike_status, parsed_type, interpreted_status,
                     parsed_mouse_display_id, parsed_ear_label_raw,
                     parsed_ear_label_confidence, parsed_ear_label_review_status,
                     confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "note_block_apply",
                    "photo_block_apply",
                    "parse_block_apply",
                    "Separated",
                    1,
                    "318 R0",
                    "none",
                    "mouse_item",
                    "active",
                    "318",
                    "R0",
                    60,
                    "needs_review",
                    60,
                    1,
                ),
            )

            preview = canonical_candidate_apply_preview(conn, "candidate_block_apply")

        assert preview["blocked"] is True
        assert "All note-line review items must be resolved before applying." in preview["blockers"]
        assert "Each canonical apply row must have note-line photo evidence." in preview["blockers"]

        with pytest.raises(HTTPException) as exc_info:
            apply_canonical_candidate("candidate_block_apply")

        assert exc_info.value.status_code == 409
        with db.connection() as conn:
            assert conn.execute("SELECT COUNT(*) AS count FROM mouse_master").fetchone()["count"] == 0
            assert conn.execute("SELECT COUNT(*) AS count FROM mouse_event").fetchone()["count"] == 0
    finally:
        db.DB_PATH = old_db_path
