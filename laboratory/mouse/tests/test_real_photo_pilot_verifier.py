from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-real-photo-pilot.py"
EXAMPLE_MANIFEST_PATH = ROOT / "config" / "real_photo_validation_cases.example.json"


def load_verifier_module():
    spec = importlib.util.spec_from_file_location("verify_real_photo_pilot", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_real_photo_manifest_passes_without_private_photos() -> None:
    verifier = load_verifier_module()
    manifest = verifier.load_manifest(EXAMPLE_MANIFEST_PATH)

    summary = verifier.validate_manifest(manifest, EXAMPLE_MANIFEST_PATH)

    assert summary["status"] == "passed"
    assert summary["boundary"] == "review item / test fixture"
    assert summary["canonical"] is False
    assert summary["case_count"] == 4
    assert summary["coverage"]["card_type_counts"] == {
        "separated": 1,
        "mating": 1,
        "unclear": 1,
        "other": 1,
    }
    assert summary["coverage"]["export_blocking_counts"] == {
        "blocking": 2,
        "non_blocking": 2,
    }
    assert summary["coverage"]["missing_recommended_card_types"] == []
    assert all(case["source_photo_exists"] for case in summary["cases"])


def test_real_photo_manifest_requires_source_traceability_and_review_policy(tmp_path: Path) -> None:
    verifier = load_verifier_module()
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "layer": "review item / test fixture",
        "canonical": False,
        "source_policy": "Local only.",
        "cases": [
            {
                "case_id": "missing_fields",
                "card_type": "separated",
                "expected_export_blocking": True,
                "expected_fields": {
                    "raw_strain_text": "ApoM",
                    "mouse_ids_or_note_lines": [],
                    "sex_count": "M 1",
                    "dob": "26.04.13",
                    "mating_or_litter_note": "",
                    "expected_review_blockers": [],
                },
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    summary = verifier.validate_manifest(manifest, manifest_path)

    assert summary["status"] == "failed"
    failures = " | ".join(summary["failures"][0]["failures"])
    assert "source_photo_path is required" in failures
    assert "traceability_label is required" in failures
    assert "expected_review_level must be one of" in failures


def test_real_photo_manifest_rejects_missing_photo_path(tmp_path: Path) -> None:
    verifier = load_verifier_module()
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "layer": "review item / test fixture",
        "canonical": False,
        "source_policy": "Local only.",
        "cases": [
            {
                "case_id": "missing_photo",
                "source_photo_path": "does-not-exist.jpg",
                "source_photo_filename": "does-not-exist.jpg",
                "card_type": "unclear",
                "traceability_label": "Pilot A / missing photo",
                "expected_review_level": "must_review",
                "expected_export_blocking": True,
                "expected_fields": {
                    "raw_strain_text": "unclear",
                    "mouse_ids_or_note_lines": [],
                    "sex_count": "unclear",
                    "dob": "unclear",
                    "mating_or_litter_note": "not visible",
                    "expected_review_blockers": ["missing_photo"],
                },
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    summary = verifier.validate_manifest(manifest, manifest_path)

    assert summary["status"] == "failed"
    assert summary["failures"] == [
        {
            "case_id": "missing_photo",
            "failures": ["source_photo_path does not exist: does-not-exist.jpg"],
        }
    ]
