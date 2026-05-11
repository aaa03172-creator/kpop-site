from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify-photo-e2e-cases.py"


def load_verifier_module():
    spec = importlib.util.spec_from_file_location("verify_photo_e2e_cases", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_photo_e2e_summary_reports_confidence_calibration_bands() -> None:
    verifier = load_verifier_module()
    manifest = {
        "boundary": "review item / test fixture",
        "source_policy": "Use only local photo fixtures.",
        "recommended_coverage_tags": ["clear", "low_confidence", "dense_notes", "cropped_or_blurry"],
        "cases": [
            {
                "case_id": "clear_card",
                "purpose": "Clear card should stay high confidence.",
                "coverage_tags": ["clear"],
                "expected_parse": {"min_confidence": 60},
            },
            {
                "case_id": "low_confidence_card_blocks_export",
                "purpose": "Low confidence card should remain review-blocking.",
                "coverage_tags": ["low_confidence"],
                "expected_parse": {"max_confidence": 20},
            },
        ],
    }
    results = [
        {
            "case_id": "clear_card",
            "status": "PASS",
            "photo_id": "photo_clear",
            "parse_id": "parse_clear",
            "confidence": 82,
            "failures": [],
        },
        {
            "case_id": "low_confidence_card_blocks_export",
            "status": "PASS",
            "photo_id": "photo_low",
            "parse_id": "parse_low",
            "confidence": 12,
            "failures": [],
        },
    ]

    summary = verifier.build_summary(
        manifest=manifest,
        manifest_path=Path("config/photo_e2e_validation_cases.json"),
        results=results,
        fail_count=0,
    )

    assert summary["boundary"] == "review item / test fixture"
    assert summary["source_policy"] == "Use only local photo fixtures."
    assert summary["confidence_calibration"] == {
        "case_count": 2,
        "min_confidence": 12.0,
        "max_confidence": 82.0,
        "average_confidence": 47.0,
        "bands": {
            "0_20_must_review": 1,
            "21_59_review": 0,
            "60_100_clearer": 1,
        },
        "low_confidence_guard_cases": ["low_confidence_card_blocks_export"],
        "coverage": {
            "recommended_tags": ["clear", "low_confidence", "dense_notes", "cropped_or_blurry"],
            "covered_tags": ["clear", "low_confidence"],
            "missing_tags": ["dense_notes", "cropped_or_blurry"],
            "case_tags": {
                "clear_card": ["clear"],
                "low_confidence_card_blocks_export": ["low_confidence"],
            },
        },
    }


def test_missing_fixture_summary_can_be_required_as_failed_gate() -> None:
    verifier = load_verifier_module()
    manifest = {
        "boundary": "review item / test fixture",
        "source_policy": "Use only local photo fixtures.",
        "cases": [{"case_id": "clear_card"}, {"case_id": "low_confidence_card"}],
    }

    summary = verifier.build_missing_fixture_summary(
        manifest=manifest,
        manifest_path=Path("config/photo_e2e_validation_cases.json"),
        missing_tables=["card_note_item_log", "photo_log"],
        require_fixtures=True,
    )

    assert summary["status"] == "failed"
    assert summary["failed"] == 2
    assert summary["skipped"] == 0
    assert summary["missing_tables"] == ["card_note_item_log", "photo_log"]
    assert "required" in summary["failure_reason"]
    assert verifier.missing_fixture_exit_code(summary) == 1
