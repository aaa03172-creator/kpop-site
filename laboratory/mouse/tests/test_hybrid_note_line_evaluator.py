from __future__ import annotations

import json

from app.hybrid_note_line_evaluator import (
    build_rule_snapshot,
    evaluate_note_line_candidate,
)
from app import db
from app.main import create_card_snapshot, parse_note_line, write_note_items_and_mouse_candidates


def parsed(raw_line: str, card_type: str = "separated") -> dict:
    result = parse_note_line(raw_line, card_type)
    result["raw_line_text"] = raw_line
    result["photo_id"] = "photo_test"
    result["parse_id"] = "parse_test"
    result["note_item_id"] = "note_parse_test_1"
    result["line_number"] = 1
    result["card_snapshot_id"] = "snapshot_test"
    result["roi_ref"] = "note_block:1"
    return result


def test_rule_snapshot_hash_is_stable_and_uses_declared_fields() -> None:
    first = build_rule_snapshot(
        {
            "display_name": "ApoM Tg/Tg 2026-05-06",
            "rule_set_id": "label_rule_apom_tgtg_20260506",
            "session_date": "2026-05-06",
            "crossed_out_handling": "dead",
            "ear_label_sequence": ["R_PRIME", "L_PRIME"],
            "sample_mapping": "sample_id_equals_mouse_display_id",
            "genotyping_target": "ApoM-tg",
            "ignored_ui_label": "not part of the evaluator contract",
        }
    )
    second = build_rule_snapshot(
        {
            "genotyping_target": "ApoM-tg",
            "sample_mapping": "sample_id_equals_mouse_display_id",
            "ear_label_sequence": ["R_PRIME", "L_PRIME"],
            "crossed_out_handling": "dead",
            "session_date": "2026-05-06",
            "rule_set_id": "label_rule_apom_tgtg_20260506",
            "display_name": "ApoM Tg/Tg 2026-05-06",
            "ignored_ui_label": "changed but outside stable hash input",
        }
    )

    assert first["rule_hash"] == second["rule_hash"]
    assert first["hash_input_fields"] == [
        "rule_set_id",
        "display_name",
        "session_date",
        "effective_from",
        "crossed_out_handling",
        "ear_label_sequence",
        "sample_mapping",
        "genotyping_target",
    ]
    assert first["display_name"] == "ApoM Tg/Tg 2026-05-06"


def test_exact_ocr_ai_agreement_with_rule_consistency_routes_to_quick_check() -> None:
    result = evaluate_note_line_candidate(
        ocr_candidate={"raw_line_text": "101 R'", "confidence": 0.91},
        ai_candidate={"raw_line_text": "101 R'", "confidence": 0.93},
        parsed_note_row=parsed("101 R'"),
        source_quality={
            "source_image_quality": "acceptable",
            "roi_alignment_confidence": 0.86,
            "line_segmentation_confidence": 0.84,
        },
        rule_context={
            "rule_set_id": "label_rule_apom_tgtg_20260506",
            "display_name": "ApoM Tg/Tg 2026-05-06",
            "session_date": "2026-05-06",
            "crossed_out_handling": "dead",
            "ear_label_sequence": ["R_PRIME", "L_PRIME"],
            "expected_ear_label_code": "R_PRIME",
        },
    )

    assert result["candidate_kind"] == "hybrid_note_line"
    assert result["hybrid_candidate"]["raw_line_text"] == "101 R'"
    assert result["hybrid_candidate"]["parsed_mouse_display_id"] == "101"
    assert result["hybrid_candidate"]["parsed_ear_label_code"] == "R_PRIME"
    assert result["review_routing"]["attention_level"] == "quick_check"
    assert result["review_routing"]["must_review"] is False
    assert result["applied_rule_keys"] == [
        "ocr_ai_exact_note_line_agreement",
        "rule_consistency_expected_ear_label_sequence",
    ]
    assert result["conflicts"] == []
    assert result["rule_candidate"]["rule_interpretation_candidate"] == "active"


