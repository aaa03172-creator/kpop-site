from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-real-photo-pilot.py"
EXAMPLE_MANIFEST_PATH = ROOT / "config" / "real_photo_validation_cases.example.json"
READINESS_MANIFEST_PATH = ROOT / "config" / "copied_photo_pilot_readiness_manifest.example.json"


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


def test_copied_photo_pilot_readiness_manifest_passes_privacy_safe_coverage_checks() -> None:
    verifier = load_verifier_module()
    manifest = verifier.load_manifest(READINESS_MANIFEST_PATH)

    summary = verifier.validate_manifest(manifest, READINESS_MANIFEST_PATH)

    assert summary["status"] == "passed"
    assert summary["case_count"] == 20
    assert summary["readiness"]["boundary"] == "review item / pilot readiness check"
    assert summary["readiness"]["status"] == "go"
    assert summary["readiness"]["checks"] == {
        "photo_count": {
            "status": "passed",
            "expected": {"min": 20, "max": 30},
            "actual": 20,
        },
        "card_type_coverage": {
            "status": "passed",
            "required": ["separated", "mating", "unclear", "other"],
            "missing": [],
        },
        "review_level_coverage": {
            "status": "passed",
            "required": ["must_review", "quick_check", "trace_only"],
            "missing": [],
        },
        "export_blocking_expectations": {
            "status": "passed",
            "minimum_blocking": 1,
            "minimum_non_blocking": 1,
            "actual": {"blocking": 10, "non_blocking": 10},
        },
        "backup_restore_evidence": {
            "status": "passed",
            "before_backup_label": "before-20-photo-readiness-example",
            "after_backup_label": "after-20-photo-readiness-example",
            "restore_probe_label": "restore-probe-20-photo-readiness-example",
            "restore_verified": True,
            "overwrite_refusal_verified": True,
        },
    }
    encoded = json.dumps(summary, ensure_ascii=False)
    assert "backup_path" not in encoded
    assert "C:/" not in encoded
    assert "C:\\" not in encoded


def test_private_copied_photo_manifest_reports_no_go_when_readiness_evidence_is_incomplete(tmp_path: Path) -> None:
    verifier = load_verifier_module()
    photo = tmp_path / "pilot_photo_001.jpg"
    photo.write_bytes(b"copied photo placeholder")
    manifest_path = tmp_path / "private-manifest.json"
    manifest = {
        "layer": "review item / test fixture",
        "canonical": False,
        "source_policy": "Local-only copied-photo pilot labels. Do not commit private paths.",
        "readiness_criteria": {
            "photo_count": {"min": 20, "max": 30},
            "required_card_types": ["separated", "mating", "unclear", "other"],
            "required_review_levels": ["must_review", "quick_check", "trace_only"],
            "export_blocking": {"minimum_blocking": 1, "minimum_non_blocking": 1},
            "backup_restore": {
                "before_backup_label": "before-private-pilot",
                "after_backup_label": "",
                "restore_probe_label": "C:/private/restore/probe",
                "restore_verified": False,
                "overwrite_refusal_verified": False,
            },
        },
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
                    "raw_strain_text": "raw text",
                    "mouse_ids_or_note_lines": ["note line"],
                    "sex_count": "M 1",
                    "dob": "unclear",
                    "mating_or_litter_note": "",
                    "expected_review_blockers": [],
                },
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    summary = verifier.validate_manifest(manifest, manifest_path)

    assert summary["status"] == "failed"
    assert summary["readiness"]["status"] == "no_go"
    assert summary["readiness"]["checks"]["photo_count"]["status"] == "failed"
    assert summary["readiness"]["checks"]["card_type_coverage"]["missing"] == ["mating", "unclear", "other"]
    assert summary["readiness"]["checks"]["review_level_coverage"]["missing"] == ["must_review", "trace_only"]
    assert summary["readiness"]["checks"]["export_blocking_expectations"]["status"] == "failed"
    assert summary["readiness"]["checks"]["backup_restore_evidence"]["status"] == "failed"
    failure_text = " | ".join(
        message
        for failure in summary["failures"]
        for message in failure["failures"]
    )
    assert "pilot photo count must be between 20 and 30; found 1" in failure_text
    assert "backup_restore.after_backup_label is required" in failure_text
    assert "backup_restore.restore_probe_label must be a label, not a local path" in failure_text
