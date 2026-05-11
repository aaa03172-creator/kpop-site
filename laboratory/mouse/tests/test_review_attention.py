from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from app import db
from app.main import (
    CorrectionCreate,
    ReviewResolutionCreate,
    create_correction,
    create_card_snapshot,
    export_review_blocker_count,
    list_review_items,
    list_note_items,
    open_review_attention_counts,
    open_review_blockers,
    parse_note_line,
    resolve_review_item,
    review_check_targets,
    review_attention_level,
    ui_action_log,
    write_note_items_and_mouse_candidates,
)


def seed_numeric_note_parse(tmp_path: Path, parse_suffix: str, notes: list[dict[str, str]]) -> tuple[str, str]:
    parse_id = f"parse_numeric_{parse_suffix}"
    photo_id = f"photo_numeric_{parse_suffix}"
    record = {
        "type": "Separated",
        "sourcePhotoId": photo_id,
        "notes": notes,
    }
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
                photo_id,
                f"{parse_suffix}-card.jpg",
                f"data/photos/test/{parse_suffix}-card.jpg",
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
                parse_id,
                photo_id,
                "manual_photo_transcription",
                json.dumps(record, ensure_ascii=False),
                "2026-05-04T00:00:00Z",
                "review",
                70,
                1,
            ),
        )
        snapshot_id = create_card_snapshot(conn, parse_id, photo_id, record, "2026-05-04T00:00:00Z")
        write_note_items_and_mouse_candidates(
            conn,
            parse_id,
            {**record, "cardSnapshotId": snapshot_id},
            "review",
        )
    return parse_id, snapshot_id


def test_ui_action_log_filters_and_parses_action_values(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO action_log
                    (action_id, action_type, target_id, before_value, after_value,
                     performed_by, performed_role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "action_review_target",
                    "correction_recorded",
                    "mouse_001",
                    json.dumps({"status": "review"}, ensure_ascii=False),
                    json.dumps({"status": "accepted"}, ensure_ascii=False),
                    "local_user",
                    "reviewer",
                    "2026-05-09T00:01:00Z",
                    "action_other_target",
                    "cage_created",
                    "cage_001",
                    "",
                    json.dumps({"cage_label": "A1"}, ensure_ascii=False),
                    "local_user",
                    "reviewer",
                    "2026-05-09T00:00:00Z",
                ),
            )

        result = ui_action_log(target_id="mouse_001", limit=500)

        assert result["source_layer"] == "export or view"
        assert result["filters"] == {
            "target_id": "mouse_001",
            "action_type": "",
            "limit": 200,
        }
        assert result["summary"]["returned_actions"] == 1
        assert result["action_types"] == [
            {"action_type": "cage_created", "count": 1},
            {"action_type": "correction_recorded", "count": 1},
        ]
        [action] = result["actions"]
        assert action["action_id"] == "action_review_target"
        assert action["before"] == {"status": "review"}
        assert action["after"] == {"status": "accepted"}
    finally:
        db.DB_PATH = old_db_path