def test_rule_mismatch_never_overrides_visible_ear_label() -> None:
    result = evaluate_note_line_candidate(
        ocr_candidate={"raw_line_text": "101 L'", "confidence": 0.9},
        ai_candidate={"raw_line_text": "101 L'", "confidence": 0.92},
        parsed_note_row=parsed("101 L'"),
        source_quality={
            "source_image_quality": "acceptable",
            "roi_alignment_confidence": 0.9,
            "line_segmentation_confidence": 0.9,
        },
        rule_context={
            "rule_set_id": "label_rule_apom_tgtg_20260506",
            "display_name": "ApoM Tg/Tg 2026-05-06",
            "session_date": "2026-05-06",
            "crossed_out_handling": "dead",
            "ear_label_sequence": ["R_PRIME", "L_PRIME"],
            "expected_ear_label_code": "R_PRIME",
        },
    )

    assert result["hybrid_candidate"]["parsed_ear_label_code"] == "L_PRIME"
    assert result["rule_candidate"]["expected_ear_label_code"] == "R_PRIME"
    assert result["review_routing"]["must_review"] is True
    assert "rule_expected_ear_label_mismatch" in result["conflicts"]


def test_ocr_ai_disagreement_and_weak_source_quality_force_review() -> None:
    result = evaluate_note_line_candidate(
        ocr_candidate={"raw_line_text": "101 R'", "confidence": 0.78},
        ai_candidate={"raw_line_text": "101 L'", "confidence": 0.82},
        parsed_note_row=parsed("101 R'"),
        source_quality={
            "source_image_quality": "poor",
            "roi_alignment_confidence": 0.42,
            "line_segmentation_confidence": 0.48,
            "quality_flags": ["cropped_note_block"],
        },
    )

    assert result["review_routing"]["attention_level"] == "must_review"
    assert result["review_routing"]["must_review"] is True
    assert "ocr_ai_note_line_disagreement" in result["conflicts"]
    assert "weak_source_or_roi_quality" in result["conflicts"]


def test_ocr_ai_identity_disagreement_for_same_raw_line_forces_review() -> None:
    result = evaluate_note_line_candidate(
        ocr_candidate={
            "raw_line_text": "101 R'",
            "parsed_mouse_display_id": "101",
            "parsed_ear_label_code": "R_PRIME",
            "strike_status": "none",
            "confidence": 0.91,
        },
        ai_candidate={
            "raw_line_text": "101 R'",
            "parsed_mouse_display_id": "102",
            "parsed_ear_label_code": "L_PRIME",
            "strike_status": "single",
            "confidence": 0.93,
        },
        parsed_note_row=parsed("101 R'"),
        source_quality={
            "source_image_quality": "acceptable",
            "roi_alignment_confidence": 0.9,
            "line_segmentation_confidence": 0.9,
        },
    )

    assert result["review_routing"]["attention_level"] == "must_review"
    assert "ocr_ai_mouse_id_disagreement" in result["conflicts"]
    assert "ocr_ai_ear_label_disagreement" in result["conflicts"]
    assert "ocr_ai_strike_status_disagreement" in result["conflicts"]


def test_missing_source_refs_force_review_even_when_candidates_agree() -> None:
    parsed_without_refs = parse_note_line("101 R'", "separated")
    parsed_without_refs["raw_line_text"] = "101 R'"

    result = evaluate_note_line_candidate(
        ocr_candidate={"raw_line_text": "101 R'", "confidence": 0.91},
        ai_candidate={"raw_line_text": "101 R'", "confidence": 0.93},
        parsed_note_row=parsed_without_refs,
        source_quality={
            "source_image_quality": "acceptable",
            "roi_alignment_confidence": 0.9,
            "line_segmentation_confidence": 0.9,
        },
    )

    assert result["review_routing"]["attention_level"] == "must_review"
    assert "missing_source_trace" in result["conflicts"]


