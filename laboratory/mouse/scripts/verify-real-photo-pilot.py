from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALID_CARD_TYPES = {"separated", "mating", "unclear", "other"}
VALID_REVIEW_LEVELS = {"must_review", "quick_check", "trace_only"}
REQUIRED_EXPECTED_FIELDS = {
    "raw_strain_text",
    "mouse_ids_or_note_lines",
    "sex_count",
    "dob",
    "mating_or_litter_note",
    "expected_review_blockers",
}


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("manifest root must be a JSON object")
    return payload


def resolve_photo_path(manifest_path: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw_path = Path(value)
    candidates = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append((manifest_path.parent / raw_path).resolve())
        candidates.append((ROOT / raw_path).resolve())
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def empty_text(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip()


def validate_case(case: Any, manifest_path: Path) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    if not isinstance(case, dict):
        return {"case_id": ""}, ["case must be a JSON object"]

    case_id = str(case.get("case_id") or "").strip()
    if not case_id:
        failures.append("case_id is required")

    source_photo_path = case.get("source_photo_path")
    resolved_photo_path = resolve_photo_path(manifest_path, source_photo_path)
    if empty_text(source_photo_path):
        failures.append("source_photo_path is required")
    elif not resolved_photo_path or not resolved_photo_path.exists():
        failures.append(f"source_photo_path does not exist: {source_photo_path}")

    if empty_text(case.get("traceability_label")):
        failures.append("traceability_label is required")

    card_type = str(case.get("card_type") or "").strip()
    if card_type not in VALID_CARD_TYPES:
        failures.append(f"card_type must be one of {sorted(VALID_CARD_TYPES)}")

    review_level = str(case.get("expected_review_level") or "").strip()
    if review_level not in VALID_REVIEW_LEVELS:
        failures.append(f"expected_review_level must be one of {sorted(VALID_REVIEW_LEVELS)}")

    if "expected_export_blocking" not in case or not isinstance(case.get("expected_export_blocking"), bool):
        failures.append("expected_export_blocking boolean is required")

    expected_fields = case.get("expected_fields")
    if not isinstance(expected_fields, dict):
        failures.append("expected_fields object is required")
    else:
        missing_fields = sorted(REQUIRED_EXPECTED_FIELDS.difference(expected_fields.keys()))
        if missing_fields:
            failures.append(f"expected_fields missing: {', '.join(missing_fields)}")
        blockers = expected_fields.get("expected_review_blockers")
        if not isinstance(blockers, list):
            failures.append("expected_fields.expected_review_blockers must be a list")
        note_lines = expected_fields.get("mouse_ids_or_note_lines")
        if not isinstance(note_lines, list):
            failures.append("expected_fields.mouse_ids_or_note_lines must be a list")

    return {
        "case_id": case_id,
        "card_type": card_type,
        "expected_review_level": review_level,
        "expected_export_blocking": bool(case.get("expected_export_blocking")) if "expected_export_blocking" in case else False,
        "source_photo_exists": bool(resolved_photo_path and resolved_photo_path.exists()),
        "source_photo_path": str(resolved_photo_path) if resolved_photo_path else "",
        "example_only": bool(case.get("example_only")),
    }, failures


def increment(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def validate_manifest(manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        cases = []
        failures.append({"case_id": "", "failures": ["cases must be a non-empty list"]})

    if manifest.get("layer") != "review item / test fixture":
        failures.append({"case_id": "", "failures": ["layer must be 'review item / test fixture'"]})
    if manifest.get("canonical") is not False:
        failures.append({"case_id": "", "failures": ["canonical must be false"]})
    if empty_text(manifest.get("source_policy")):
        failures.append({"case_id": "", "failures": ["source_policy is required"]})

    case_summaries: list[dict[str, Any]] = []
    card_type_counts: dict[str, int] = {}
    review_level_counts: dict[str, int] = {}
    export_blocking_counts = {"blocking": 0, "non_blocking": 0}

    for case in cases:
        summary, case_failures = validate_case(case, manifest_path)
        case_summaries.append(summary)
        if summary.get("card_type"):
            increment(card_type_counts, str(summary["card_type"]))
        if summary.get("expected_review_level"):
            increment(review_level_counts, str(summary["expected_review_level"]))
        if summary.get("expected_export_blocking"):
            export_blocking_counts["blocking"] += 1
        else:
            export_blocking_counts["non_blocking"] += 1
        if case_failures:
            failures.append({"case_id": summary.get("case_id", ""), "failures": case_failures})

    missing_card_types = sorted(VALID_CARD_TYPES.difference(card_type_counts.keys()))
    status = "passed" if not failures else "failed"
    return {
        "status": status,
        "boundary": manifest.get("layer", ""),
        "canonical": manifest.get("canonical", None),
        "source_policy": manifest.get("source_policy", ""),
        "manifest": str(manifest_path),
        "case_count": len(cases),
        "failed": len(failures),
        "failures": failures,
        "coverage": {
            "card_type_counts": card_type_counts,
            "review_level_counts": review_level_counts,
            "export_blocking_counts": export_blocking_counts,
            "missing_recommended_card_types": missing_card_types,
        },
        "cases": case_summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a local-only real-photo pilot manifest.")
    parser.add_argument("--manifest", default="config/real_photo_validation_cases.example.json")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()

    try:
        manifest = load_manifest(manifest_path)
        summary = validate_manifest(manifest, manifest_path)
    except Exception as exc:
        summary = {
            "status": "failed",
            "manifest": str(manifest_path),
            "failed": 1,
            "failures": [{"case_id": "", "failures": [str(exc)]}],
        }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary.get("status") == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
