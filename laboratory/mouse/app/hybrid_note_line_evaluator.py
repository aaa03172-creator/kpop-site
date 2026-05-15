from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


RULE_HASH_INPUT_FIELDS = [
    "rule_set_id",
    "display_name",
    "session_date",
    "effective_from",
    "crossed_out_handling",
    "ear_label_sequence",
    "sample_mapping",
    "genotyping_target",
]

CANDIDATE_FIELD_ALIASES = {
    "raw": "raw_line_text",
    "raw_line_text": "raw_line_text",
    "mouse_display_id": "parsed_mouse_display_id",
    "parsed_mouse_display_id": "parsed_mouse_display_id",
    "ear_label_code": "parsed_ear_label_code",
    "parsed_ear_label_code": "parsed_ear_label_code",
    "strike_status": "strike_status",
    "confidence": "confidence",
}

REQUIRED_SOURCE_REF_FIELDS = ["photo_id", "parse_id", "note_item_id", "line_number", "card_snapshot_id"]


def bounded_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number < 0:
        return 0.0
    if number > 1:
        return min(number / 100.0, 1.0)
    return number


def normalized_raw_line(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def build_rule_snapshot(rule_context: dict[str, Any] | None) -> dict[str, Any]:
    context = dict(rule_context or {})
    stable_input = {field: context.get(field) for field in RULE_HASH_INPUT_FIELDS}
    serialized = json.dumps(stable_input, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return {
        "rule_set_id": str(context.get("rule_set_id") or ""),
        "display_name": str(context.get("display_name") or ""),
        "session_date": str(context.get("session_date") or ""),
        "effective_from": str(context.get("effective_from") or ""),
        "crossed_out_handling": str(context.get("crossed_out_handling") or ""),
        "ear_label_sequence": list(context.get("ear_label_sequence") or []),
        "sample_mapping": str(context.get("sample_mapping") or ""),
        "genotyping_target": str(context.get("genotyping_target") or ""),
        "hash_input_fields": list(RULE_HASH_INPUT_FIELDS),
        "rule_hash": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
    }


def rule_interpretation_candidate(strike_status: str, crossed_out_handling: str) -> str:
    strike = str(strike_status or "none").strip().lower()
    handling = str(crossed_out_handling or "review").strip().lower()
    if strike == "none":
        return "active"
    if handling == "dead" and strike in {"single", "double"}:
        return "dead"
    return "review"


def weak_source_quality(source_quality: dict[str, Any]) -> bool:
    image_quality = str(source_quality.get("source_image_quality") or "unknown").lower()
    roi_confidence = bounded_confidence(source_quality.get("roi_alignment_confidence"))
    line_confidence = bounded_confidence(source_quality.get("line_segmentation_confidence"))
    quality_flags = (
        source_quality.get("quality_flags")
        if isinstance(source_quality.get("quality_flags"), list)
        else []
    )
    if image_quality in {"poor", "unreadable", "cropped", "unknown"}:
        return True
    return roi_confidence < 0.7 or line_confidence < 0.7 or bool(quality_flags)


def candidate_payload(candidate: Any, candidate_name: str, conflicts: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if candidate is None:
        payload["raw_line_text"] = ""
        payload["confidence"] = 0.0
        return payload
    if not isinstance(candidate, dict):
        conflicts.append(f"malformed_{candidate_name}_candidate")
        payload["raw_line_text"] = ""
        payload["confidence"] = 0.0
        return payload
    for source_key, output_key in CANDIDATE_FIELD_ALIASES.items():
        if source_key in candidate:
            payload[output_key] = candidate[source_key]
    payload["raw_line_text"] = str(payload.get("raw_line_text") or "")
    payload["confidence"] = bounded_confidence(payload.get("confidence"))
    return payload


def hybrid_candidate_from_parsed(parsed_note_row: dict[str, Any]) -> dict[str, Any]:
    parsed = deepcopy(parsed_note_row)
    return {
        "raw_line_text": str(parsed.get("raw_line_text") or ""),
        "parsed_type": parsed.get("parsed_type"),
        "parsed_mouse_display_id": parsed.get("parsed_mouse_display_id"),
        "parsed_ear_label_raw": parsed.get("parsed_ear_label_raw"),
        "parsed_ear_label_code": parsed.get("parsed_ear_label_code"),
        "parsed_ear_label_confidence": parsed.get("parsed_ear_label_confidence"),
        "parsed_ear_label_review_status": parsed.get("parsed_ear_label_review_status"),
        "parsed_event_date": parsed.get("parsed_event_date"),
        "parsed_count": parsed.get("parsed_count"),
        "confidence": bounded_confidence(parsed.get("confidence")),
        "needs_review": int(parsed.get("needs_review") or 0),
    }


def source_refs_from_parsed(parsed_note_row: dict[str, Any]) -> dict[str, Any]:
    refs: dict[str, Any] = {}
    for key in [
        "photo_id",
        "parse_id",
        "note_item_id",
        "line_number",
        "card_snapshot_id",
        "roi_ref",
        "photo_evidence_id",
    ]:
        value = parsed_note_row.get(key)
        if value not in {None, ""}:
            refs[key] = value
    return refs


def source_refs_complete(source_refs: dict[str, Any]) -> bool:
    return all(source_refs.get(field) not in {None, ""} for field in REQUIRED_SOURCE_REF_FIELDS)


def compare_candidate_field(
    ocr: dict[str, Any],
    ai: dict[str, Any],
    field: str,
    conflict: str,
    conflicts: list[str],
) -> None:
    ocr_value = normalized_raw_line(ocr.get(field))
    ai_value = normalized_raw_line(ai.get(field))
    if ocr_value and ai_value and ocr_value != ai_value:
        conflicts.append(conflict)


def evaluate_note_line_candidate(
    *,
    ocr_candidate: dict[str, Any] | None = None,
    ai_candidate: dict[str, Any] | None = None,
    parsed_note_row: dict[str, Any],
    source_quality: dict[str, Any] | None = None,
    rule_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    conflicts: list[str] = []
    ocr = candidate_payload(ocr_candidate, "ocr", conflicts)
    ai = candidate_payload(ai_candidate, "ai", conflicts)
    source = {
        "source_image_quality": "unknown",
        "roi_alignment_confidence": 0.0,
        "line_segmentation_confidence": 0.0,
        "quality_flags": [],
    }
    if source_quality is None:
        pass
    elif isinstance(source_quality, dict):
        source.update(source_quality)
    else:
        conflicts.append("malformed_source_quality")

    hybrid = hybrid_candidate_from_parsed(parsed_note_row)
    rule_snapshot = build_rule_snapshot(rule_context) if rule_context else None
    source_refs = source_refs_from_parsed(parsed_note_row)
    strike_status = str(
        parsed_note_row.get("raw_strike_status")
        or parsed_note_row.get("strike_status")
        or ocr.get("strike_status")
        or ai.get("strike_status")
        or "none"
    )

    applied_rule_keys: list[str] = []

    ocr_raw = normalized_raw_line(ocr.get("raw_line_text"))
    ai_raw = normalized_raw_line(ai.get("raw_line_text"))
    if ocr_raw and ai_raw:
        if ocr_raw == ai_raw:
            applied_rule_keys.append("ocr_ai_exact_note_line_agreement")
        else:
            conflicts.append("ocr_ai_note_line_disagreement")
    compare_candidate_field(
        ocr,
        ai,
        "parsed_mouse_display_id",
        "ocr_ai_mouse_id_disagreement",
        conflicts,
    )
    compare_candidate_field(
        ocr,
        ai,
        "parsed_ear_label_code",
        "ocr_ai_ear_label_disagreement",
        conflicts,
    )
    compare_candidate_field(ocr, ai, "strike_status", "ocr_ai_strike_status_disagreement", conflicts)

    if weak_source_quality(source):
        conflicts.append("weak_source_or_roi_quality")
    if not source_refs_complete(source_refs):
        conflicts.append("missing_source_trace")

    if hybrid["parsed_type"] == "unlabeled_numeric_note":
        conflicts.append("numeric_only_note_line")
    elif hybrid["parsed_type"] == "unknown":
        conflicts.append("unknown_note_line_parse")
    elif hybrid["needs_review"]:
        conflicts.append("parsed_note_line_needs_review")

    rule_candidate: dict[str, Any] | None = None
    if rule_snapshot:
        expected_ear_label_code = str((rule_context or {}).get("expected_ear_label_code") or "")
        interpreted = rule_interpretation_candidate(strike_status, rule_snapshot["crossed_out_handling"])
        rule_candidate = {
            "rule_snapshot": rule_snapshot,
            "expected_ear_label_code": expected_ear_label_code or None,
            "raw_strike_status": strike_status,
            "default_strike_interpretation": parsed_note_row.get("interpreted_status"),
            "rule_interpretation_candidate": interpreted,
            "rule_interpretation_boundary": "review hint only",
        }
        parsed_code = str(hybrid.get("parsed_ear_label_code") or "")
        if expected_ear_label_code and parsed_code:
            if expected_ear_label_code == parsed_code:
                applied_rule_keys.append("rule_consistency_expected_ear_label_sequence")
            else:
                conflicts.append("rule_expected_ear_label_mismatch")

    must_review = bool(conflicts)
    if not ocr_raw and not ai_raw:
        must_review = True
        conflicts.append("missing_ocr_and_ai_note_line_candidates")

    candidate_confidences = [
        confidence
        for confidence in [
            bounded_confidence(ocr.get("confidence")),
            bounded_confidence(ai.get("confidence")),
            bounded_confidence(hybrid.get("confidence")),
            bounded_confidence(source.get("roi_alignment_confidence")),
            bounded_confidence(source.get("line_segmentation_confidence")),
        ]
        if confidence > 0
    ]
    confidence = min(candidate_confidences) if candidate_confidences else 0.0
    if must_review:
        confidence = min(confidence, 0.69)

    return {
        "candidate_kind": "hybrid_note_line",
        "source_layer": "parsed or intermediate result",
        "ocr_candidate": ocr,
        "ai_candidate": ai,
        "source_quality": source,
        "rule_candidate": rule_candidate,
        "hybrid_candidate": hybrid,
        "applied_rule_keys": applied_rule_keys,
        "conflicts": sorted(set(conflicts)),
        "source_refs": source_refs,
        "confidence": confidence,
        "review_routing": {
            "attention_level": "must_review" if must_review else "quick_check",
            "must_review": must_review,
        },
    }
