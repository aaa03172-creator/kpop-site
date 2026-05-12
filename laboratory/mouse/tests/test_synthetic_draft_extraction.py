from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-synthetic-draft-extraction.py"
PACKAGE_PATH = ROOT / "package.json"


def test_synthetic_draft_extraction_harness_reports_reviewable_local_drafts(tmp_path: Path) -> None:
    output_dir = tmp_path / "synthetic_draft_extraction"

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--output-dir",
            str(output_dir),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    assert summary["boundary"] == "review item / test fixture"
    assert summary["canonical"] is False
    assert summary["source_policy"] == (
        "Local-only synthetic draft extraction. Do not send generated images, "
        "draft payloads, or source records to external OCR, LLM, or inference services."
    )
    assert summary["generated"]["image_count"] == 5
    assert summary["verification"]["passed"] == 5
    assert summary["verification"]["failed"] == 0
    assert summary["verification"]["draft_boundary"] == "parsed or intermediate result"
    assert summary["verification"]["external_inference_used"] is False
    assert summary["verification"]["canonical_writes"] == 0
    assert summary["verification"]["reviewable_cases"] >= 4
    assert summary["verification"]["trace_only_cases"] >= 1
    assert summary["ocr_provider"]["provider"] == "tesseract_cli"
    assert summary["ocr_provider"]["external_inference_used"] is False
    assert summary["local_ocr_probe"]["provider"] == "tesseract_cli"
    assert summary["local_ocr_probe"]["external_inference_used"] is False
    assert summary["extraction_mode"] in {"fixture_payload_surrogate", "local_ocr"}
    if not summary["ocr_provider"]["available"]:
        assert summary["extraction_mode"] == "fixture_payload_surrogate"
        assert "skip_reason" in summary["ocr_provider"]
        assert summary["local_ocr_probe"]["status"] == "skipped"
        assert summary["local_ocr_probe"]["case_count"] == 0
        assert "skip_reason" in summary["local_ocr_probe"]
        assert summary["local_ocr_probe"]["quality_report"] == {
            "case_count": 0,
            "empty_ocr_case_count": 0,
            "hint_matched_case_count": 0,
            "text_length_min": 0,
            "text_length_max": 0,
            "quality_grade_counts": {},
            "by_coverage_tag": {},
            "quality_findings": [],
        }
    else:
        quality_report = summary["local_ocr_probe"]["quality_report"]
        assert quality_report["case_count"] == 5
        assert quality_report["empty_ocr_case_count"] <= 5
        assert quality_report["hint_matched_case_count"] <= 5
        assert quality_report["text_length_min"] >= 0
        assert quality_report["text_length_max"] >= quality_report["text_length_min"]
        assert quality_report["quality_grade_counts"].keys() <= {
            "empty",
            "garbled",
            "partial_note_match",
            "usable_note_match",
        }
        assert quality_report["by_coverage_tag"]["cropped_or_blurry"]["case_count"] == 1
        assert quality_report["by_coverage_tag"]["cropped_or_blurry"]["garbled_case_count"] == 1
        assert quality_report["by_coverage_tag"]["ear_label_ambiguity"]["empty_ocr_case_count"] == 1
        assert quality_report["by_coverage_tag"]["numeric_notes"]["usable_note_match_case_count"] == 1
        assert quality_report["quality_findings"] == [
            {
                "coverage_tag": "cropped_or_blurry",
                "issue": "garbled_ocr",
                "affected_case_count": 1,
                "recommended_action": "Route this card type to review and tune image preprocessing before trusting raw OCR text.",
            },
            {
                "coverage_tag": "ear_label_ambiguity",
                "issue": "empty_ocr",
                "affected_case_count": 1,
                "recommended_action": "Treat empty OCR as review-only and require source photo or manual note-line evidence.",
            },
            {
                "coverage_tag": "low_confidence",
                "issue": "garbled_ocr",
                "affected_case_count": 1,
                "recommended_action": "Route this card type to review and tune image preprocessing before trusting raw OCR text.",
            },
        ]
        for result in summary["local_ocr_probe"]["results"]:
            assert isinstance(result["coverage_tags"], list)
            assert result["coverage_tags"]
            assert result["quality_grade"] in {
                "empty",
                "garbled",
                "partial_note_match",
                "usable_note_match",
            }
            assert isinstance(result["expected_note_hints"], list)
            assert result["expected_note_hints"]
            assert isinstance(result["matched_note_hints"], list)
            assert result["empty_ocr"] == (result["text_length"] == 0)
            assert result["review_required"] is (result["quality_grade"] in {"empty", "garbled"})
            assert result["canonical_write"] is False
            assert result["recommended_action"]
        results_by_case = {
            result["case_id"]: result
            for result in summary["local_ocr_probe"]["results"]
        }
        assert results_by_case["synthetic_digit_prime_confusion_card"]["recommended_action"] == (
            "Treat empty OCR as review-only and require source photo or manual note-line evidence."
        )
        assert results_by_case["synthetic_low_confidence_blurry_card"]["recommended_action"] == (
            "Route this card type to review and tune image preprocessing before trusting raw OCR text."
        )
        assert results_by_case["synthetic_numeric_notes_card"]["recommended_action"] == (
            "Use OCR note-line hints as review aids only; keep fixture draft and source photo as the evidence anchors."
        )
    assert {result["case_id"] for result in summary["results"]} == {
        "synthetic_clear_card",
        "synthetic_low_confidence_blurry_card",
        "synthetic_numeric_notes_card",
        "synthetic_digit_prime_confusion_card",
        "synthetic_dense_mating_notes_card",
    }
    for result in summary["results"]:
        assert result["source_photo_id"]
        assert result["photo_filename"].endswith(".jpg")
        assert result["draft_boundary"] == "parsed or intermediate result"
        assert result["canonical_write"] is False
        assert result["external_inference_used"] is False
        assert result["source_evidence"]["photo_id"] == result["source_photo_id"]
        assert result["source_evidence"]["photo_filename"] == result["photo_filename"]
        assert result["source_evidence"]["boundary"] == "raw source / test fixture"
        assert isinstance(result["source_evidence"]["note_lines"], list)
        assert result["source_evidence"]["photo_id"] == result["source_photo_id"]
        assert result["source_evidence"]["note_lines"]


