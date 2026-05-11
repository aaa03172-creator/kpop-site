from __future__ import annotations

import json
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
    assert summary["extraction_mode"] in {"fixture_payload_surrogate", "local_ocr"}
    if not summary["ocr_provider"]["available"]:
        assert summary["extraction_mode"] == "fixture_payload_surrogate"
        assert "skip_reason" in summary["ocr_provider"]
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


def test_package_exposes_synthetic_draft_extraction_script() -> None:
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))

    assert package["scripts"]["test:synthetic-draft-extraction"] == (
        "python scripts/verify-synthetic-draft-extraction.py --json"
    )
    assert "npm run test:synthetic-draft-extraction" in package["scripts"]["verify"]
