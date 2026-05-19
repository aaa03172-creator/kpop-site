from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from app import db


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "export-review-scoring-audit-input.py"
REPORTER_PATH = ROOT / "scripts" / "report-private-accuracy.py"
REGRESSION_RUNNER_PATH = ROOT / "scripts" / "run-private-accuracy-regression.py"


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


def load_regression_runner_module():
    spec = importlib.util.spec_from_file_location("run_private_accuracy_regression", REGRESSION_RUNNER_PATH)
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
                "card_type": "separated",
                "traceability_label": "Private review audit export / photo 001",
                "expected_review_level": "must_review",
                "expected_export_blocking": True,
                "expected_fields": {
                    "raw_strain_text": "operator reviewed",
                    "mouse_ids_or_note_lines": ["SECRET_RAW_NOTE_ACTION"],
                    "sex_count": "operator reviewed",
                    "dob": "operator reviewed",
                    "mating_or_litter_note": "",
                    "expected_review_blockers": [],
                },
            },
            {
                "case_id": "apom_002",
                "source_photo_path": str(private_source / "card-correction.jpg"),
                "source_photo_filename": "card-correction.jpg",
                "card_type": "separated",
                "traceability_label": "Private review audit export / photo 002",
                "expected_review_level": "must_review",
                "expected_export_blocking": True,
                "expected_fields": {
                    "raw_strain_text": "operator reviewed",
                    "mouse_ids_or_note_lines": [],
                    "sex_count": "operator reviewed",
                    "dob": "operator reviewed",
                    "mating_or_litter_note": "",
                    "expected_review_blockers": ["no_visible_note_line_for_evaluator_scoring"],
                },
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


def complete_field_scores(*, note_status: str) -> dict[str, dict[str, object]]:
    return {
        "mouse_ids_or_note_lines": {
            "status": note_status,
            "reviewed_before_apply": True,
            "traceable": True,
        },
        "card_type_review_routing": {
            "status": "corrected",
            "reviewed_before_apply": True,
            "traceable": True,
        },
        "sex_count_dob": {
            "status": "corrected",
            "reviewed_before_apply": True,
            "traceable": True,
        },
        "mating_litter_context": {
            "status": "corrected",
            "reviewed_before_apply": True,
            "traceable": True,
        },
        "export_provenance": {
            "status": "corrected",
            "reviewed_before_apply": True,
            "traceable": True,
        },
    }


def seed_full_field_review_outcome_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "mouse_full_outcome.sqlite"
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
                    "photo_full_scored",
                    "card-action.jpg",
                    "private path omitted",
                    "2026-05-16T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                    "photo_full_nonscorable",
                    "card-correction.jpg",
                    "private path omitted",
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
                    "parse_full_scored",
                    "photo_full_scored",
                    "ai_photo_extraction",
                    json.dumps({"rawText": "SECRET_RAW_OCR"}, ensure_ascii=False),
                    "2026-05-16T00:01:00Z",
                    "review",
                    50,
                    1,
                    "parse_full_nonscorable",
                    "photo_full_nonscorable",
                    "ai_photo_extraction",
                    json.dumps({"rawText": "SECRET_RAW_OCR"}, ensure_ascii=False),
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
                     review_reason, status, created_at, resolved_at, resolution_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_full_scored",
                    "parse_full_scored",
                    "Medium",
                    "AI-extracted photo transcription needs review",
                    "SECRET_CURRENT",
                    "candidate",
                    "Needs reviewer scoring.",
                    "resolved",
                    "2026-05-16T00:02:00Z",
                    "2026-05-16T00:03:00Z",
                    "Sanitized review note.",
                    "review_full_nonscorable",
                    "parse_full_nonscorable",
                    "Medium",
                    "AI-extracted photo transcription needs review",
                    "SECRET_CURRENT",
                    "candidate",
                    "Needs reviewer scoring.",
                    "resolved",
                    "2026-05-16T00:02:00Z",
                    "2026-05-16T00:03:00Z",
                    "Sanitized review note.",
                ),
            )
            field_outcome_scored = {
                "actual_review_level": "must_review",
                "export_blocked_until_resolved": True,
                "unresolved_must_review_at_export": False,
                "manual_transcription_required": False,
                "note_line_scoring_scope": "scored_note_line",
                "field_scores": complete_field_scores(note_status="exact"),
                "failure_labels": [],
            }
            field_outcome_nonscorable = {
                "actual_review_level": "must_review",
                "export_blocked_until_resolved": True,
                "unresolved_must_review_at_export": False,
                "manual_transcription_required": False,
                "note_line_scoring_scope": "no_visible_note_line_for_evaluator_scoring",
                "field_scores": complete_field_scores(note_status="not_applicable"),
                "failure_labels": ["no_visible_note_line_for_evaluator_scoring", "SECRET_RAW_LABEL"],
            }
            conn.execute(
                """
                INSERT INTO action_log
                    (action_id, action_type, target_id, before_value, after_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?)
                """,
                (
                    "action_full_scored",
                    "review_resolved",
                    "review_full_scored",
                    json.dumps({"current_value": "SECRET_BEFORE"}, ensure_ascii=False),
                    json.dumps(
                        {
                            "source_photo_filename": "card-action.jpg",
                            "scoring_audit": {
                                "status": "exact",
                                "note": "SECRET_RAW_NOTE",
                            },
                            "field_review_outcome": field_outcome_scored,
                        },
                        ensure_ascii=False,
                    ),
                    "2026-05-16T00:03:00Z",
                    "action_full_nonscorable",
                    "review_resolved",
                    "review_full_nonscorable",
                    json.dumps({"current_value": "SECRET_BEFORE"}, ensure_ascii=False),
                    json.dumps(
                        {
                            "source_photo_filename": "card-correction.jpg",
                            "field_review_outcome": field_outcome_nonscorable,
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


def test_export_field_outcomes_and_nonscorable_cases_reconstructs_go_report(tmp_path: Path) -> None:
    exporter = load_export_module()
    reporter = load_reporter_module()
    manifest_path = write_manifest(tmp_path)
    db_path = seed_full_field_review_outcome_db(tmp_path)
    output_path = tmp_path / "field-outcome-private-input.json"

    summary = exporter.export_review_scoring_audit_input(
        db_path=db_path,
        manifest_path=manifest_path,
        output_path=output_path,
        run_label="field outcome audit",
    )

    assert summary["matched_case_count"] == 2
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert [case["case_id"] for case in payload["cases"]] == ["apom_001", "apom_002"]
    assert payload["cases"][0]["field_scores"]["mouse_ids_or_note_lines"]["status"] == "exact"
    assert payload["cases"][1]["field_scores"]["mouse_ids_or_note_lines"]["status"] == "not_applicable"
    assert payload["cases"][1]["hybrid_note_line_evaluator"]["scored_cases"] == []
    assert payload["cases"][1]["failure_labels"] == ["no_visible_note_line_for_evaluator_scoring"]
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "SECRET_" not in encoded
    assert str(tmp_path) not in encoded

    report = reporter.build_report(manifest_path=manifest_path, results_path=output_path)
    assert report["decision"] == "go"
    assert report["matched_case_count"] == 2
    assert report["hybrid_note_line_evaluator_metrics"]["scored_note_line_cases"] == 1
    assert report["failure_taxonomy_counts"] == {"no_visible_note_line_for_evaluator_scoring": 1}


def test_export_field_outcomes_drops_untrusted_review_level_text(tmp_path: Path) -> None:
    exporter = load_export_module()
    manifest_path = write_manifest(tmp_path)
    db_path = seed_full_field_review_outcome_db(tmp_path)
    output_path = tmp_path / "field-outcome-private-input.json"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT after_value
            FROM action_log
            WHERE action_id = 'action_full_scored'
            """
        ).fetchone()
        after = json.loads(row[0])
        after["field_review_outcome"]["actual_review_level"] = r"C:\Users\User\Documents\SECRET_RAW_LEVEL"
        conn.execute(
            """
            UPDATE action_log
            SET after_value = ?
            WHERE action_id = 'action_full_scored'
            """,
            (json.dumps(after, ensure_ascii=False),),
        )

    exporter.export_review_scoring_audit_input(
        db_path=db_path,
        manifest_path=manifest_path,
        output_path=output_path,
        run_label="field outcome audit",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["cases"][0]["actual_review_level"] == "quick_check"
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "SECRET_RAW_LEVEL" not in encoded
    assert str(tmp_path) not in encoded


def test_sanitized_payload_validation_blocks_private_markers_without_echoing_values() -> None:
    exporter = load_export_module()
    payload = {
        "layer": "review item / private accuracy scoring input",
        "canonical": False,
        "cases": [
            {
                "case_id": "apom_001",
                "raw_payload": {"rawText": r"C:\Users\User\Documents\SECRET_RAW_NOTE"},
            }
        ],
    }

    with pytest.raises(ValueError) as exc:
        exporter.validate_sanitized_payload(payload)

    message = str(exc.value)
    assert "sanitized payload validation failed" in message
    assert "blocked_key:raw_payload" in message
    assert "blocked_value_marker:windows_path" in message
    assert "blocked_value_marker:secret_marker" in message
    assert "SECRET_RAW_NOTE" not in message
    assert r"C:\Users\User" not in message


def test_sanitized_payload_validation_blocks_raw_field_vocabulary_and_forward_slash_paths() -> None:
    exporter = load_export_module()
    payload = {
        "layer": "review item / private accuracy scoring input",
        "canonical": False,
        "cases": [
            {
                "case_id": "apom_001",
                "raw_line_text": "101 R'",
                "review_note": "C:/MouseDB-private-pilot/photos/card.jpg",
                "rawVisibleTextLines": ["line from source photo"],
                "raw_reviewer_notes": "operator transcription",
            }
        ],
    }

    with pytest.raises(ValueError) as exc:
        exporter.validate_sanitized_payload(payload)

    message = str(exc.value)
    assert "blocked_key:raw_line_text" in message
    assert "blocked_key:rawVisibleTextLines" in message
    assert "blocked_key:raw_reviewer_notes" in message
    assert "blocked_value_marker:windows_path" in message
    assert "MouseDB-private-pilot" not in message
    assert "101 R" not in message


def test_sanitized_payload_validation_allows_benign_documents_word_without_path_shape() -> None:
    exporter = load_export_module()
    payload = {
        "layer": "review item / private accuracy scoring input",
        "canonical": False,
        "run_label": "Documents workflow smoke run",
        "cases": [{"case_id": "apom_001", "traceability_label": "Documents checklist reviewed"}],
    }

    exporter.validate_sanitized_payload(payload)


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


def test_private_accuracy_regression_runner_exports_reports_and_compares_metrics(tmp_path: Path) -> None:
    exporter = load_export_module()
    manifest_path = write_manifest(tmp_path)
    db_path = seed_full_field_review_outcome_db(tmp_path)
    baseline_path = tmp_path / "baseline-private-input.json"
    run_dir = tmp_path / "private-regression-run"

    exporter.export_review_scoring_audit_input(
        db_path=db_path,
        manifest_path=manifest_path,
        output_path=baseline_path,
        run_label="baseline field outcomes",
    )

    result = subprocess.run(
        [
            "python",
            str(REGRESSION_RUNNER_PATH),
            "--db-path",
            str(db_path),
            "--manifest",
            str(manifest_path),
            "--run-dir",
            str(run_dir),
            "--run-label",
            "field outcome regression",
            "--suffix",
            "field-outcomes-regression-test",
            "--baseline-results",
            str(baseline_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "passed"
    assert summary["decision"] == "go"
    assert summary["matched_case_count"] == 2
    assert summary["field_outcome_integrity"] == {
        "case_count": 2,
        "missing_scope": [],
        "empty_scoped": [],
        "invalid_scoring_status": [],
        "scored_scope_missing_scored_cases": [],
    }
    assert summary["comparison"]["all_key_metrics_match"] is True
    assert summary["output_path"] == "private output path omitted"
    assert summary["report_path"] == "private output path omitted"
    assert summary["comparison_path"] == "private output path omitted"
    assert str(tmp_path) not in result.stdout

    exported = run_dir / "review-scoring-audit-export-input-field-outcomes-regression-test.json"
    report = run_dir / "sanitized-private-accuracy-field-outcomes-regression-test.md"
    comparison = run_dir / "field-outcomes-regression-comparison-field-outcomes-regression-test.json"
    assert exported.exists()
    assert report.exists()
    assert comparison.exists()
    encoded = exported.read_text(encoding="utf-8") + report.read_text(encoding="utf-8") + comparison.read_text(encoding="utf-8")
    assert "SECRET_" not in encoded
    assert str(tmp_path) not in encoded

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["pilot:private-accuracy-regression"] == (
        "python scripts/run-private-accuracy-regression.py"
    )


def test_private_accuracy_regression_runner_writes_sanitized_history_index(tmp_path: Path) -> None:
    exporter = load_export_module()
    manifest_path = write_manifest(tmp_path)
    db_path = seed_full_field_review_outcome_db(tmp_path)
    baseline_path = tmp_path / "baseline-private-input.json"
    run_dir = tmp_path / "private-regression-run"
    history_path = run_dir / "private-accuracy-regression-history.json"

    exporter.export_review_scoring_audit_input(
        db_path=db_path,
        manifest_path=manifest_path,
        output_path=baseline_path,
        run_label="baseline field outcomes",
    )

    result = subprocess.run(
        [
            "python",
            str(REGRESSION_RUNNER_PATH),
            "--db-path",
            str(db_path),
            "--manifest",
            str(manifest_path),
            "--run-dir",
            str(run_dir),
            "--run-label",
            "field outcome regression",
            "--suffix",
            "field-outcomes-history-test",
            "--baseline-results",
            str(baseline_path),
            "--history-index",
            str(history_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["history_update_status"] == "updated"
    assert summary["history_index_path"] == "private output path omitted"
    assert summary["baseline_promotion"] == {
        "eligible": True,
        "status": "ready_for_operator_promotion",
        "recommended_action": "operator_may_promote_current_results_to_baseline_after_review",
        "candidate_results_filename": "review-scoring-audit-export-input-field-outcomes-history-test.json",
        "current_baseline_filename": "baseline-private-input.json",
        "blocked_reasons": [],
    }
    assert str(tmp_path) not in result.stdout

    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["layer"] == "review item / private accuracy regression history"
    assert history["canonical"] is False
    assert history["run_count"] == 1
    assert history["latest_run_label"] == "field-outcomes-history-test"
    assert history["baseline"]["current_filename"] == "baseline-private-input.json"
    assert history["runs"][0]["artifacts"] == {
        "results_filename": "review-scoring-audit-export-input-field-outcomes-history-test.json",
        "report_filename": "sanitized-private-accuracy-field-outcomes-history-test.md",
        "comparison_filename": "field-outcomes-regression-comparison-field-outcomes-history-test.json",
    }
    assert history["runs"][0]["baseline_promotion"]["eligible"] is True
    encoded = json.dumps(history, ensure_ascii=False)
    assert str(tmp_path) not in encoded
    assert "SECRET_" not in encoded
    assert "source_photo_path" not in encoded


def test_private_accuracy_regression_history_sanitizes_existing_entries(tmp_path: Path) -> None:
    exporter = load_export_module()
    manifest_path = write_manifest(tmp_path)
    db_path = seed_full_field_review_outcome_db(tmp_path)
    baseline_path = tmp_path / "baseline-private-input.json"
    run_dir = tmp_path / "private-regression-existing-history"
    history_path = run_dir / "private-accuracy-regression-history.json"
    run_dir.mkdir()

    exporter.export_review_scoring_audit_input(
        db_path=db_path,
        manifest_path=manifest_path,
        output_path=baseline_path,
        run_label="baseline field outcomes",
    )
    history_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "run_id": "legacy-safe-run",
                        "recorded_at": "2026-05-18T00:00:00Z",
                        "boundary": "review item / private accuracy regression history",
                        "canonical": False,
                        "run_label": "operator reviewed free text",
                        "status": {"full_private_payload": "operator reviewed free text"},
                        "decision": "go",
                        "report_hard_gate_failures": [
                            "manifest_validation",
                            {"full_private_payload": "operator reviewed free text"},
                        ],
                        "private_path": str(tmp_path / "private-photo.jpg"),
                        "raw_payload": {"rawText": "SECRET_RAW_NOTE"},
                        "comparison": {
                            "all_key_metrics_match": True,
                            "matches": {
                                "decision": True,
                                "cases": [{"full_private_payload": "operator reviewed free text"}],
                            },
                            "old": {"cases": [{"full_private_payload": "operator reviewed free text"}]},
                            "new": {"cases": [{"full_private_payload": "operator reviewed free text"}]},
                        },
                        "field_outcome_integrity": {
                            "case_count": 17,
                            "missing_scope": ["operator reviewed free text"],
                        },
                        "regression_gate": {
                            "status": "operator reviewed free text",
                            "report_status": "failed",
                            "field_outcome_integrity_status": "passed",
                            "comparison_all_key_metrics_match": True,
                        },
                        "baseline_promotion": {
                            "eligible": False,
                            "status": "operator reviewed free text",
                            "recommended_action": "operator reviewed free text",
                            "blocked_reasons": [
                                "manifest_validation_failed",
                                {"full_private_payload": "operator reviewed free text"},
                            ],
                        },
                        "artifacts": {
                            "results_filename": "operator reviewed free text",
                            "source_photo_path": str(tmp_path / "private-photo.jpg"),
                        },
                    },
                    {
                        "run_id": "field-outcomes-existing-history-test",
                        "private_path": str(tmp_path / "stale-run.json"),
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "python",
            str(REGRESSION_RUNNER_PATH),
            "--db-path",
            str(db_path),
            "--manifest",
            str(manifest_path),
            "--run-dir",
            str(run_dir),
            "--run-label",
            "field outcome regression",
            "--suffix",
            "field-outcomes-existing-history-test",
            "--baseline-results",
            str(baseline_path),
            "--history-index",
            str(history_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["run_count"] == 2
    run_ids = {run["run_id"] for run in history["runs"]}
    assert run_ids == {"legacy-safe-run", "field-outcomes-existing-history-test"}
    encoded = json.dumps(history, ensure_ascii=False)
    assert str(tmp_path) not in encoded
    assert "private_path" not in encoded
    assert "raw_payload" not in encoded
    assert "rawText" not in encoded
    assert "SECRET_" not in encoded
    assert "source_photo_path" not in encoded
    assert "full_private_payload" not in encoded
    assert "operator reviewed free text" not in encoded
    assert "old" not in history["runs"][0]["comparison"]
    assert "new" not in history["runs"][0]["comparison"]
    assert history["runs"][0]["comparison"]["matches"] == {"decision": True}
    assert history["runs"][0]["field_outcome_integrity"]["missing_scope"] == []
    assert "status" not in history["runs"][0]["regression_gate"]
    assert history["runs"][0]["regression_gate"]["report_status"] == "failed"
    assert history["runs"][0]["baseline_promotion"]["blocked_reasons"] == ["manifest_validation_failed"]
    assert "status" not in history["runs"][0]["baseline_promotion"]
    assert "recommended_action" not in history["runs"][0]["baseline_promotion"]
    assert "results_filename" not in history["runs"][0]["artifacts"]


def test_baseline_promotion_status_blocks_each_operator_safety_gate() -> None:
    runner = load_regression_runner_module()
    base_kwargs = {
        "gate": {
            "status": "passed",
            "report_status": "passed",
            "field_outcome_integrity_status": "passed",
            "comparison_all_key_metrics_match": True,
        },
        "decision": "go",
        "matched_case_count": 2,
        "unmatched_audit_count": 0,
        "missing_result_case_count": 0,
        "extra_result_case_count": 0,
        "result_validation_failures": 0,
        "comparison": {"all_key_metrics_match": True},
        "report_hard_gate_failures": [],
        "results_path": Path("candidate-results.json"),
        "baseline_results_path": Path("baseline-results.json"),
    }

    checks = [
        ({"baseline_results_path": None}, "baseline_results_required"),
        ({"decision": "no_go"}, "decision_not_go"),
        ({"matched_case_count": 0}, "no_matched_cases"),
        ({"unmatched_audit_count": 1}, "unmatched_audit"),
        ({"missing_result_case_count": 1}, "result_case_mismatch"),
        ({"extra_result_case_count": 1}, "result_case_mismatch"),
        ({"result_validation_failures": 1}, "result_validation_failures"),
        ({"comparison": {"all_key_metrics_match": False}}, "baseline_comparison_mismatch"),
        ({"report_hard_gate_failures": ["manifest_validation"]}, "manifest_validation_failed"),
        ({"gate": {**base_kwargs["gate"], "status": "failed"}}, "regression_gate_failed"),
    ]
    for override, expected_reason in checks:
        kwargs = {**base_kwargs, **override}
        status = runner.baseline_promotion_status(**kwargs)
        assert status["eligible"] is False
        assert status["status"] == "blocked"
        assert status["recommended_action"] == "do_not_promote_baseline"
        assert expected_reason in status["blocked_reasons"]


def test_private_accuracy_regression_runner_fails_on_baseline_metric_mismatch(tmp_path: Path) -> None:
    exporter = load_export_module()
    manifest_path = write_manifest(tmp_path)
    db_path = seed_full_field_review_outcome_db(tmp_path)
    baseline_path = tmp_path / "baseline-private-input.json"
    run_dir = tmp_path / "private-regression-mismatch"

    exporter.export_review_scoring_audit_input(
        db_path=db_path,
        manifest_path=manifest_path,
        output_path=baseline_path,
        run_label="baseline field outcomes",
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["cases"][0]["field_scores"]["mouse_ids_or_note_lines"]["status"] = "missed"
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            "python",
            str(REGRESSION_RUNNER_PATH),
            "--db-path",
            str(db_path),
            "--manifest",
            str(manifest_path),
            "--run-dir",
            str(run_dir),
            "--run-label",
            "field outcome regression",
            "--suffix",
            "field-outcomes-regression-mismatch",
            "--baseline-results",
            str(baseline_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "failed"
    assert summary["regression_gate"]["status"] == "failed"
    assert summary["regression_gate"]["comparison_all_key_metrics_match"] is False
    assert "field_family_scores" in summary["comparison"]["matches"]
    assert summary["comparison"]["matches"]["field_family_scores"] is False
    assert str(tmp_path) not in result.stdout


def test_private_accuracy_regression_history_blocks_baseline_promotion_on_metric_mismatch(tmp_path: Path) -> None:
    exporter = load_export_module()
    manifest_path = write_manifest(tmp_path)
    db_path = seed_full_field_review_outcome_db(tmp_path)
    baseline_path = tmp_path / "baseline-private-input.json"
    run_dir = tmp_path / "private-regression-mismatch"
    history_path = run_dir / "private-accuracy-regression-history.json"

    exporter.export_review_scoring_audit_input(
        db_path=db_path,
        manifest_path=manifest_path,
        output_path=baseline_path,
        run_label="baseline field outcomes",
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["cases"][0]["field_scores"]["mouse_ids_or_note_lines"]["status"] = "missed"
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            "python",
            str(REGRESSION_RUNNER_PATH),
            "--db-path",
            str(db_path),
            "--manifest",
            str(manifest_path),
            "--run-dir",
            str(run_dir),
            "--run-label",
            "field outcome regression",
            "--suffix",
            "field-outcomes-history-mismatch",
            "--baseline-results",
            str(baseline_path),
            "--history-index",
            str(history_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "failed"
    assert summary["baseline_promotion"]["eligible"] is False
    assert "regression_gate_failed" in summary["baseline_promotion"]["blocked_reasons"]
    assert "baseline_comparison_mismatch" in summary["baseline_promotion"]["blocked_reasons"]
    assert summary["history_update_status"] == "updated"
    assert str(tmp_path) not in result.stdout

    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["run_count"] == 1
    assert history["runs"][0]["baseline_promotion"]["eligible"] is False
    assert "baseline_comparison_mismatch" in history["runs"][0]["baseline_promotion"]["blocked_reasons"]
    encoded = json.dumps(history, ensure_ascii=False)
    assert str(tmp_path) not in encoded


def test_private_accuracy_regression_runner_fails_on_field_outcome_integrity_violation(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path)
    db_path = seed_full_field_review_outcome_db(tmp_path)
    run_dir = tmp_path / "private-regression-integrity"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT after_value
            FROM action_log
            WHERE action_id = 'action_full_scored'
            """
        ).fetchone()
        after = json.loads(row["after_value"])
        after["field_review_outcome"].pop("note_line_scoring_scope", None)
        conn.execute(
            """
            UPDATE action_log
            SET after_value = ?
            WHERE action_id = 'action_full_scored'
            """,
            (json.dumps(after, ensure_ascii=False),),
        )

    result = subprocess.run(
        [
            "python",
            str(REGRESSION_RUNNER_PATH),
            "--db-path",
            str(db_path),
            "--manifest",
            str(manifest_path),
            "--run-dir",
            str(run_dir),
            "--run-label",
            "field outcome regression",
            "--suffix",
            "field-outcomes-regression-integrity",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "failed"
    assert summary["regression_gate"]["field_outcome_integrity_status"] == "failed"
    assert summary["field_outcome_integrity"]["missing_scope"] == ["apom_001"]
    assert str(tmp_path) not in result.stdout


def test_private_accuracy_regression_runner_fails_when_scored_scope_has_no_scored_cases(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path)
    db_path = seed_full_field_review_outcome_db(tmp_path)
    run_dir = tmp_path / "private-regression-missing-scored-case"
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT after_value
            FROM action_log
            WHERE action_id = 'action_full_scored'
            """
        ).fetchone()
        after = json.loads(row[0])
        after["scoring_audit"] = {}
        conn.execute(
            """
            UPDATE action_log
            SET after_value = ?
            WHERE action_id = 'action_full_scored'
            """,
            (json.dumps(after, ensure_ascii=False),),
        )

    result = subprocess.run(
        [
            "python",
            str(REGRESSION_RUNNER_PATH),
            "--db-path",
            str(db_path),
            "--manifest",
            str(manifest_path),
            "--run-dir",
            str(run_dir),
            "--run-label",
            "field outcome regression",
            "--suffix",
            "field-outcomes-regression-missing-scored-case",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "failed"
    assert summary["regression_gate"]["field_outcome_integrity_status"] == "failed"
    assert summary["field_outcome_integrity"]["scored_scope_missing_scored_cases"] == ["apom_001"]
    assert str(tmp_path) not in result.stdout