def test_correction_empty_source_record_does_not_create_orphan_source(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()

        result = create_correction(
            CorrectionCreate(
                entity_type="mouse",
                entity_id="MT401",
                field_name="sex",
                before_value="unknown",
                after_value="female",
                reason="Reviewed source evidence; no source record selected.",
                source_record_id="",
                review_id="",
            )
        )

        with db.connection() as conn:
            correction = conn.execute(
                """
                SELECT source_record_id, review_id
                FROM correction_log
                WHERE correction_id = ?
                """,
                (result["correction_id"],),
            ).fetchone()
        assert correction["source_record_id"] is None
        assert correction["review_id"] is None
    finally:
        db.DB_PATH = old_db_path


def test_correction_preserves_before_after_with_evidence_context(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()
        with db.connection() as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(correction_log)").fetchall()
            }
            assert "source_layer" in columns
            assert "evidence_reference_json" in columns
            assert "correction_context_json" in columns
            conn.execute(
                """
                INSERT INTO source_record
                    (source_record_id, source_type, source_uri, source_label,
                     raw_payload, imported_at, checksum, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "source_correction_context",
                    "photo",
                    "data/photos/test/correction-context.jpg",
                    "correction-context.jpg",
                    "{}",
                    "2026-05-09T00:00:00Z",
                    "checksum",
                    "",
                ),
            )
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "parse_correction_context",
                    None,
                    "manual_photo_transcription",
                    "{}",
                    "2026-05-09T00:00:00Z",
                    "review",
                    60,
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
                    "review_correction_context",
                    "parse_correction_context",
                    "Medium",
                    "Correction review",
                    "unknown",
                    "female",
                    "Reviewer corrected the parsed value.",
                    "open",
                    "2026-05-09T00:00:01Z",
                ),
            )

        result = create_correction(
            CorrectionCreate(
                entity_type="mouse",
                entity_id="MT401",
                field_name="sex",
                before_value="unknown",
                after_value="female",
                reason="Reviewed source photo and corrected parsed sex.",
                source_record_id="source_correction_context",
                review_id="review_correction_context",
            )
        )

        with db.connection() as conn:
            correction = conn.execute(
                """
                SELECT source_layer, before_value, after_value,
                       evidence_reference_json, correction_context_json
                FROM correction_log
                WHERE correction_id = ?
                """,
                (result["correction_id"],),
            ).fetchone()

        evidence_reference = json.loads(correction["evidence_reference_json"])
        correction_context = json.loads(correction["correction_context_json"])
        assert correction["source_layer"] == "review item"
        assert correction["before_value"] == "unknown"
        assert correction["after_value"] == "female"
        assert evidence_reference["source_record_id"] == "source_correction_context"
        assert evidence_reference["review_id"] == "review_correction_context"
        assert correction_context["before_value"] == "unknown"
        assert correction_context["after_value"] == "female"
        assert correction_context["field_name"] == "sex"
    finally:
        db.DB_PATH = old_db_path


def test_correction_rejects_missing_source_record_without_partial_write(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()

        with pytest.raises(HTTPException) as exc_info:
            create_correction(
                CorrectionCreate(
                    entity_type="mouse",
                    entity_id="MT401",
                    field_name="sex",
                    before_value="unknown",
                    after_value="female",
                    reason="Reviewed source evidence.",
                    source_record_id="source_missing",
                )
            )

        assert exc_info.value.status_code == 400
        with db.connection() as conn:
            correction_count = conn.execute("SELECT COUNT(*) AS count FROM correction_log").fetchone()["count"]
            action_count = conn.execute("SELECT COUNT(*) AS count FROM action_log").fetchone()["count"]
        assert correction_count == 0
        assert action_count == 0
    finally:
        db.DB_PATH = old_db_path


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


def test_card_snapshot_keeps_raw_and_selected_normalized_sex_separate(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "parse_selected_sex",
                    None,
                    "manual_photo_transcription",
                    json.dumps({"sexRaw": "unclear symbol", "sexNormalized": "female"}, ensure_ascii=False),
                    "2026-05-04T00:00:00Z",
                    "review",
                    70,
                    1,
                ),
            )
            snapshot_id = create_card_snapshot(
                conn,
                "parse_selected_sex",
                None,
                {
                    "type": "Separated",
                    "rawStrain": "ApoM Tg/Tg",
                    "matchedStrain": "ApoM Tg/Tg",
                    "sexRaw": "unclear symbol",
                    "sexNormalized": "female",
                    "notes": [],
                },
                "2026-05-04T00:00:00Z",
            )
            snapshot = conn.execute(
                "SELECT sex_raw, sex_normalized FROM card_snapshot WHERE card_snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()

        assert snapshot["sex_raw"] == "unclear symbol"
        assert snapshot["sex_normalized"] == "female"
    finally:
        db.DB_PATH = old_db_path


def test_impossible_ear_label_token_stays_reviewable() -> None:
    parsed = parse_note_line("318 RWM", "Separated")

    assert parsed["parsed_type"] == "mouse_item"
    assert parsed["parsed_mouse_display_id"] == "318"
    assert parsed["parsed_ear_label_raw"] == "RWM"
    assert parsed["parsed_ear_label_code"] is None
    assert parsed["parsed_ear_label_review_status"] == "needs_review"
    assert parsed["needs_review"] == 1
    assert "Unexpected ear-label mark" in parsed["parsed_metadata"]["ear_label_issue"]


def test_note_item_display_marks_impossible_ear_label_as_review(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        parse_id, _ = seed_numeric_note_parse(tmp_path, "bad_ear", [{"raw": "318 RWM", "strike": "single"}])

        [note] = [
            item
            for item in list_note_items()
            if item["parse_id"] == parse_id and item["raw_line_text"] == "318 RWM"
        ]

        assert note["raw_line_text"] == "318 RWM"
        assert note["display_value"] == "318 [ear label review: RWM]"
        assert note["parsed_ear_label_review_status"] == "needs_review"
        assert note["parsed_metadata"]["ear_label_raw"] == "RWM"
    finally:
        db.DB_PATH = old_db_path


def test_resolving_ear_label_review_updates_note_without_overwriting_raw(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        parse_id, _ = seed_numeric_note_parse(tmp_path, "ear_resolve", [{"raw": "318 RWM", "strike": "single"}])
        note_item_id = f"note_{parse_id}_1"

        result = resolve_review_item(
            f"review_ear_{note_item_id}",
            ReviewResolutionCreate(
                resolution_note="Checked the source photo; the visible ear mark is R prime.",
                resolved_value="R_PRIME",
                note_item_id=note_item_id,
                ear_label_code="R_PRIME",
            ),
        )

        with db.connection() as conn:
            note = conn.execute(
                """
                SELECT raw_line_text, parsed_ear_label_raw, parsed_ear_label_code,
                       parsed_ear_label_review_status, needs_review
                FROM card_note_item_log
                WHERE note_item_id = ?
                """,
                (note_item_id,),
            ).fetchone()
            action = conn.execute(
                """
                SELECT action_type, after_value
                FROM action_log
                WHERE action_type = 'ear_label_reviewed'
                  AND target_id = ?
                """,
                (note_item_id,),
            ).fetchone()

        assert result["ear_label_update"]["ear_label_code"] == "R_PRIME"
        assert note["raw_line_text"] == "318 RWM"
        assert note["parsed_ear_label_raw"] == "RWM"
        assert note["parsed_ear_label_code"] == "R_PRIME"
        assert note["parsed_ear_label_review_status"] == "user_corrected"
        assert note["needs_review"] == 0
        assert action["action_type"] == "ear_label_reviewed"
    finally:
        db.DB_PATH = old_db_path


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


def test_review_attention_escalates_high_plausibility_warning() -> None:
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
            "confidence": 92,
            "rawStrain": "ApoM Tg/Tg",
            "sexRaw": "6",
            "uncertainFields": ["sex_raw"],
            "plausibilityFindings": [
                {
                    "field": "sex_raw",
                    "severity": "high",
                    "message": "Sex field contains digits without a sex symbol or sex word.",
                }
            ],
        },
    )

    assert result["attention_level"] == "must_review"
    assert "Plausibility check" in result["attention_reason"]


def test_review_items_api_exposes_plausibility_findings(tmp_path: Path) -> None:
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
                    "photo_plausibility",
                    "plausibility-card.jpg",
                    "data/photos/test/plausibility-card.jpg",
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
                    "parse_plausibility",
                    "photo_plausibility",
                    "ai_photo_extraction",
                    json.dumps(
                        {
                            "confidence": 92,
                            "rawStrain": "ApoM Tg/Tg",
                            "sexRaw": "6",
                            "uncertainFields": ["sex_raw", "mouse_count"],
                            "plausibilityFindings": [
                                {
                                    "field": "sex_raw",
                                    "severity": "high",
                                    "message": "Sex field contains digits without a sex symbol or sex word.",
                                }
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    "2026-05-04T00:00:00Z",
                    "review",
                    92,
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
                    "review_plausibility",
                    "parse_plausibility",
                    "Medium",
                    "AI-extracted photo transcription needs review",
                    "6",
                    "Check sex/count field.",
                    "AI photo extraction must remain reviewable before canonical writes.",
                    "open",
                    "2026-05-04T00:00:01Z",
                ),
            )

        [item] = list_review_items()

        assert item["attention_level"] == "must_review"
        assert item["review_plausibility_findings"] == [
            {
                "field": "sex_raw",
                "severity": "high",
                "message": "Sex field contains digits without a sex symbol or sex word.",
            }
        ]
        assert item["review_check_targets"][:3] == ["Plausibility warning", "Sex/count field", "Mouse count"]
    finally:
        db.DB_PATH = old_db_path


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


def test_review_check_targets_summarize_focus_fields() -> None:
    targets = review_check_targets(
        {
            "status": "open",
            "issue": "AI-extracted photo transcription needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
        },
        {
            "confidence": 52,
            "rawStrain": "",
            "sexRaw": "female",
            "uncertain_fields": ["matched_strain", "mouse_count", "dob_raw"],
        },
    )

    assert targets == [
        "Low OCR confidence",
        "Strain field",
        "Assigned strain match",
        "Mouse count",
        "DOB",
    ]


def test_review_check_targets_include_plausibility_warning() -> None:
    targets = review_check_targets(
        {
            "status": "open",
            "issue": "AI-extracted photo transcription needs review",
            "source_name": "ai_photo_extraction",
            "photo_id": "photo_1",
            "priority": "medium",
            "severity": "Medium",
        },
        {
            "confidence": 90,
            "rawStrain": "ApoM Tg/Tg",
            "sexRaw": "6",
            "uncertainFields": ["sex_raw", "mouse_count"],
            "plausibilityFindings": [
                {
                    "field": "sex_raw",
                    "severity": "high",
                    "message": "Sex field contains digits without a sex symbol or sex word.",
                }
            ],
        },
    )

    assert targets[:3] == ["Plausibility warning", "Sex/count field", "Mouse count"]


def test_review_check_targets_include_legacy_strain_registry_focus() -> None:
    targets = review_check_targets(
        {
            "status": "open",
            "issue": "Legacy strain registry candidate requires review",
            "source_name": "legacy_workbook_import",
            "priority": "medium",
            "severity": "Medium",
        }
    )

    assert targets == [
        "Strain registry",
        "Raw strain/genotype",
        "Gene/allele link",
        "Workbook row evidence",
    ]


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
        assert "Low OCR confidence" in item["review_check_targets"]
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
        assert "Low OCR confidence" in blockers[0]["review_check_targets"]
        assert counts["must_review"] == 1
        assert counts["quick_check"] == 1
        assert blocker_count == 1
    finally:
        db.DB_PATH = old_db_path


def test_numeric_note_reviews_are_grouped_by_parse(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        parse_id, _ = seed_numeric_note_parse(tmp_path, "group", [{"raw": "1"}, {"raw": "2"}, {"raw": "3"}])
        with db.connection() as conn:
            reviews = conn.execute(
                """
                SELECT review_id, current_value, suggested_value, review_reason
                FROM review_queue
                WHERE issue = 'Unlabeled numeric note needs review'
                ORDER BY review_id
                """
            ).fetchall()
            note_items = conn.execute(
                """
                SELECT raw_line_text, parsed_type
                FROM card_note_item_log
                WHERE parse_id = ?
                ORDER BY line_number
                """,
                (parse_id,),
            ).fetchall()

        assert len(reviews) == 1
        assert reviews[0]["review_id"] == f"review_unlabeled_numeric_{parse_id}"
        assert reviews[0]["current_value"] == "1, 2, 3"
        assert "3 numeric-only note lines" in reviews[0]["review_reason"]
        assert [row["raw_line_text"] for row in note_items] == ["1", "2", "3"]
        assert {row["parsed_type"] for row in note_items} == {"unlabeled_numeric_note"}
    finally:
        db.DB_PATH = old_db_path


def test_multi_label_numeric_note_line_uses_grouped_review_contract(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        parse_id, _ = seed_numeric_note_parse(tmp_path, "line", [{"raw": "1 2 3"}])
        with db.connection() as conn:
            [review] = conn.execute(
                """
                SELECT review_id, current_value, review_reason
                FROM review_queue
                WHERE issue = 'Unlabeled numeric note needs review'
                """
            ).fetchall()

        assert review["review_id"] == f"review_unlabeled_numeric_{parse_id}"
        assert review["current_value"] == "1, 2, 3"
        assert "numeric-only note lines" in review["review_reason"]
    finally:
        db.DB_PATH = old_db_path


def test_resolving_grouped_numeric_note_review_updates_all_numeric_notes(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        parse_id, snapshot_id = seed_numeric_note_parse(tmp_path, "resolve", [{"raw": "1"}, {"raw": "2"}, {"raw": "3"}])
        with db.connection() as conn:
            first_note_id = conn.execute(
                """
                SELECT note_item_id
                FROM card_note_item_log
                WHERE parse_id = ?
                ORDER BY line_number
                LIMIT 1
                """,
                (parse_id,),
            ).fetchone()["note_item_id"]

        result = resolve_review_item(
            f"review_unlabeled_numeric_{parse_id}",
            ReviewResolutionCreate(
                resolution_note="Confirmed grouped numeric-only labels as reviewed count notes.",
                resolved_value="3 temporary labels",
                note_item_id=first_note_id,
                note_label_decision="count_note",
                note_label_count=3,
            ),
        )

        with db.connection() as conn:
            rows = conn.execute(
                """
                SELECT raw_line_text, parsed_type, parsed_count, needs_review
                FROM card_note_item_log
                WHERE parse_id = ?
                ORDER BY line_number
                """,
                (parse_id,),
            ).fetchall()
            snapshot = conn.execute(
                "SELECT note_summary_json FROM card_snapshot WHERE card_snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
        review_after_resolution = next(
            item for item in list_review_items()
            if item["review_id"] == f"review_unlabeled_numeric_{parse_id}"
        )

        assert result["status"] == "resolved"
        assert [row["parsed_type"] for row in rows] == ["count_note", "count_note", "count_note"]
        assert [row["parsed_count"] for row in rows] == [1, 1, 1]
        assert [row["needs_review"] for row in rows] == [0, 0, 0]
        summary = json.loads(snapshot["note_summary_json"])
        assert summary["count_note_total"] == 3
        assert summary["needs_review_count"] == 0
        assert review_after_resolution["note_item_id"] == f"note_{parse_id}_1"
        assert review_after_resolution["review_note_raw_line"] == "1"
    finally:
        db.DB_PATH = old_db_path


def test_grouped_numeric_note_review_requires_label_decision(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        parse_id, _ = seed_numeric_note_parse(tmp_path, "requires_decision", [{"raw": "1"}, {"raw": "2"}])

        with pytest.raises(HTTPException) as exc_info:
            resolve_review_item(
                f"review_unlabeled_numeric_{parse_id}",
                ReviewResolutionCreate(
                    resolution_note="Resolve without classifying numeric evidence.",
                    resolved_value="reviewed",
                    note_item_id=f"note_{parse_id}_1",
                ),
            )

        with db.connection() as conn:
            review = conn.execute(
                "SELECT status FROM review_queue WHERE review_id = ?",
                (f"review_unlabeled_numeric_{parse_id}",),
            ).fetchone()
            remaining_review_notes = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM card_note_item_log
                WHERE parse_id = ?
                  AND parsed_type = 'unlabeled_numeric_note'
                  AND needs_review = 1
                """,
                (parse_id,),
            ).fetchone()

        assert exc_info.value.status_code == 400
        assert "note_label_decision" in exc_info.value.detail
        assert review["status"] == "open"
        assert remaining_review_notes["count"] == 2
    finally:
        db.DB_PATH = old_db_path


def test_grouped_numeric_note_review_resolve_falls_back_to_first_note_anchor(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        parse_id, _ = seed_numeric_note_parse(tmp_path, "fallback", [{"raw": "1"}, {"raw": "2"}])

        result = resolve_review_item(
            f"review_unlabeled_numeric_{parse_id}",
            ReviewResolutionCreate(
                resolution_note="Confirmed grouped numeric-only labels without explicit note anchor.",
                resolved_value="2 temporary labels",
                note_label_decision="count_note",
            ),
        )

        assert result["note_label_update"]["grouped_note_item_ids"] == [
            f"note_{parse_id}_1",
            f"note_{parse_id}_2",
        ]
    finally:
        db.DB_PATH = old_db_path