def test_synthetic_draft_extraction_default_run_cleans_disposable_output() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(completed.stdout)
    generated_dir = Path(summary["generated"]["manifest"]).parent
    assert summary["verification"]["passed"] == 5
    assert not generated_dir.exists()


def test_synthetic_draft_extraction_text_output_includes_ocr_quality(tmp_path: Path) -> None:
    output_dir = tmp_path / "synthetic_draft_extraction"

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Synthetic draft extraction: 5/5 passed, 0 failed" in completed.stdout
    assert "Local OCR quality:" in completed.stdout
    assert "empty OCR" in completed.stdout
    assert "note-line hints matched" in completed.stdout
    assert "text length range" in completed.stdout
    if shutil.which("tesseract"):
        assert "By card type:" in completed.stdout
        assert "cropped_or_blurry: 1 case(s), 0 empty, 1 garbled" in completed.stdout
        assert "ear_label_ambiguity: 1 case(s), 1 empty, 0 garbled" in completed.stdout
        assert "OCR weak spots:" in completed.stdout
        assert "cropped_or_blurry -> garbled_ocr (1 case)" in completed.stdout
        assert "ear_label_ambiguity -> empty_ocr (1 case)" in completed.stdout
    else:
        assert "0 empty OCR / 0 case(s)" in completed.stdout
        assert "By card type:" not in completed.stdout
        assert "OCR weak spots:" not in completed.stdout


def test_package_exposes_synthetic_draft_extraction_script() -> None:
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))

    assert package["scripts"]["test:synthetic-draft-extraction"] == (
        "python scripts/verify-synthetic-draft-extraction.py --json"
    )
    assert "npm run test:synthetic-draft-extraction" in package["scripts"]["verify"]
