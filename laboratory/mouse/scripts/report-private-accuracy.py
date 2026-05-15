from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts" / "verify-real-photo-pilot.py"

BOUNDARY = "review item / sanitized private accuracy report"
RESULT_INPUT_LAYER = "review item / private accuracy scoring input"

FIELD_FAMILIES = {
    "mouse_ids_or_note_lines": {
        "label": "Mouse IDs and note-line continuity",
        "threshold": 0.95,
    },
    "card_type_review_routing": {
        "label": "Card type and review routing",
        "threshold": 1.0,
    },
    "sex_count_dob": {
        "label": "Sex/count and DOB/date handling",
        "threshold": 0.9,
    },
    "mating_litter_context": {
        "label": "Mating/litter context",
        "threshold": 0.9,
    },
    "export_provenance": {
        "label": "Export provenance",
        "threshold": 1.0,
    },
}

PASSING_STATUSES = {"exact", "corrected"}
SOURCE_IMAGE_QUALITY_BUCKETS = {"clear", "acceptable", "weak", "poor", "cropped", "unreadable", "unknown"}
QUALITY_SIGNAL_BUCKETS = {"strong", "acceptable", "weak", "missing", "unknown"}
AUDIT_TAXONOMY_STATUSES = {"partial_match", "near_miss", "unscorable_due_to_occlusion"}
CANDIDATE_SOURCE_STATUS_KEYS = {
    "local_ocr": ["local_ocr_pre_review_status", "ocr_pre_review_status"],
    "ai": ["ai_pre_review_status"],
    "hybrid": ["hybrid_pre_review_status"],
}
HYBRID_FAILURE_LABELS = {
    "missing_source_trace",
    "numeric_only_note_line",
    "ocr_ai_ear_label_disagreement",
    "ocr_ai_mouse_id_disagreement",
    "ocr_ai_note_line_disagreement",
    "ocr_ai_strike_status_disagreement",
    "parsed_note_line_needs_review",
    "partial_match",
    "near_miss",
    "rule_expected_ear_label_mismatch",
    "unscorable_due_to_occlusion",
    "unknown_note_line_parse",
    "weak_source_or_roi_quality",
}


