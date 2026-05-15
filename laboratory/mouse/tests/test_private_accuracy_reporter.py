from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "report-private-accuracy.py"


def load_reporter_module():
    spec = importlib.util.spec_from_file_location("report_private_accuracy", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_private_manifest(tmp_path: Path) -> Path:
    photo = tmp_path / "private-source-photo.jpg"
    photo.write_bytes(b"private copied photo placeholder")
    manifest = {
        "layer": "review item / test fixture",
        "canonical": False,
        "source_policy": "Local-only private pilot. Do not publish raw fields.",
        "cases": [
            {
                "case_id": "pilot_photo_001",
                "source_photo_path": str(photo),
                "source_photo_filename": "pilot_photo_001.jpg",
                "card_type": "separated",
                "traceability_label": "Private pilot / photo 001",
                "expected_review_level": "quick_check",
                "expected_export_blocking": False,
                "expected_fields": {
                    "raw_strain_text": "SECRET_STRAIN_ALPHA",
                    "mouse_ids_or_note_lines": ["SECRET_MOUSE_001 R'"],
                    "sex_count": "SECRET_COUNT_ONE",
                    "dob": "SECRET_DOB_ONE",
                    "mating_or_litter_note": "",
                    "expected_review_blockers": [],
                },
            },
            {
                "case_id": "pilot_photo_002",
                "source_photo_path": str(photo),
                "source_photo_filename": "pilot_photo_002.jpg",
                "card_type": "mating",
                "traceability_label": "Private pilot / photo 002",
                "expected_review_level": "must_review",
                "expected_export_blocking": True,
                "expected_fields": {
                    "raw_strain_text": "SECRET_STRAIN_BETA",
                    "mouse_ids_or_note_lines": ["SECRET_PARENT_NOTE"],
                    "sex_count": "SECRET_PARENT_COUNT",
                    "dob": "unclear",
                    "mating_or_litter_note": "SECRET_LITTER_NOTE",
                    "expected_review_blockers": ["mating_litter_note_review"],
                },
            },
            {
                "case_id": "pilot_photo_003",
                "source_photo_path": str(photo),
                "source_photo_filename": "pilot_photo_003.jpg",
                "card_type": "unclear",
                "traceability_label": "Private pilot / photo 003",
                "expected_review_level": "must_review",
                "expected_export_blocking": True,
                "expected_fields": {
                    "raw_strain_text": "unclear",
                    "mouse_ids_or_note_lines": ["SECRET_UNCLEAR_NOTE"],
                    "sex_count": "unclear",
                    "dob": "unclear",
                    "mating_or_litter_note": "not visible",
                    "expected_review_blockers": ["low_confidence"],
                },
            },
            {
                "case_id": "pilot_photo_004",
                "source_photo_path": str(photo),
                "source_photo_filename": "pilot_photo_004.jpg",
                "card_type": "other",
                "traceability_label": "Private pilot / photo 004",
                "expected_review_level": "trace_only",
                "expected_export_blocking": False,
                "expected_fields": {
                    "raw_strain_text": "SECRET_OTHER_FORMAT",
                    "mouse_ids_or_note_lines": [],
                    "sex_count": "not applicable",
                    "dob": "",
                    "mating_or_litter_note": "",
                    "expected_review_blockers": [],
                },
            },
        ],
    }
    path = tmp_path / "private-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def passing_result(case_id: str, *, review_level: str, blocking: bool) -> dict[str, object]:
    return {
        "case_id": case_id,
        "actual_review_level": review_level,
        "export_blocked_until_resolved": blocking,
        "unresolved_must_review_at_export": False,
        "source_preserved": True,
        "silent_overwrite": False,
        "review_seconds": 180,
        "manual_transcription_required": False,
        "failure_labels": [],
        "field_scores": {
            "mouse_ids_or_note_lines": {
                "status": "exact",
                "reviewed_before_apply": True,
                "traceable": True,
            },
            "card_type_review_routing": {
                "status": "exact",
                "reviewed_before_apply": True,
                "traceable": True,
            },
            "sex_count_dob": {
                "status": "corrected",
                "reviewed_before_apply": True,
                "traceable": True,
            },
            "mating_litter_context": {
                "status": "exact",
                "reviewed_before_apply": True,
                "traceable": True,
            },
            "export_provenance": {
                "status": "exact",
                "reviewed_before_apply": True,
                "traceable": True,
            },
        },
    }


def add_hybrid_note_line_cases(case: dict[str, object], scored_cases: list[dict[str, object]]) -> dict[str, object]:
    case["hybrid_note_line_evaluator"] = {
        "boundary": "review item / private accuracy scoring input",
        "scored_cases": scored_cases,
    }
    return case


def write_results(tmp_path: Path, cases: list[dict[str, object]]) -> Path:
    payload = {
        "layer": "review item / private accuracy scoring input",
        "canonical": False,
        "source_policy": "Local-only scoring input. Publish aggregates only.",
        "workflow_metrics": {
            "photos_uploaded": len(cases),
            "photos_with_extraction_draft": len(cases),
            "review_items_opened": 3,
            "review_items_corrected": 1,
            "review_items_accepted_without_correction": 2,
            "xlsx_exports_generated": 1,
        },
        "cases": cases,
    }
    path = tmp_path / "private-results.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_reporter_scores_private_results_without_leaking_manifest_values(tmp_path: Path) -> None:
    reporter = load_reporter_module()
    manifest_path = write_private_manifest(tmp_path)
    results_path = write_results(
        tmp_path,
        [
            passing_result("pilot_photo_001", review_level="quick_check", blocking=False),
            passing_result("pilot_photo_002", review_level="must_review", blocking=True),
            passing_result("pilot_photo_003", review_level="must_review", blocking=True),
            passing_result("pilot_photo_004", review_level="trace_only", blocking=False),
        ],
    )

    summary = reporter.build_report(manifest_path=manifest_path, results_path=results_path)

    assert summary["status"] == "passed"
    assert summary["decision"] == "go"
    assert summary["boundary"] == "review item / sanitized private accuracy report"
    assert summary["canonical"] is False
    assert summary["case_count"] == 4
    assert summary["matched_case_count"] == 4
    assert summary["field_family_scores"]["mouse_ids_or_note_lines"]["rate"] == 1.0
    assert summary["field_family_scores"]["sex_count_dob"]["corrected_before_apply"] == 4
    assert summary["hard_gates"]["private_data_containment"]["status"] == "passed"
    assert summary["hard_gates"]["review_blocking"]["status"] == "passed"
    assert summary["hard_gates"]["accuracy_thresholds"]["status"] == "passed"
    encoded = json.dumps(summary, ensure_ascii=False)
    assert "SECRET_" not in encoded
    assert str(manifest_path) not in encoded
    assert str(tmp_path) not in encoded
    assert "source_photo_path" not in encoded


def test_reporter_summarizes_hybrid_note_line_evaluator_metrics_without_case_text(tmp_path: Path) -> None:
    reporter = load_reporter_module()
    manifest_path = write_private_manifest(tmp_path)
    cases = [
        add_hybrid_note_line_cases(
            passing_result("pilot_photo_001", review_level="quick_check", blocking=False),
            [
                {
                    "hybrid_pre_review_status": "exact",
                    "local_ocr_pre_review_status": "missed",
                    "auto_candidate_usable_without_edit": True,
                    "review_correction_required": False,
                    "reviewed_before_apply": True,
                    "source_image_quality_bucket": "acceptable",
                    "roi_alignment_bucket": "strong",
                    "line_segmentation_bucket": "strong",
                }
            ],
        ),
        add_hybrid_note_line_cases(
            passing_result("pilot_photo_002", review_level="must_review", blocking=True),
            [
                {
                    "hybrid_pre_review_status": "missed",
                    "local_ocr_pre_review_status": "missed",
                    "auto_candidate_usable_without_edit": False,
                    "review_correction_required": True,
                    "reviewed_before_apply": True,
                    "source_image_quality_bucket": "poor",
                    "roi_alignment_bucket": "weak",
                    "line_segmentation_bucket": "weak",
                    "failure_labels": [
                        "ocr_ai_note_line_disagreement",
                        "SECRET_PRIVATE_FAILURE_SHOULD_MAP_TO_UNKNOWN",
                    ],
                }
            ],
        ),
        add_hybrid_note_line_cases(
            passing_result("pilot_photo_003", review_level="must_review", blocking=True),
            [
                {
                    "hybrid_pre_review_status": "exact",
                    "local_ocr_pre_review_status": "exact",
                    "auto_candidate_usable_without_edit": True,
                    "review_correction_required": False,
                    "reviewed_before_apply": True,
                    "source_image_quality_bucket": "SECRET_PRIVATE_BUCKET_SHOULD_MAP_TO_UNKNOWN",
                    "roi_alignment_bucket": "strong",
                    "line_segmentation_bucket": "strong",
                    "raw_line_text": "SECRET_RAW_NOTE_SHOULD_NOT_APPEAR",
                }
            ],
        ),
        passing_result("pilot_photo_004", review_level="trace_only", blocking=False),
    ]
    results_path = write_results(tmp_path, cases)

    summary = reporter.build_report(manifest_path=manifest_path, results_path=results_path)

    metrics = summary["hybrid_note_line_evaluator_metrics"]
    assert metrics["scored_note_line_cases"] == 3
    assert metrics["pre_review_exact_rate"] == 0.6667
    assert metrics["auto_candidate_usable_without_edit_rate"] == 0.6667
    assert metrics["review_correction_rate"] == 0.3333
    assert metrics["local_ocr_pre_review_exact_rate"] == 0.3333
    assert metrics["local_ocr_to_hybrid_delta"] == 0.3333
    assert metrics["exact_or_corrected_before_apply_rate"] == 1.0
    assert metrics["invalid_hybrid_evaluator_inputs"] == 0
    assert metrics["source_image_quality_breakdown"]["acceptable"]["pre_review_exact_rate"] == 1.0
    assert metrics["source_image_quality_breakdown"]["poor"]["review_correction_rate"] == 1.0
    assert metrics["source_image_quality_breakdown"]["unknown"]["scored_note_line_cases"] == 1
    assert metrics["roi_alignment_breakdown"]["strong"]["scored_note_line_cases"] == 2
    assert metrics["line_segmentation_breakdown"]["strong"]["scored_note_line_cases"] == 2
    assert metrics["failure_label_counts"] == {
        "ocr_ai_note_line_disagreement": 1,
        "unknown_failure_label": 1,
    }
    encoded = json.dumps(summary, ensure_ascii=False)
    assert "SECRET_" not in encoded
    assert "raw_line_text" not in encoded


def test_reporter_summarizes_hybrid_candidate_sources_overrides_and_rule_hashes(
    tmp_path: Path,
) -> None:
    reporter = load_reporter_module()
    manifest_path = write_private_manifest(tmp_path)
    cases = [
        add_hybrid_note_line_cases(
            passing_result("pilot_photo_001", review_level="quick_check", blocking=False),
            [
                {
                    "expected_candidate_present": True,
                    "hybrid_pre_review_status": "exact",
                    "local_ocr_pre_review_status": "missed",
                    "ai_pre_review_status": "exact",
                    "auto_candidate_usable_without_edit": True,
                    "review_correction_required": False,
                    "reviewed_before_apply": True,
                    "source_image_quality_bucket": "acceptable",
                    "roi_alignment_bucket": "strong",
                    "line_segmentation_bucket": "strong",
                    "rule_snapshot_hash": "rulehash_apom_20260506",
                    "raw_line_text": "SECRET_RAW_NOTE_SHOULD_NOT_APPEAR",
                }
            ],
        ),
        add_hybrid_note_line_cases(
            passing_result("pilot_photo_002", review_level="must_review", blocking=True),
            [
                {
                    "expected_candidate_present": False,
                    "hybrid_pre_review_status": "false_positive",
                    "local_ocr_pre_review_status": "false_positive",
                    "ai_pre_review_status": "false_positive",
                    "auto_candidate_usable_without_edit": False,
                    "review_correction_required": True,
                    "reviewer_override": True,
                    "reviewed_before_apply": True,
                    "source_image_quality_bucket": "weak",
                    "roi_alignment_bucket": "weak",
                    "line_segmentation_bucket": "weak",
                    "rule_candidate": {
                        "rule_snapshot": {"rule_hash": "rulehash_apom_20260506"}
                    },
                }
            ],
        ),
        add_hybrid_note_line_cases(
            passing_result("pilot_photo_003", review_level="must_review", blocking=True),
            [
                {
                    "expected_candidate_present": True,
                    "hybrid_pre_review_status": "missed",
                    "local_ocr_pre_review_status": "missed",
                    "ai_pre_review_status": "missed",
                    "auto_candidate_usable_without_edit": False,
                    "review_correction_required": True,
                    "reviewer_override": True,
                    "reviewed_before_apply": True,
                    "source_image_quality_bucket": "poor",
                    "roi_alignment_bucket": "weak",
                    "line_segmentation_bucket": "weak",
                    "rule_snapshot_hash": "rulehash_other_20260507",
                }
            ],
        ),
        passing_result("pilot_photo_004", review_level="trace_only", blocking=False),
    ]
    results_path = write_results(tmp_path, cases)

    summary = reporter.build_report(manifest_path=manifest_path, results_path=results_path)

    metrics = summary["hybrid_note_line_evaluator_metrics"]
    assert metrics["false_positive_rate"] == 0.3333
    assert metrics["false_negative_rate"] == 0.3333
    assert metrics["reviewer_override_rate"] == 0.6667
    assert metrics["candidate_source_metrics"]["local_ocr"]["false_negative_rate"] == 0.6667
    assert metrics["candidate_source_metrics"]["ai"]["pre_review_exact_rate"] == 0.3333
    assert metrics["candidate_source_metrics"]["hybrid"]["false_positive_rate"] == 0.3333
    assert metrics["rule_snapshot_breakdown"]["rulehash_apom_20260506"]["scored_note_line_cases"] == 2
    assert metrics["rule_snapshot_breakdown"]["rulehash_apom_20260506"]["false_positive_count"] == 1
    assert metrics["rule_snapshot_breakdown"]["rulehash_other_20260507"]["false_negative_count"] == 1
    encoded = json.dumps(summary, ensure_ascii=False)
    assert "SECRET_" not in encoded
    assert "raw_line_text" not in encoded

    output_report = tmp_path / "sanitized-private-accuracy.md"
    output_report.write_text(
        reporter.build_markdown_report(run_label="candidate-source", summary=summary),
        encoding="utf-8",
    )
    markdown = output_report.read_text(encoding="utf-8")
    assert "Candidate source comparison" in markdown
    assert "Rule snapshot/hash breakdown" in markdown
    assert "rulehash_apom_20260506" in markdown
    assert "SECRET_" not in markdown


def test_reporter_flags_malformed_hybrid_note_line_metric_input(tmp_path: Path) -> None:
    reporter = load_reporter_module()
    manifest_path = write_private_manifest(tmp_path)
    malformed = passing_result("pilot_photo_001", review_level="quick_check", blocking=False)
    malformed["hybrid_note_line_evaluator"] = {"scored_cases": "not-a-list"}
    results_path = write_results(tmp_path, [malformed])

    summary = reporter.build_report(manifest_path=manifest_path, results_path=results_path)

    metrics = summary["hybrid_note_line_evaluator_metrics"]
    assert metrics["invalid_hybrid_evaluator_inputs"] == 1
    assert metrics["status"] == "invalid_input"
    assert summary["hard_gates"]["hybrid_note_line_evaluator_input"]["status"] == "failed"
    assert summary["decision"] == "no_go"


def test_reporter_returns_no_go_for_missing_cases_and_unreviewed_high_risk_failures(tmp_path: Path) -> None:
    reporter = load_reporter_module()
    manifest_path = write_private_manifest(tmp_path)
    bad_case = passing_result("pilot_photo_001", review_level="quick_check", blocking=False)
    bad_case["field_scores"]["mouse_ids_or_note_lines"] = {
        "status": "missed",
        "reviewed_before_apply": False,
        "traceable": False,
    }
    bad_case["failure_labels"] = ["mouse_id_or_note_line_error", "source_trace_missing"]
    bad_case["silent_overwrite"] = True
    results_path = write_results(tmp_path, [bad_case])

    summary = reporter.build_report(manifest_path=manifest_path, results_path=results_path)

    assert summary["status"] == "failed"
    assert summary["decision"] == "no_go"
    assert summary["matched_case_count"] == 1
    assert summary["missing_result_case_count"] == 3
    assert summary["field_family_scores"]["mouse_ids_or_note_lines"]["unreviewed_high_risk_misses"] == 1
    assert summary["hard_gates"]["traceability"]["status"] == "failed"
    assert summary["hard_gates"]["silent_overwrite_prevention"]["status"] == "failed"
    assert summary["failure_taxonomy_counts"] == {
        "mouse_id_or_note_line_error": 1,
        "source_trace_missing": 1,
    }
    encoded = json.dumps(summary, ensure_ascii=False)
    assert "SECRET_" not in encoded
    assert str(tmp_path) not in encoded


def test_reporter_cli_writes_sanitized_markdown_and_json_summary(tmp_path: Path) -> None:
    manifest_path = write_private_manifest(tmp_path)
    results_path = write_results(
        tmp_path,
        [
            passing_result("pilot_photo_001", review_level="quick_check", blocking=False),
            passing_result("pilot_photo_002", review_level="must_review", blocking=True),
            passing_result("pilot_photo_003", review_level="must_review", blocking=True),
            passing_result("pilot_photo_004", review_level="trace_only", blocking=False),
        ],
    )
    output_report = tmp_path / "sanitized-private-accuracy.md"

    result = subprocess.run(
        [
            "python",
            str(SCRIPT_PATH),
            "--manifest",
            str(manifest_path),
            "--results",
            str(results_path),
            "--output-report",
            str(output_report),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["decision"] == "go"
    assert summary["sanitized_report_written"] is True
    assert summary["sanitized_report_filename"] == output_report.name
    markdown = output_report.read_text(encoding="utf-8")
    assert "Layer classification: review item / sanitized private accuracy report." in markdown
    assert "Mouse IDs and note-line continuity" in markdown
    assert "Hybrid Note-Line Evaluator Metrics" in markdown
    assert "Source image quality breakdown" in markdown
    assert "ROI alignment breakdown" in markdown
    assert "| Go/no-go decision | go |" in markdown
    combined = result.stdout + markdown
    assert "SECRET_" not in combined
    assert str(manifest_path) not in combined
    assert str(results_path) not in combined
    assert str(output_report) not in result.stdout


def test_package_exposes_private_accuracy_reporter_command() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"]["pilot:private-accuracy"] == "python scripts/report-private-accuracy.py"
