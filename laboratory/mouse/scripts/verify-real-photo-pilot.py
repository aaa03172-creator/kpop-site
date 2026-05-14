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
READINESS_BOUNDARY = "review item / pilot readiness check"


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


def redacted_manifest_error(exc: Exception, manifest_path: Path) -> str:
    text = str(exc)
    replacements = {
        str(manifest_path),
        manifest_path.as_posix(),
        repr(str(manifest_path)).strip("'"),
    }
    for replacement in replacements:
        if replacement:
            text = text.replace(replacement, "<private manifest path>")
    return text


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
        failures.append("source_photo_path does not exist: <private source photo path>")

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
        "example_only": bool(case.get("example_only")),
    }, failures


def increment(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def int_setting(value: Any, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default


def list_setting(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def label_looks_like_path(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return any(marker in value for marker in (":", "/", "\\"))


def build_check(status: str, **values: Any) -> dict[str, Any]:
    return {"status": status, **values}


def missing_in_required_order(required: list[str], counts: dict[str, int]) -> list[str]:
    return [item for item in required if item not in counts]


def validate_readiness(
    manifest: dict[str, Any],
    *,
    case_count: int,
    card_type_counts: dict[str, int],
    review_level_counts: dict[str, int],
    export_blocking_counts: dict[str, int],
) -> tuple[dict[str, Any], list[str]]:
    criteria = manifest.get("readiness_criteria")
    if not isinstance(criteria, dict):
        return {
            "boundary": READINESS_BOUNDARY,
            "status": "skipped",
            "checks": {},
        }, []

    failures: list[str] = []
    checks: dict[str, dict[str, Any]] = {}

    photo_count = criteria.get("photo_count")
    if not isinstance(photo_count, dict):
        photo_count = {}
    min_count = int_setting(photo_count.get("min"), 20)
    max_count = int_setting(photo_count.get("max"), 30)
    photo_count_passed = min_count <= case_count <= max_count
    if not photo_count_passed:
        failures.append(f"pilot photo count must be between {min_count} and {max_count}; found {case_count}")
    checks["photo_count"] = build_check(
        "passed" if photo_count_passed else "failed",
        expected={"min": min_count, "max": max_count},
        actual=case_count,
    )

    required_card_types = list_setting(criteria.get("required_card_types"))
    missing_card_types = missing_in_required_order(required_card_types, card_type_counts)
    if missing_card_types:
        failures.append(f"missing required card types: {', '.join(missing_card_types)}")
    checks["card_type_coverage"] = build_check(
        "passed" if not missing_card_types else "failed",
        required=required_card_types,
        missing=missing_card_types,
    )

    required_review_levels = list_setting(criteria.get("required_review_levels"))
    missing_review_levels = missing_in_required_order(required_review_levels, review_level_counts)
    if missing_review_levels:
        failures.append(f"missing required review levels: {', '.join(missing_review_levels)}")
    checks["review_level_coverage"] = build_check(
        "passed" if not missing_review_levels else "failed",
        required=required_review_levels,
        missing=missing_review_levels,
    )

    export_blocking = criteria.get("export_blocking")
    if not isinstance(export_blocking, dict):
        export_blocking = {}
    minimum_blocking = int_setting(export_blocking.get("minimum_blocking"), 1)
    minimum_non_blocking = int_setting(export_blocking.get("minimum_non_blocking"), 1)
    export_blocking_passed = (
        export_blocking_counts["blocking"] >= minimum_blocking
        and export_blocking_counts["non_blocking"] >= minimum_non_blocking
    )
    if not export_blocking_passed:
        failures.append(
            "export blocking expectations require at least "
            f"{minimum_blocking} blocking and {minimum_non_blocking} non-blocking cases"
        )
    checks["export_blocking_expectations"] = build_check(
        "passed" if export_blocking_passed else "failed",
        minimum_blocking=minimum_blocking,
        minimum_non_blocking=minimum_non_blocking,
        actual=export_blocking_counts,
    )

    backup_restore = criteria.get("backup_restore")
    if not isinstance(backup_restore, dict):
        backup_restore = {}
    before_label = str(backup_restore.get("before_backup_label") or "").strip()
    after_label = str(backup_restore.get("after_backup_label") or "").strip()
    restore_label = str(backup_restore.get("restore_probe_label") or "").strip()
    restore_verified = backup_restore.get("restore_verified") is True
    overwrite_refusal_verified = backup_restore.get("overwrite_refusal_verified") is True
    backup_failures: list[str] = []
    for key, value in (
        ("before_backup_label", before_label),
        ("after_backup_label", after_label),
        ("restore_probe_label", restore_label),
    ):
        if not value:
            backup_failures.append(f"backup_restore.{key} is required")
        elif label_looks_like_path(value):
            backup_failures.append(f"backup_restore.{key} must be a label, not a local path")
    if not restore_verified:
        backup_failures.append("backup_restore.restore_verified must be true")
    if not overwrite_refusal_verified:
        backup_failures.append("backup_restore.overwrite_refusal_verified must be true")
    failures.extend(backup_failures)
    checks["backup_restore_evidence"] = build_check(
        "passed" if not backup_failures else "failed",
        before_backup_label=before_label,
        after_backup_label=after_label,
        restore_probe_label=restore_label,
        restore_verified=restore_verified,
        overwrite_refusal_verified=overwrite_refusal_verified,
    )

    return {
        "boundary": READINESS_BOUNDARY,
        "status": "go" if not failures else "no_go",
        "checks": checks,
    }, failures


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
    readiness, readiness_failures = validate_readiness(
        manifest,
        case_count=len(cases),
        card_type_counts=card_type_counts,
        review_level_counts=review_level_counts,
        export_blocking_counts=export_blocking_counts,
    )
    if readiness_failures:
        failures.append({"case_id": "", "failures": readiness_failures})
    status = "passed" if not failures else "failed"
    return {
        "status": status,
        "boundary": manifest.get("layer", ""),
        "canonical": manifest.get("canonical", None),
        "source_policy": manifest.get("source_policy", ""),
        "manifest": "private manifest path omitted",
        "manifest_filename": manifest_path.name,
        "case_count": len(cases),
        "failed": len(failures),
        "failures": failures,
        "coverage": {
            "card_type_counts": card_type_counts,
            "review_level_counts": review_level_counts,
            "export_blocking_counts": export_blocking_counts,
            "missing_recommended_card_types": missing_card_types,
        },
        "readiness": readiness,
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
            "manifest": "private manifest path omitted",
            "manifest_filename": manifest_path.name,
            "failed": 1,
            "failures": [{"case_id": "", "failures": [redacted_manifest_error(exc, manifest_path)]}],
        }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary.get("status") == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
