from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = "review item / private real-photo evaluator run pack"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "private_real_photo_hybrid_evaluator_runs"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".webp"}


def sanitized_run_label(value: str) -> str:
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return label or "real-photo-hybrid"


def case_prefix(value: str) -> str:
    prefix = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")
    return prefix or "real_photo_hybrid"


def image_files(source_dir: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in source_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ],
        key=lambda path: path.name.lower(),
    )


def unresolved_field_score() -> dict[str, Any]:
    return {
        "status": "missed",
        "reviewed_before_apply": False,
        "traceable": True,
    }


def manifest_case(photo_path: Path, *, index: int, prefix: str) -> dict[str, Any]:
    case_id = f"{prefix}_{index:03d}"
    return {
        "case_id": case_id,
        "source_photo_path": str(photo_path.resolve()),
        "source_photo_filename": photo_path.name,
        "card_type": "unclear",
        "traceability_label": f"Private real-photo hybrid evaluator run / photo {index:03d}",
        "expected_review_level": "must_review",
        "expected_export_blocking": True,
        "expected_fields": {
            "raw_strain_text": "operator review required",
            "mouse_ids_or_note_lines": [],
            "sex_count": "operator review required",
            "dob": "operator review required",
            "mating_or_litter_note": "",
            "expected_review_blockers": [
                "manual_real_photo_review_required",
                "hybrid_evaluator_scoring_pending",
            ],
        },
    }


def result_template_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "scoring_status": "operator_fill_required",
        "actual_review_level": "must_review",
        "export_blocked_until_resolved": True,
        "unresolved_must_review_at_export": True,
        "source_preserved": True,
        "silent_overwrite": False,
        "review_seconds": 0,
        "manual_transcription_required": True,
        "failure_labels": ["hybrid_evaluator_scoring_pending"],
        "field_scores": {
            "mouse_ids_or_note_lines": unresolved_field_score(),
            "card_type_review_routing": unresolved_field_score(),
            "sex_count_dob": unresolved_field_score(),
            "mating_litter_context": unresolved_field_score(),
            "export_provenance": unresolved_field_score(),
        },
        "hybrid_note_line_evaluator": {
            "boundary": "review item / private accuracy scoring input",
            "scored_cases": [],
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_readme(run_label: str, photo_count: int) -> str:
    return f"""# Real Photo Hybrid Evaluator Run - {run_label}

Local-only private run pack.

Layer classification: {BOUNDARY}.

Canonical: false.

Photo count: {photo_count}

Use the manifest with `scripts/verify-real-photo-pilot.py`, then fill the scoring template after reviewing each source photo in the app. Keep raw photos, private manifest paths, raw OCR/AI text, reviewer notes, and generated exports out of commits.

For each visible note-line case, add a sanitized object under `hybrid_note_line_evaluator.scored_cases` with:

- `hybrid_pre_review_status`: `exact`, `missed`, or `false_positive`
- `local_ocr_pre_review_status`: `exact`, `missed`, or `false_positive`
- `ai_pre_review_status`: `exact`, `missed`, or `false_positive`
- `expected_candidate_present`: true or false
- `auto_candidate_usable_without_edit`: true or false
- `review_correction_required`: true or false
- `reviewer_override`: true or false
- `reviewed_before_apply`: true or false
- `source_image_quality_bucket`: `clear`, `acceptable`, `weak`, `poor`, `cropped`, `unreadable`, or `unknown`
- `roi_alignment_bucket`: `strong`, `acceptable`, `weak`, `missing`, or `unknown`
- `line_segmentation_bucket`: `strong`, `acceptable`, `weak`, `missing`, or `unknown`
- `rule_snapshot_hash`: evaluator rule hash, if present

Do not paste raw note-line text into the sanitized report output.
"""


def build_run_pack(*, source_dir: Path | str, output_dir: Path | str | None, run_label: str) -> dict[str, Any]:
    source_dir = Path(source_dir)
    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError("source_dir must be an existing directory")
    safe_label = sanitized_run_label(run_label)
    output_path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_ROOT / safe_label
    output_path.mkdir(parents=True, exist_ok=True)

    photos = image_files(source_dir)
    prefix = case_prefix(safe_label)
    cases = [
        manifest_case(photo_path, index=index, prefix=prefix)
        for index, photo_path in enumerate(photos, start=1)
    ]
    manifest = {
        "layer": "review item / test fixture",
        "canonical": False,
        "source_policy": (
            "Local-only private real-photo evaluator manifest. Do not commit private photos, "
            "private source paths, raw OCR/AI payloads, or pilot exports."
        ),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cases": cases,
    }
    results_template = {
        "layer": "review item / private accuracy scoring input",
        "canonical": False,
        "source_policy": "Local-only scoring input. Publish aggregates only.",
        "workflow_metrics": {
            "photos_uploaded": len(cases),
            "photos_with_extraction_draft": 0,
            "manual_transcriptions": 0,
            "review_items_opened": 0,
            "review_items_corrected": 0,
            "review_items_accepted_without_correction": 0,
            "xlsx_exports_generated": 0,
        },
        "cases": [result_template_case(case) for case in cases],
    }

    manifest_filename = "real-photo-hybrid-manifest.json"
    results_template_filename = "real-photo-hybrid-scoring-template.json"
    write_json(output_path / manifest_filename, manifest)
    write_json(output_path / results_template_filename, results_template)
    (output_path / "README.md").write_text(build_readme(safe_label, len(cases)), encoding="utf-8")

    return {
        "status": "created",
        "boundary": BOUNDARY,
        "canonical": False,
        "source_dir": "private source directory omitted",
        "output_dir": "private output directory omitted",
        "run_label": safe_label,
        "photo_count": len(cases),
        "manifest_filename": manifest_filename,
        "results_template_filename": results_template_filename,
        "readme_filename": "README.md",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a local-only real-photo hybrid evaluator validation run pack."
    )
    parser.add_argument("--source-dir", required=True, help="Private source photo directory.")
    parser.add_argument("--output-dir", default="", help="Private output directory. Defaults under ignored data/.")
    parser.add_argument("--run-label", default="real-photo-hybrid", help="Sanitized run label.")
    parser.add_argument("--json", action="store_true", help="Print sanitized JSON summary.")
    args = parser.parse_args()

    try:
        summary = build_run_pack(
            source_dir=Path(args.source_dir),
            output_dir=Path(args.output_dir) if args.output_dir else None,
            run_label=args.run_label,
        )
    except Exception as exc:
        summary = {
            "status": "failed",
            "boundary": BOUNDARY,
            "canonical": False,
            "source_dir": "private source directory omitted",
            "output_dir": "private output directory omitted",
            "error": str(exc).replace(str(args.source_dir), "<private source directory>"),
        }
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            print(f"status: {summary['status']}")
            print(f"error: {summary['error']}")
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"status: {summary['status']}")
        print(f"photo_count: {summary['photo_count']}")
        print(f"manifest: {summary['manifest_filename']}")
        print(f"results_template: {summary['results_template_filename']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
