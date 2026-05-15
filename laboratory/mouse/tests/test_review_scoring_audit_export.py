from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

from app import db


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "export-review-scoring-audit-input.py"
REPORTER_PATH = ROOT / "scripts" / "report-private-accuracy.py"


def load_export_module():
    spec = importlib.util.spec_from_file_location("export_review_scoring_audit_input", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reporter_module():
    spec = importlib.util.spec_from_file_location("report_private_accuracy", REPORTER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_manifest(tmp_path: Path) -> Path:
    private_source = tmp_path / "private-source"
    private_source.mkdir()
    (private_source / "card-action.jpg").write_bytes(b"private photo action")
    (private_source / "card-correction.jpg").write_bytes(b"private photo correction")
    manifest = {
        "layer": "review item / test fixture",
        "canonical": False,
        "source_policy": "Local-only private manifest. Do not publish raw fields.",
        "cases": [
            {
                "case_id": "apom_001",
                "source_photo_path": str(private_source / "card-action.jpg"),
                "source_photo_filename": "card-action.jpg",
                "expected_review_level": "must_review",
                "expected_export_blocking": True,
                "expected_fields": {"mouse_ids_or_note_lines": ["SECRET_RAW_NOTE_ACTION"]},
            },
            {
                "case_id": "apom_002",
                "source_photo_path": str(private_source / "card-correction.jpg"),
                "source_photo_filename": "card-correction.jpg",
                "expected_review_level": "must_review",
                "expected_export_blocking": True,
                "expected_fields": {"mouse_ids_or_note_lines": ["SECRET_RAW_NOTE_CORRECTION"]},
            },
        ],
    }
    path = tmp_path / "private-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def seed_review_scoring_audit_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "mouse_lims.sqlite"
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = db_path
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_action",
                    "card-action.jpg",
                    str(tmp_path / "SECRET_PRIVATE_PATH" / "card-action.jpg"),
                    "2026-05-16T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                    "photo_correction",
                    "card-correction.jpg",
                    str(tmp_path / "SECRET_PRIVATE_PATH" / "card-correction.jpg"),
                    "2026-05-16T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "parse_action",
                    "photo_action",
                    "ai_photo_extraction",
                    json.dumps({"rawText": "SECRET_RAW_OCR_ACTION"}, ensure_ascii=False),
                    "2026-05-16T00:01:00Z",
                    "review",
                    50,
                    1,
                    "parse_correction",
                    "photo_correction",
                    "ai_photo_extraction",
                    json.dumps({"rawText": "SECRET_RAW_OCR_CORRECTION"}, ensure_ascii=False),
                    "2026-05-16T00:01:00Z",
                    "review",
                    50,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value, suggested_value,
                     review_reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_action",
                    "parse_action",
                    "Medium",
                    "AI-extracted photo transcription needs review",
                    "SECRET_CURRENT_ACTION",
                    "candidate",
                    "Needs reviewer scoring.",
                    "resolved",
                    "2026-05-16T00:02:00Z",
                    "review_correction",
                    "parse_correction",
                    "Medium",
                    "AI-extracted photo transcription needs review",
                    "SECRET_CURRENT_CORRECTION",
                    "candidate",
                    "Needs reviewer scoring.",
                    "resolved",
                    "2026-05-16T00:02:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO action_log
                    (action_id, action_type, target_id, before_value, after_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "action_review_resolved",
                    "review_resolved",
                    "review_action",
                    json.dumps({"current_value": "SECRET_BEFORE_ACTION"}, ensure_ascii=False),
                    json.dumps(
                        {
                            "status": "resolved",
                            "source_photo_id": "photo_action",
                            "source_photo_filename": "card-action.jpg",
                            "scoring_audit": {
                                "status": "partial_match",
                                "note": str(tmp_path / "SECRET_PRIVATE_PATH"),
                                "boundary": "review item / scoring audit metadata",
                            },
                        },
                        ensure_ascii=False,
                    ),
                    "2026-05-16T00:03:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO correction_log
                    (correction_id, entity_type, entity_id, field_name, before_value, after_value,
                     reason, review_id, source_layer, evidence_reference_json,
                     correction_context_json, corrected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "correction_scoring_audit",
                    "review_item",
                    "review_correction",
                    "reviewed_value",
                    "SECRET_BEFORE_CORRECTION",
                    "reviewed candidate",
                    "Reviewer correction.",
                    "review_correction",
                    "review item",
                    json.dumps({"review_id": "review_correction"}, ensure_ascii=False),
                    json.dumps(
                        {
                            "field_name": "reviewed_value",
                            "scoring_audit_status": "unscorable_due_to_occlusion",
                            "scoring_audit_note": "SECRET_RAW_CORRECTION_NOTE",
                        },
                        ensure_ascii=False,
                    ),
                    "2026-05-16T00:04:00Z",
                ),
            )
    finally:
        db.DB_PATH = old_db_path
    return db_path


def test_export_review_scoring_audit_input_feeds_private_accuracy_reporter(tmp_path: Path) -> None:
    exporter = load_export_module()
    reporter = load_reporter_module()
    manifest_path = write_manifest(tmp_path)
    db_path = seed_review_scoring_audit_db(tmp_path)
    output_path = tmp_path / "sanitized-review-scoring-input.json"

    summary = exporter.export_review_scoring_audit_input(
        db_path=db_path,
        manifest_path=manifest_path,
        output_path=output_path,
        run_label="apom review scoring audit",
    )

    assert summary == {
        "status": "created",
        "boundary": "review item / private accuracy scoring input",
        "canonical": False,
        "run_label": "apom-review-scoring-audit",
        "matched_case_count": 2,
        "unmatched_audit_count": 0,
        "output_path": "private output path omitted",
    }
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["reviewer_scoring_provenance"] == {
        "method": "manual_operator_review",
        "approved_by_operator": True,
        "approval_scope": "review resolution scoring audit metadata",
        "raw_payload_policy": "omitted_from_sanitized_report",
    }
    assert [case["case_id"] for case in payload["cases"]] == ["apom_001", "apom_002"]
    first_scored = payload["cases"][0]["hybrid_note_line_evaluator"]["scored_cases"][0]
    second_scored = payload["cases"][1]["hybrid_note_line_evaluator"]["scored_cases"][0]
    assert first_scored["hybrid_pre_review_status"] == "partial_match"
    assert first_scored["failure_labels"] == ["partial_match"]
    assert second_scored["hybrid_pre_review_status"] == "unscorable_due_to_occlusion"
    assert second_scored["failure_labels"] == ["unscorable_due_to_occlusion"]
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "SECRET_" not in encoded
    assert str(tmp_path) not in encoded

    report = reporter.build_report(manifest_path=manifest_path, results_path=output_path)
    metrics = report["hybrid_note_line_evaluator_metrics"]
    assert metrics["scored_note_line_cases"] == 2
    assert metrics["partial_match_count"] == 1
    assert metrics["unscorable_due_to_occlusion_count"] == 1
    assert metrics["reviewer_override_count"] == 2


def test_review_scoring_audit_export_cli_and_package_script_redact_paths(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path)
    db_path = seed_review_scoring_audit_db(tmp_path)
    output_path = tmp_path / "private-output" / "review-scoring-input.json"

    result = subprocess.run(
        [
            "python",
            str(SCRIPT_PATH),
            "--db-path",
            str(db_path),
            "--manifest",
            str(manifest_path),
            "--output",
            str(output_path),
            "--run-label",
            "apom cli audit",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["matched_case_count"] == 2
    assert summary["output_path"] == "private output path omitted"
    assert str(tmp_path) not in result.stdout

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert (
        package["scripts"]["pilot:review-scoring-audit-export"]
        == "python scripts/export-review-scoring-audit-input.py"
    )
