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
    assert summary["sanitized_report_path"] == str(output_report)
    markdown = output_report.read_text(encoding="utf-8")
    assert "Layer classification: review item / sanitized private accuracy report." in markdown
    assert "Mouse IDs and note-line continuity" in markdown
    assert "| Go/no-go decision | go |" in markdown
    combined = result.stdout + markdown
    assert "SECRET_" not in combined
    assert str(manifest_path) not in combined
    assert str(results_path) not in combined


def test_package_exposes_private_accuracy_reporter_command() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"]["pilot:private-accuracy"] == "python scripts/report-private-accuracy.py"