def load_real_photo_verifier() -> Any:
    spec = importlib.util.spec_from_file_location("verify_real_photo_pilot", VERIFIER_PATH)
    if not spec or not spec.loader:
        raise RuntimeError("Unable to load real-photo pilot verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    return payload


def bool_value(value: Any) -> bool:
    return value is True


def case_ids_from_manifest(manifest: dict[str, Any]) -> list[str]:
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        return []
    return [
        str(case.get("case_id") or "")
        for case in cases
        if isinstance(case, dict) and str(case.get("case_id") or "").strip()
    ]


def expected_case_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id") or "").strip()
        if case_id:
            index[case_id] = case
    return index


def result_case_index(results: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    cases = results.get("cases")
    if not isinstance(cases, list):
        return {}, ["results.cases must be a list"]
    index: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            failures.append("result case must be an object")
            continue
        case_id = str(case.get("case_id") or "").strip()
        if not case_id:
            failures.append("result case_id is required")
            continue
        if case_id in index:
            failures.append(f"duplicate result case_id: {case_id}")
            continue
        index[case_id] = case
    return index, failures


def validate_results_payload(results: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if results.get("layer") != RESULT_INPUT_LAYER:
        failures.append(f"results.layer must be {RESULT_INPUT_LAYER!r}")
    if results.get("canonical") is not False:
        failures.append("results.canonical must be false")
    if not str(results.get("source_policy") or "").strip():
        failures.append("results.source_policy is required")
    _, case_failures = result_case_index(results)
    failures.extend(case_failures)
    return failures


def score_is_passing(score: dict[str, Any]) -> bool:
    status = str(score.get("status") or "").strip()
    if status == "exact":
        return True
    if status == "corrected":
        return bool_value(score.get("reviewed_before_apply"))
    return False


def empty_family_score() -> dict[str, Any]:
    return {
        "label": "",
        "threshold": 0.0,
        "evaluated": 0,
        "passed": 0,
        "exact": 0,
        "corrected_before_apply": 0,
        "missed": 0,
        "not_applicable": 0,
        "unreviewed_high_risk_misses": 0,
        "traceability_failures": 0,
        "rate": 0.0,
        "status": "failed",
    }


def calculate_family_scores(
    *,
    manifest_case_ids: list[str],
    result_cases: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    family_scores = {}
    for family, definition in FIELD_FAMILIES.items():
        summary = empty_family_score()
        summary["label"] = definition["label"]
        summary["threshold"] = definition["threshold"]
        for case_id in manifest_case_ids:
            result = result_cases.get(case_id)
            score = {}
            if isinstance(result, dict):
                field_scores = result.get("field_scores")
                if isinstance(field_scores, dict) and isinstance(field_scores.get(family), dict):
                    score = field_scores[family]
            has_score = bool(score)
            status = str(score.get("status") or "missed").strip()
            if status == "not_applicable":
                summary["not_applicable"] += 1
                continue
            summary["evaluated"] += 1
            if status == "exact":
                summary["exact"] += 1
            if status == "corrected" and bool_value(score.get("reviewed_before_apply")):
                summary["corrected_before_apply"] += 1
            if status == "missed" or status not in PASSING_STATUSES:
                summary["missed"] += 1
            if has_score and not bool_value(score.get("traceable")):
                summary["traceability_failures"] += 1
            if has_score and status == "missed" and not bool_value(score.get("reviewed_before_apply")):
                summary["unreviewed_high_risk_misses"] += 1
            if score and score_is_passing(score):
                summary["passed"] += 1
        if summary["evaluated"]:
            summary["rate"] = round(summary["passed"] / summary["evaluated"], 4)
        threshold_met = summary["rate"] >= definition["threshold"]
        high_risk_clean = summary["unreviewed_high_risk_misses"] == 0
        summary["status"] = "passed" if threshold_met and high_risk_clean else "failed"
        family_scores[family] = summary
    return family_scores


def count_failure_labels(result_cases: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in result_cases.values():
        labels = result.get("failure_labels", [])
        if not isinstance(labels, list):
            continue
        for label in labels:
            key = str(label).strip()
            if key:
                counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def empty_hybrid_metric_counts() -> dict[str, Any]:
    return {
        "scored_note_line_cases": 0,
        "pre_review_exact": 0,
        "auto_candidate_usable_without_edit": 0,
        "review_corrections": 0,
        "local_ocr_pre_review_exact": 0,
        "exact_or_corrected_before_apply": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "partial_matches": 0,
        "near_misses": 0,
        "unscorable_due_to_occlusion": 0,
        "reviewer_overrides": 0,
        "invalid_hybrid_evaluator_inputs": 0,
        "failure_label_counts": {},
    }


def hybrid_rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def finalize_hybrid_metric_counts(counts: dict[str, Any]) -> dict[str, Any]:
    total = int(counts["scored_note_line_cases"])
    pre_review_exact_rate = hybrid_rate(int(counts["pre_review_exact"]), total)
    local_ocr_rate = hybrid_rate(int(counts["local_ocr_pre_review_exact"]), total)
    invalid_inputs = int(counts["invalid_hybrid_evaluator_inputs"])
    return {
        "status": "invalid_input" if invalid_inputs else "passed",
        "scored_note_line_cases": total,
        "pre_review_exact_rate": pre_review_exact_rate,
        "auto_candidate_usable_without_edit_rate": hybrid_rate(
            int(counts["auto_candidate_usable_without_edit"]), total
        ),
        "review_correction_rate": hybrid_rate(int(counts["review_corrections"]), total),
        "local_ocr_pre_review_exact_rate": local_ocr_rate,
        "local_ocr_to_hybrid_delta": hybrid_rate(
            int(counts["pre_review_exact"]) - int(counts["local_ocr_pre_review_exact"]),
            total,
        ),
        "exact_or_corrected_before_apply_rate": hybrid_rate(
            int(counts["exact_or_corrected_before_apply"]), total
        ),
        "false_positive_count": int(counts["false_positives"]),
        "false_positive_rate": hybrid_rate(int(counts["false_positives"]), total),
        "false_negative_count": int(counts["false_negatives"]),
        "false_negative_rate": hybrid_rate(int(counts["false_negatives"]), total),
        "partial_match_count": int(counts["partial_matches"]),
        "partial_match_rate": hybrid_rate(int(counts["partial_matches"]), total),
        "near_miss_count": int(counts["near_misses"]),
        "near_miss_rate": hybrid_rate(int(counts["near_misses"]), total),
        "unscorable_due_to_occlusion_count": int(counts["unscorable_due_to_occlusion"]),
        "unscorable_due_to_occlusion_rate": hybrid_rate(
            int(counts["unscorable_due_to_occlusion"]), total
        ),
        "reviewer_override_count": int(counts["reviewer_overrides"]),
        "reviewer_override_rate": hybrid_rate(int(counts["reviewer_overrides"]), total),
        "invalid_hybrid_evaluator_inputs": invalid_inputs,
        "failure_label_counts": dict(sorted(counts["failure_label_counts"].items())),
    }


def sanitized_hybrid_failure_label(value: Any) -> str:
    label = str(value or "").strip()
    return label if label in HYBRID_FAILURE_LABELS else "unknown_failure_label"


def add_audit_status_counts(counts: dict[str, Any], status: str) -> None:
    if status == "partial_match":
        counts["partial_matches"] += 1
    elif status == "near_miss":
        counts["near_misses"] += 1
    elif status == "unscorable_due_to_occlusion":
        counts["unscorable_due_to_occlusion"] += 1


def add_hybrid_metric_case(counts: dict[str, Any], note_case: dict[str, Any]) -> None:
    counts["scored_note_line_cases"] += 1
    hybrid_status = str(note_case.get("hybrid_pre_review_status") or "").strip()
    local_status = str(note_case.get("local_ocr_pre_review_status") or "").strip()
    expected_candidate_present = note_case.get("expected_candidate_present") is not False
    if hybrid_status == "exact":
        counts["pre_review_exact"] += 1
    add_audit_status_counts(counts, hybrid_status)
    if local_status == "exact":
        counts["local_ocr_pre_review_exact"] += 1
    if bool_value(note_case.get("auto_candidate_usable_without_edit")):
        counts["auto_candidate_usable_without_edit"] += 1
    if bool_value(note_case.get("review_correction_required")):
        counts["review_corrections"] += 1
    if hybrid_status == "exact" or (
        bool_value(note_case.get("review_correction_required"))
        and bool_value(note_case.get("reviewed_before_apply"))
    ):
        counts["exact_or_corrected_before_apply"] += 1
    if hybrid_status == "false_positive" or bool_value(note_case.get("hybrid_false_positive")):
        counts["false_positives"] += 1
    if (
        hybrid_status in {"missed", "false_negative"}
        and expected_candidate_present
    ) or bool_value(note_case.get("hybrid_false_negative")):
        counts["false_negatives"] += 1
    if bool_value(note_case.get("reviewer_override")):
        counts["reviewer_overrides"] += 1
    labels = note_case.get("failure_labels", [])
    if isinstance(labels, list):
        for label in labels:
            key = str(label).strip()
            if key:
                sanitized = sanitized_hybrid_failure_label(key)
                counts["failure_label_counts"][sanitized] = counts["failure_label_counts"].get(sanitized, 0) + 1


def add_invalid_hybrid_metric_input(counts: dict[str, Any]) -> None:
    counts["invalid_hybrid_evaluator_inputs"] += 1


def sanitized_bucket(value: Any, allowed: set[str]) -> str:
    normalized = str(value or "unknown").strip().lower()
    return normalized if normalized in allowed else "unknown"


def first_status_value(note_case: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = str(note_case.get(key) or "").strip()
        if value:
            return value
    return ""


def add_candidate_source_metric_case(
    counts: dict[str, Any],
    note_case: dict[str, Any],
    *,
    status_keys: list[str],
) -> None:
    counts["scored_note_line_cases"] += 1
    status = first_status_value(note_case, status_keys)
    expected_candidate_present = note_case.get("expected_candidate_present") is not False
    if status == "exact":
        counts["pre_review_exact"] += 1
    add_audit_status_counts(counts, status)
    if bool_value(note_case.get("auto_candidate_usable_without_edit")) and status == "exact":
        counts["auto_candidate_usable_without_edit"] += 1
    if bool_value(note_case.get("review_correction_required")):
        counts["review_corrections"] += 1
    if status == "exact" or (
        bool_value(note_case.get("review_correction_required"))
        and bool_value(note_case.get("reviewed_before_apply"))
    ):
        counts["exact_or_corrected_before_apply"] += 1
    if status == "false_positive":
        counts["false_positives"] += 1
    if status in {"missed", "false_negative"} and expected_candidate_present:
        counts["false_negatives"] += 1
    if bool_value(note_case.get("reviewer_override")):
        counts["reviewer_overrides"] += 1


def sanitized_rule_snapshot_hash(note_case: dict[str, Any]) -> str:
    value = note_case.get("rule_snapshot_hash")
    if not value:
        rule_candidate = note_case.get("rule_candidate")
        if isinstance(rule_candidate, dict):
            rule_snapshot = rule_candidate.get("rule_snapshot")
            if isinstance(rule_snapshot, dict):
                value = rule_snapshot.get("rule_hash")
    text_value = str(value or "").strip()
    if (
        6 <= len(text_value) <= 128
        and not any(marker in text_value for marker in (":", "/", "\\", " "))
        and all(ch.isalnum() or ch in {"_", "-"} for ch in text_value)
    ):
        return text_value
    return "unknown_rule_hash"


def hybrid_note_line_evaluator_metrics(result_cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    totals = empty_hybrid_metric_counts()
    by_source_quality: dict[str, dict[str, Any]] = {}
    by_roi_alignment: dict[str, dict[str, Any]] = {}
    by_line_segmentation: dict[str, dict[str, Any]] = {}
    by_candidate_source: dict[str, dict[str, Any]] = {
        source: empty_hybrid_metric_counts()
        for source in CANDIDATE_SOURCE_STATUS_KEYS
    }
    by_rule_snapshot: dict[str, dict[str, Any]] = {}

    for result in result_cases.values():
        evaluator = result.get("hybrid_note_line_evaluator")
        if evaluator is None:
            continue
        if not isinstance(evaluator, dict):
            add_invalid_hybrid_metric_input(totals)
            continue
        scored_cases = evaluator.get("scored_cases")
        if not isinstance(scored_cases, list):
            add_invalid_hybrid_metric_input(totals)
            continue
        for note_case in scored_cases:
            if not isinstance(note_case, dict):
                add_invalid_hybrid_metric_input(totals)
                continue
            add_hybrid_metric_case(totals, note_case)
            source_bucket = sanitized_bucket(
                note_case.get("source_image_quality_bucket", note_case.get("source_image_quality")),
                SOURCE_IMAGE_QUALITY_BUCKETS,
            )
            roi_bucket = sanitized_bucket(note_case.get("roi_alignment_bucket"), QUALITY_SIGNAL_BUCKETS)
            line_bucket = sanitized_bucket(note_case.get("line_segmentation_bucket"), QUALITY_SIGNAL_BUCKETS)
            rule_hash = sanitized_rule_snapshot_hash(note_case)
            add_hybrid_metric_case(
                by_source_quality.setdefault(source_bucket, empty_hybrid_metric_counts()),
                note_case,
            )
            add_hybrid_metric_case(
                by_roi_alignment.setdefault(roi_bucket, empty_hybrid_metric_counts()),
                note_case,
            )
            add_hybrid_metric_case(
                by_line_segmentation.setdefault(line_bucket, empty_hybrid_metric_counts()),
                note_case,
            )
            add_hybrid_metric_case(
                by_rule_snapshot.setdefault(rule_hash, empty_hybrid_metric_counts()),
                note_case,
            )
            for source, status_keys in CANDIDATE_SOURCE_STATUS_KEYS.items():
                add_candidate_source_metric_case(
                    by_candidate_source[source],
                    note_case,
                    status_keys=status_keys,
                )

    summary = finalize_hybrid_metric_counts(totals)
    summary["candidate_source_metrics"] = {
        key: finalize_hybrid_metric_counts(value)
        for key, value in sorted(by_candidate_source.items())
    }
    summary["rule_snapshot_breakdown"] = {
        key: finalize_hybrid_metric_counts(value)
        for key, value in sorted(by_rule_snapshot.items())
    }
    summary["source_image_quality_breakdown"] = {
        key: finalize_hybrid_metric_counts(value)
        for key, value in sorted(by_source_quality.items())
    }
    summary["roi_alignment_breakdown"] = {
        key: finalize_hybrid_metric_counts(value)
        for key, value in sorted(by_roi_alignment.items())
    }
    summary["line_segmentation_breakdown"] = {
        key: finalize_hybrid_metric_counts(value)
        for key, value in sorted(by_line_segmentation.items())
    }
    return summary


def workflow_metrics(results: dict[str, Any], matched_case_count: int) -> dict[str, Any]:
    metrics = results.get("workflow_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    return {
        "photos_uploaded": int(metrics.get("photos_uploaded") or matched_case_count),
        "photos_with_extraction_draft": int(metrics.get("photos_with_extraction_draft") or 0),
        "manual_transcriptions": int(metrics.get("manual_transcriptions") or 0),
        "review_items_opened": int(metrics.get("review_items_opened") or 0),
        "review_items_corrected": int(metrics.get("review_items_corrected") or 0),
        "review_items_accepted_without_correction": int(
            metrics.get("review_items_accepted_without_correction") or 0
        ),
        "xlsx_exports_generated": int(metrics.get("xlsx_exports_generated") or 0),
    }


def reviewer_scoring_provenance(results: dict[str, Any]) -> dict[str, Any]:
    provenance = results.get("reviewer_scoring_provenance")
    if not isinstance(provenance, dict):
        return {
            "method": "unspecified",
            "approved_by_operator": False,
            "approval_scope": "",
            "raw_payload_policy": "omitted_from_sanitized_report",
        }
    method = str(provenance.get("method") or "unspecified").strip()
    if method not in {"manual_operator_review", "model_vision_reviewer_scoring", "mixed_manual_and_model_review"}:
        method = "other_sanitized_review_method"
    approval_scope = str(provenance.get("approval_scope") or "").strip()
    if len(approval_scope) > 120 or any(marker in approval_scope for marker in (":", "\\", "/")):
        approval_scope = "sanitized_scope"
    return {
        "method": method,
        "approved_by_operator": provenance.get("approved_by_operator") is True,
        "approval_scope": approval_scope,
        "raw_payload_policy": "omitted_from_sanitized_report",
    }


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percent
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return round(ordered[lower], 2)
    fraction = index - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 2)


def workload_summary(result_cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    seconds = [
        float(case["review_seconds"])
        for case in result_cases.values()
        if isinstance(case.get("review_seconds"), (int, float))
    ]
    manual_count = len(
        [case for case in result_cases.values() if bool_value(case.get("manual_transcription_required"))]
    )
    total = len(result_cases)
    manual_rate = round(manual_count / total, 4) if total else 0.0
    return {
        "median_review_seconds": percentile(seconds, 0.5),
        "p90_review_seconds": percentile(seconds, 0.9),
        "manual_transcription_count": manual_count,
        "manual_transcription_rate": manual_rate,
        "status": "passed"
        if (
            (not seconds or (percentile(seconds, 0.5) or 0) <= 240)
            and (not seconds or (percentile(seconds, 0.9) or 0) <= 480)
            and manual_rate <= 0.4
        )
        else "needs_narrow_rerun",
    }


def build_hard_gates(
    *,
    validation: dict[str, Any],
    manifest_index: dict[str, dict[str, Any]],
    result_cases: dict[str, dict[str, Any]],
    missing_case_count: int,
    family_scores: dict[str, dict[str, Any]],
    hybrid_metrics: dict[str, Any],
    result_validation_failures: list[str],
) -> dict[str, dict[str, Any]]:
    all_source_preserved = (
        missing_case_count == 0
        and all(bool_value(case.get("source_preserved")) for case in result_cases.values())
    )
    traceability_failures = sum(
        int(summary["traceability_failures"]) for summary in family_scores.values()
    )
    unresolved_blockers = len(
        [case for case in result_cases.values() if bool_value(case.get("unresolved_must_review_at_export"))]
    )
    expected_blocking_failures = 0
    review_level_failures = 0
    for case_id, expected in manifest_index.items():
        result = result_cases.get(case_id)
        if result is None:
            continue
        expected_review = str(expected.get("expected_review_level") or "")
        actual_review = str(result.get("actual_review_level") or "")
        if expected_review and actual_review != expected_review:
            review_level_failures += 1
        if bool_value(expected.get("expected_export_blocking")) and not bool_value(
            result.get("export_blocked_until_resolved")
        ):
            expected_blocking_failures += 1
    silent_overwrites = len(
        [case for case in result_cases.values() if bool_value(case.get("silent_overwrite"))]
    )
    accuracy_failed = [
        family
        for family, summary in family_scores.items()
        if summary.get("status") != "passed"
    ]

    gates = {
        "private_data_containment": {
            "status": "passed" if not result_validation_failures else "failed",
            "details": "Reporter output contains sanitized aggregates only.",
        },
        "manifest_validation": {
            "status": "passed" if validation.get("status") == "passed" else "failed",
            "failed_checks": int(validation.get("failed") or 0),
        },
        "source_preservation": {
            "status": "passed" if all_source_preserved else "failed",
            "missing_or_unpreserved_cases": missing_case_count
            + len([case for case in result_cases.values() if not bool_value(case.get("source_preserved"))]),
        },
        "traceability": {
            "status": "passed"
            if missing_case_count == 0 and traceability_failures == 0
            else "failed",
            "traceability_failures": traceability_failures,
            "missing_result_cases": missing_case_count,
        },
        "review_blocking": {
            "status": "passed"
            if unresolved_blockers == 0 and expected_blocking_failures == 0 and review_level_failures == 0
            else "failed",
            "unresolved_must_review_at_export": unresolved_blockers,
            "expected_blocking_failures": expected_blocking_failures,
            "review_level_failures": review_level_failures,
        },
        "silent_overwrite_prevention": {
            "status": "passed" if silent_overwrites == 0 else "failed",
            "silent_overwrite_count": silent_overwrites,
        },
        "accuracy_thresholds": {
            "status": "passed" if not accuracy_failed and missing_case_count == 0 else "failed",
            "failed_families": accuracy_failed,
            "missing_result_cases": missing_case_count,
        },
        "hybrid_note_line_evaluator_input": {
            "status": "passed"
            if int(hybrid_metrics.get("invalid_hybrid_evaluator_inputs") or 0) == 0
            else "failed",
            "invalid_hybrid_evaluator_inputs": int(
                hybrid_metrics.get("invalid_hybrid_evaluator_inputs") or 0
            ),
        },
    }
    return gates


def go_decision(hard_gates: dict[str, dict[str, Any]], workload: dict[str, Any]) -> str:
    if any(gate.get("status") != "passed" for gate in hard_gates.values()):
        return "no_go"
    if workload.get("status") != "passed":
        return "narrow_rerun"
    return "go"


def build_report(*, manifest_path: Path | str, results_path: Path | str) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    results_path = Path(results_path)
    verifier = load_real_photo_verifier()
    manifest = verifier.load_manifest(manifest_path)
    validation = verifier.validate_manifest(manifest, manifest_path)
    results = load_json_object(results_path)
    result_validation_failures = validate_results_payload(results)
    result_cases, _ = result_case_index(results)
    manifest_case_ids = case_ids_from_manifest(manifest)
    manifest_index = expected_case_index(manifest)
    missing_case_ids = [case_id for case_id in manifest_case_ids if case_id not in result_cases]
    extra_case_ids = sorted([case_id for case_id in result_cases if case_id not in manifest_index])
    matched_result_cases = {
        case_id: result_cases[case_id]
        for case_id in manifest_case_ids
        if case_id in result_cases
    }
    family_scores = calculate_family_scores(
        manifest_case_ids=manifest_case_ids,
        result_cases=matched_result_cases,
    )
    hybrid_metrics = hybrid_note_line_evaluator_metrics(matched_result_cases)
    workload = workload_summary(matched_result_cases)
    hard_gates = build_hard_gates(
        validation=validation,
        manifest_index=manifest_index,
        result_cases=matched_result_cases,
        missing_case_count=len(missing_case_ids),
        family_scores=family_scores,
        hybrid_metrics=hybrid_metrics,
        result_validation_failures=result_validation_failures,
    )
    decision = go_decision(hard_gates, workload)
    status = "passed" if decision == "go" else "failed"
    return {
        "status": status,
        "decision": decision,
        "boundary": BOUNDARY,
        "canonical": False,
        "case_count": len(manifest_case_ids),
        "matched_case_count": len(matched_result_cases),
        "missing_result_case_count": len(missing_case_ids),
        "extra_result_case_count": len(extra_case_ids),
        "coverage": validation.get("coverage", {}),
        "workflow_metrics": workflow_metrics(results, len(matched_result_cases)),
        "reviewer_scoring_provenance": reviewer_scoring_provenance(results),
        "workload": workload,
        "field_family_scores": family_scores,
        "hybrid_note_line_evaluator_metrics": hybrid_metrics,
        "hard_gates": hard_gates,
        "failure_taxonomy_counts": count_failure_labels(matched_result_cases),
        "result_validation_failures": len(result_validation_failures),
    }


def markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def hybrid_breakdown_rows(breakdown: dict[str, dict[str, Any]]) -> list[str]:
    if not breakdown:
        return [markdown_table_row(["none", 0, "0.00%", "0.00%"])]
    return [
        markdown_table_row(
            [
                bucket,
                metrics["scored_note_line_cases"],
                f"{metrics['pre_review_exact_rate']:.2%}",
                f"{metrics['review_correction_rate']:.2%}",
            ]
        )
        for bucket, metrics in breakdown.items()
    ]


def hybrid_candidate_source_rows(breakdown: dict[str, dict[str, Any]]) -> list[str]:
    if not breakdown:
        return [markdown_table_row(["none", 0, "0.00%", "0.00%", "0.00%", "0.00%"])]
    return [
        markdown_table_row(
            [
                source,
                metrics["scored_note_line_cases"],
                f"{metrics['pre_review_exact_rate']:.2%}",
                f"{metrics['false_positive_rate']:.2%}",
                f"{metrics['false_negative_rate']:.2%}",
                f"{metrics['reviewer_override_rate']:.2%}",
            ]
        )
        for source, metrics in breakdown.items()
    ]


def hybrid_rule_snapshot_rows(breakdown: dict[str, dict[str, Any]]) -> list[str]:
    if not breakdown:
        return [markdown_table_row(["none", 0, "0.00%", 0, 0, 0])]
    return [
        markdown_table_row(
            [
                rule_hash,
                metrics["scored_note_line_cases"],
                f"{metrics['pre_review_exact_rate']:.2%}",
                metrics["false_positive_count"],
                metrics["false_negative_count"],
                metrics["reviewer_override_count"],
            ]
        )
        for rule_hash, metrics in breakdown.items()
    ]


def audit_taxonomy_rows(metrics: dict[str, Any]) -> list[str]:
    return [
        markdown_table_row(["partial match", metrics["partial_match_count"], f"{metrics['partial_match_rate']:.2%}"]),
        markdown_table_row(["near miss", metrics["near_miss_count"], f"{metrics['near_miss_rate']:.2%}"]),
        markdown_table_row([
            "unscorable due to occlusion",
            metrics["unscorable_due_to_occlusion_count"],
            f"{metrics['unscorable_due_to_occlusion_rate']:.2%}",
        ]),
    ]


def build_markdown_report(*, run_label: str, summary: dict[str, Any]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    field_rows = []
    for family in FIELD_FAMILIES:
        score = summary["field_family_scores"][family]
        field_rows.append(
            markdown_table_row(
                [
                    score["label"],
                    score["status"],
                    f"{score['rate']:.2%}",
                    f"{score['threshold']:.0%}",
                    score["passed"],
                    score["evaluated"],
                    score["unreviewed_high_risk_misses"],
                ]
            )
        )
    gate_rows = [
        markdown_table_row([name, gate.get("status", "")])
        for name, gate in summary["hard_gates"].items()
    ]
    taxonomy = summary.get("failure_taxonomy_counts", {})
    taxonomy_rows = [
        markdown_table_row([label, count])
        for label, count in taxonomy.items()
    ] or [markdown_table_row(["none", 0])]
    metrics = summary["workflow_metrics"]
    hybrid = summary["hybrid_note_line_evaluator_metrics"]
    source_breakdown_rows = hybrid_breakdown_rows(hybrid["source_image_quality_breakdown"])
    roi_breakdown_rows = hybrid_breakdown_rows(hybrid["roi_alignment_breakdown"])
    line_breakdown_rows = hybrid_breakdown_rows(hybrid["line_segmentation_breakdown"])
    candidate_source_rows = hybrid_candidate_source_rows(hybrid["candidate_source_metrics"])
    rule_snapshot_rows = hybrid_rule_snapshot_rows(hybrid["rule_snapshot_breakdown"])
    audit_rows = audit_taxonomy_rows(hybrid)
    provenance = summary.get("reviewer_scoring_provenance", {})
    return f"""# Private Accuracy Scoring Report - {run_label}

Layer classification: {BOUNDARY}.

Canonical: false.

Generated at: {generated_at}

This report was generated from local-only private scoring inputs. It intentionally omits private photo paths, raw cage-card text, raw OCR/AI payloads, generated workbook paths, local database paths, backup paths, and case-level animal-room details.

## Reviewer scoring provenance

| Field | Sanitized value |
| --- | --- |
| Method | {provenance.get('method', 'unspecified')} |
| Approved by operator | {provenance.get('approved_by_operator', False)} |
| Approval scope | {provenance.get('approval_scope', '')} |
| Raw payload policy | {provenance.get('raw_payload_policy', 'omitted_from_sanitized_report')} |

## Go / No-Go

| Check | Result |
| --- | --- |
| Go/no-go decision | {summary['decision']} |
| Manifest cases | {summary['case_count']} |
| Matched scoring cases | {summary['matched_case_count']} |
| Missing scoring cases | {summary['missing_result_case_count']} |
| Extra scoring cases ignored | {summary['extra_result_case_count']} |

## Field-Family Accuracy

| Field family | Status | Rate | Threshold | Passed | Evaluated | Unreviewed high-risk misses |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(field_rows)}

## Hard Gates

| Gate | Status |
| --- | --- |
{chr(10).join(gate_rows)}

## Workflow Metrics

| Metric | Sanitized value |
| --- | ---: |
| Photos uploaded | {metrics['photos_uploaded']} |
| Photos with extraction draft | {metrics['photos_with_extraction_draft']} |
| Manual transcriptions | {metrics['manual_transcriptions']} |
| Review items opened | {metrics['review_items_opened']} |
| Review items corrected | {metrics['review_items_corrected']} |
| Review items accepted without correction | {metrics['review_items_accepted_without_correction']} |
| XLSX exports generated | {metrics['xlsx_exports_generated']} |

## Hybrid Note-Line Evaluator Metrics

| Metric | Sanitized value |
| --- | ---: |
| Scored note-line cases | {hybrid['scored_note_line_cases']} |
| Pre-review exact rate | {hybrid['pre_review_exact_rate']:.2%} |
| Auto candidate usable without edit rate | {hybrid['auto_candidate_usable_without_edit_rate']:.2%} |
| Review correction rate | {hybrid['review_correction_rate']:.2%} |
| Local OCR pre-review exact rate | {hybrid['local_ocr_pre_review_exact_rate']:.2%} |
| Local OCR to hybrid delta | {hybrid['local_ocr_to_hybrid_delta']:.2%} |
| Exact or corrected before apply rate | {hybrid['exact_or_corrected_before_apply_rate']:.2%} |
| False positive rate | {hybrid['false_positive_rate']:.2%} |
| False negative rate | {hybrid['false_negative_rate']:.2%} |
| Reviewer override rate | {hybrid['reviewer_override_rate']:.2%} |

### Audit taxonomy

| Taxonomy | Count | Rate |
| --- | ---: | ---: |
{chr(10).join(audit_rows)}

### Candidate source comparison

| Candidate source | Scored | Pre-review exact rate | False positive rate | False negative rate | Reviewer override rate |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(candidate_source_rows)}

### Rule snapshot/hash breakdown

| Rule hash | Scored | Pre-review exact rate | False positives | False negatives | Reviewer overrides |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rule_snapshot_rows)}

### Source image quality breakdown

| Bucket | Scored | Pre-review exact rate | Review correction rate |
| --- | ---: | ---: | ---: |
{chr(10).join(source_breakdown_rows)}

### ROI alignment breakdown

| Bucket | Scored | Pre-review exact rate | Review correction rate |
| --- | ---: | ---: | ---: |
{chr(10).join(roi_breakdown_rows)}

### Line segmentation breakdown

| Bucket | Scored | Pre-review exact rate | Review correction rate |
| --- | ---: | ---: | ---: |
{chr(10).join(line_breakdown_rows)}

## Reviewer Workload

| Criterion | Sanitized value |
| --- | ---: |
| Median review seconds | {summary['workload']['median_review_seconds']} |
| 90th percentile review seconds | {summary['workload']['p90_review_seconds']} |
| Manual transcription count | {summary['workload']['manual_transcription_count']} |
| Manual transcription rate | {summary['workload']['manual_transcription_rate']:.2%} |
| Workload status | {summary['workload']['status']} |

## Failure Taxonomy Counts

| Failure label | Count |
| --- | ---: |
{chr(10).join(taxonomy_rows)}

## Sanitization Checklist

- [ ] No private source photo paths.
- [ ] No raw copied-photo OCR/AI payloads.
- [ ] No raw expected field text copied from the private manifest.
- [ ] No generated workbook paths.
- [ ] No local database or backup folder paths.
- [ ] No animal-room details beyond sanitized case labels.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score private copied-photo accuracy inputs and emit sanitized aggregates."
    )
    parser.add_argument("--manifest", required=True, help="Private manifest path.")
    parser.add_argument("--results", required=True, help="Private scoring results JSON path.")
    parser.add_argument("--run-label", default="private-accuracy", help="Sanitized report label.")
    parser.add_argument("--output-report", default="", help="Optional sanitized Markdown report path.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary.")
    args = parser.parse_args()

    summary = build_report(manifest_path=Path(args.manifest), results_path=Path(args.results))
    output_report = Path(args.output_report) if args.output_report else None
    if output_report:
        output_report.parent.mkdir(parents=True, exist_ok=True)
        output_report.write_text(
            build_markdown_report(run_label=args.run_label, summary=summary),
            encoding="utf-8",
        )
        summary = {
            **summary,
            "sanitized_report_written": True,
            "sanitized_report_filename": output_report.name,
        }

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"status: {summary['status']}")
        print(f"decision: {summary['decision']}")
        if output_report:
            print(f"sanitized_report_path: {output_report}")
    return 0 if summary.get("decision") in {"go", "narrow_rerun"} else 1


if __name__ == "__main__":
    sys.exit(main())