def test_malformed_candidate_payload_routes_to_review_without_preserving_extra_fields() -> None:
    result = evaluate_note_line_candidate(
        ocr_candidate="garbled local ocr payload",
        ai_candidate={
            "raw_line_text": "101 R'",
            "confidence": 0.93,
            "full_prompt": "do not persist bulky or private prompt context",
        },
        parsed_note_row=parsed("101 R'"),
        source_quality=["not a source-quality dict"],
    )

    assert result["review_routing"]["attention_level"] == "must_review"
    assert "malformed_ocr_candidate" in result["conflicts"]
    assert "malformed_source_quality" in result["conflicts"]
    assert "full_prompt" not in result["ai_candidate"]


def test_numeric_only_note_lines_remain_reviewable() -> None:
    result = evaluate_note_line_candidate(
        ocr_candidate={"raw_line_text": "1 2 3", "confidence": 0.94},
        ai_candidate={"raw_line_text": "1 2 3", "confidence": 0.95},
        parsed_note_row=parsed("1 2 3"),
        source_quality={
            "source_image_quality": "acceptable",
            "roi_alignment_confidence": 0.9,
            "line_segmentation_confidence": 0.9,
        },
    )

    assert result["hybrid_candidate"]["parsed_type"] == "unlabeled_numeric_note"
    assert result["review_routing"]["attention_level"] == "must_review"
    assert result["review_routing"]["must_review"] is True
    assert "numeric_only_note_line" in result["conflicts"]


def test_writer_attaches_hybrid_evaluator_metadata_without_replacing_raw_note(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        photo_id = "photo_hybrid_eval"
        parse_id = "parse_hybrid_eval"
        record = {
            "type": "Separated",
            "sourcePhotoId": photo_id,
            "labelingRuleSetId": "label_rule_apom_tgtg_20260506",
            "notes": [
                {
                    "raw": "101 L'",
                    "ocrCandidate": {"raw_line_text": "101 L'", "confidence": 0.91},
                    "aiCandidate": {"raw_line_text": "101 L'", "confidence": 0.93},
                    "sourceQuality": {
                        "source_image_quality": "acceptable",
                        "roi_alignment_confidence": 0.9,
                        "line_segmentation_confidence": 0.9,
                    },
                    "roiRef": "note_block:1",
                }
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
                    "hybrid.jpg",
                    "data/photos/test/hybrid.jpg",
                    "2026-05-06T00:00:00Z",
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
                    "{}",
                    "2026-05-06T00:00:00Z",
                    "review",
                    90,
                    1,
                ),
            )
            snapshot_id = create_card_snapshot(conn, parse_id, photo_id, record, "2026-05-06T00:00:00Z")
            write_note_items_and_mouse_candidates(
                conn,
                parse_id,
                {**record, "cardSnapshotId": snapshot_id},
                "review",
            )
            row = conn.execute(
                """
                SELECT raw_line_text, parsed_ear_label_code, parsed_metadata_json, needs_review
                FROM card_note_item_log
                WHERE parse_id = ?
                """,
                (parse_id,),
            ).fetchone()

        metadata = json.loads(row["parsed_metadata_json"])
        evaluator = metadata["hybrid_note_line_evaluator"]

        assert row["raw_line_text"] == "101 L'"
        assert row["parsed_ear_label_code"] == "L_PRIME"
        assert row["needs_review"] == 1
        assert evaluator["source_layer"] == "parsed or intermediate result"
        assert evaluator["source_refs"] == {
            "photo_id": photo_id,
            "parse_id": parse_id,
            "note_item_id": f"note_{parse_id}_1",
            "line_number": 1,
            "card_snapshot_id": snapshot_id,
            "roi_ref": "note_block:1",
        }
        assert evaluator["hybrid_candidate"]["parsed_ear_label_code"] == "L_PRIME"
        assert evaluator["rule_candidate"]["expected_ear_label_code"] == "R_PRIME"
        assert evaluator["rule_candidate"]["rule_interpretation_boundary"] == "review hint only"
        assert "rule_expected_ear_label_mismatch" in evaluator["conflicts"]
    finally:
        db.DB_PATH = old_db_path
