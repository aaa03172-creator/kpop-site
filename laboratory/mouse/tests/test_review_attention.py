from __future__ import annotations

import json
from pathlib import Path

from app import db
from app.main import (
    export_review_blocker_count,
    list_review_items,
    open_review_attention_counts,
    open_review_blockers,
    review_attention_level,
)


def test_review_attention_hides_fixture_reviews_by_default() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "Outside assigned strain scope",
            "source_name": "fixtures/sample_parse_results.json",
            "priority": "medium",
            "severity": "Medium",
        },
        {"confidence": 94, "rawStrain": "ApoM Tg/Tg", "sexRaw": "male"},
    )

    assert result["attention_level"] == "hidden_default"


def test_review_attention_focuses_missing_core_photo_fields() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "AI-extracted photo transcription needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
        },
        {"confidence": 74, "rawStrain": "", "sexRaw": "female"},
    )

    assert result["attention_level"] == "must_review"


def test_review_attention_keeps_low_risk_photo_as_trace_only() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "AI-extracted photo transcription needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
        },
        {
            "confidence": 78,
            "rawStrain": "ApoM Tg/Tg",
            "matchedStrain": "ApoMtg/tg",
            "sexRaw": "female 8",
            "uncertainFields": ["dob_normalized", "lmo_raw"],
        },
    )

    assert result["attention_level"] == "trace_only"


def test_review_attention_groups_numeric_note_as_quick_check() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "Unlabeled numeric note needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
        },
        {"confidence": 78, "rawStrain": "ApoM Tg/Tg", "sexRaw": "female"},
    )

    assert result["attention_level"] == "quick_check"


def test_review_attention_normalizes_uncertain_field_aliases() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "AI-extracted photo transcription needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
        },
        {
            "confidence": 58,
            "rawStrain": "ApoM Tg/Tg",
            "sexRaw": "female",
            "uncertainFields": ["matchedStrain"],
        },
    )

    assert result["attention_level"] == "must_review"


def test_review_attention_reads_snake_case_uncertain_fields() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "AI-extracted photo transcription needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
        },
        {
            "confidence": 58,
            "rawStrain": "ApoM Tg/Tg",
            "sexRaw": "female",
            "uncertain_fields": ["matched_strain"],
        },
    )

    assert result["attention_level"] == "must_review"


def test_review_attention_preserves_zero_payload_confidence() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "AI-extracted photo transcription needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
            "confidence": 95,
        },
        {
            "confidence": 0,
            "rawStrain": "ApoM Tg/Tg",
            "sexRaw": "female",
        },
    )

    assert result["attention_level"] == "must_review"


def test_review_attention_treats_high_priority_case_insensitively() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "Manual photo transcription needs review",
            "source_name": "manual_photo_transcription",
            "priority": "High",
            "severity": "medium",
        },
        {},
    )

    assert result["attention_level"] == "must_review"


def test_review_attention_treats_high_severity_case_insensitively() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "Manual photo transcription needs review",
            "source_name": "manual_photo_transcription",
            "priority": "medium",
            "severity": "high",
        },
        {},
    )

    assert result["attention_level"] == "must_review"


def test_review_attention_treats_open_status_case_insensitively() -> None:
    result = review_attention_level(
        {
            "status": "Open",
            "issue": "AI-extracted photo transcription needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
        },
        {"confidence": 40, "rawStrain": "ApoM Tg/Tg", "sexRaw": "female"},
    )

    assert result["attention_level"] == "must_review"


def test_review_attention_treats_known_issue_labels_case_insensitively() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "ai-extracted photo transcription needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
        },
        {"confidence": 40, "rawStrain": "ApoM Tg/Tg", "sexRaw": "female"},
    )

    assert result["attention_level"] == "must_review"


def test_review_attention_hides_fixture_source_case_insensitively() -> None:
    result = review_attention_level(
        {
            "status": "open",
            "issue": "Outside assigned strain scope",
            "source_name": "Fixtures/sample_parse_results.json",
            "priority": "medium",
            "severity": "Medium",
        },
        {"confidence": 94, "rawStrain": "ApoM Tg/Tg", "sexRaw": "male"},
    )

    assert result["attention_level"] == "hidden_default"


def test_review_items_api_includes_attention_contract(tmp_path: Path) -> None:
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
                    "photo_attention",
                    "attention-card.jpg",
                    "data/photos/test/attention-card.jpg",
                    "2026-05-04T00:00:00Z",
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
                    "parse_attention",
                    "photo_attention",
                    "ai_photo_extraction",
                    json.dumps(
                        {
                            "confidence": 0,
                            "rawStrain": "ApoM Tg/Tg",
                            "sexRaw": "female",
                            "uncertainFields": [],
                        },
                        ensure_ascii=False,
                    ),
                    "2026-05-04T00:00:00Z",
                    "review",
                    95,
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
                    "review_attention",
                    "parse_attention",
                    "Medium",
                    "AI-extracted photo transcription needs review",
                    "photo_attention",
                    "Review low-confidence OCR draft.",
                    "AI photo extraction must remain reviewable before canonical writes.",
                    "open",
                    "2026-05-04T00:00:01Z",
                ),
            )

        [item] = list_review_items()

        assert item["attention_level"] == "must_review"
        assert item["attention_reason"]
        assert item["confidence"] == 95
        assert "parse_raw_payload" not in item
        assert "parse_confidence" not in item
    finally:
        db.DB_PATH = old_db_path


def test_export_blockers_include_only_focus_review_items(tmp_path: Path) -> None:
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
                    "photo_focus",
                    "focus-card.jpg",
                    "data/photos/test/focus-card.jpg",
                    "2026-05-04T00:00:00Z",
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
                    "parse_quick",
                    "photo_focus",
                    "ai_photo_extraction",
                    json.dumps({"confidence": 78, "rawStrain": "ApoM Tg/Tg", "sexRaw": "female"}, ensure_ascii=False),
                    "2026-05-04T00:00:00Z",
                    "review",
                    78,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "parse_focus",
                    "photo_focus",
                    "ai_photo_extraction",
                    json.dumps({"confidence": 40, "rawStrain": "", "sexRaw": ""}, ensure_ascii=False),
                    "2026-05-04T00:00:00Z",
                    "review",
                    40,
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
                    "review_quick",
                    "parse_quick",
                    "Medium",
                    "Unlabeled numeric note needs review",
                    "7",
                    "7",
                    "Numeric note can be grouped as a quick check.",
                    "open",
                    "2026-05-04T00:00:01Z",
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
                    "review_focus",
                    "parse_focus",
                    "Medium",
                    "AI-extracted photo transcription needs review",
                    "photo",
                    "Review low-confidence OCR draft.",
                    "Low-confidence OCR draft needs focused review.",
                    "open",
                    "2026-05-04T00:00:02Z",
                ),
            )

            blockers = open_review_blockers(conn)
            counts = open_review_attention_counts(conn)
            blocker_count = export_review_blocker_count(conn)

        assert [item["review_id"] for item in blockers] == ["review_focus"]
        assert blockers[0]["attention_level"] == "must_review"
        assert counts["must_review"] == 1
        assert counts["quick_check"] == 1
        assert blocker_count == 1
    finally:
        db.DB_PATH = old_db_path
