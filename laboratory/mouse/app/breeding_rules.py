from __future__ import annotations

from datetime import date
from typing import Any


DEFAULT_BREEDING_RULE_SET: dict[str, Any] = {
    "rule_set_id": "breeding_rule_default_20260509",
    "display_name": "Default breeding operation review rules",
    "thresholds": {
        "no_birth_review_after_days": 60,
        "parent_replacement_review_after_days": 365,
        "litter_separation_due_after_days": 30,
        "litter_separation_overdue_after_days": 45,
        "litter_separation_high_overdue_after_days": 60,
        "schedule_due_soon_window_days": 30,
        "separation_batch_max_dob_span_days": 14,
    },
    "strain_specific_assumptions": [
        {
            "assumption_key": "default_genotype_for_pups",
            "strain_text": "ApoM Tg/Tg",
            "value": "Tg",
            "rule_strength": "adopted_policy",
            "review_required_before_global_use": True,
        }
    ],
}


def infer_cage_type_candidate(evidence_rows: list[dict[str, Any]], signals: dict[str, bool] | None = None) -> dict[str, Any]:
    active_signals = signals or {}
    sexes = {
        str(row.get("normalized_candidate", {}).get("sex") or "").strip().lower()
        for row in evidence_rows
    }
    has_mixed_sex = "male" in sexes and "female" in sexes
    supporting_signals: list[str] = []
    confidence = 0.0
    review_required = True
    review_reason = "Insufficient evidence for cage type."
    candidate_value = "unknown"

    if has_mixed_sex:
        candidate_value = "mating"
        supporting_signals.append("mixed_sex")
        confidence = 0.55
        if active_signals.get("mating_date"):
            supporting_signals.append("mating_date")
            confidence += 0.18
        if active_signals.get("parent_style_rows"):
            supporting_signals.append("parent_style_rows")
            confidence += 0.14
        if active_signals.get("active_litter_evidence"):
            supporting_signals.append("active_litter_evidence")
            confidence += 0.13
        review_required = confidence < 0.7
        review_reason = "" if not review_required else "Mixed-sex evidence lacks mating-specific support."

    return {
        "candidate_type": "cage_type",
        "candidate_value": candidate_value,
        "confidence": round(min(confidence, 0.95), 2),
        "source_evidence_ids": _evidence_ids(evidence_rows),
        "supporting_signals": supporting_signals,
        "weakening_signals": [],
        "review_required": review_required,
        "review_reason": review_reason,
    }


def infer_maintenance_group_candidate(evidence_row: dict[str, Any]) -> dict[str, Any]:
    raw = evidence_row.get("raw", {})
    normalized = evidence_row.get("normalized_candidate", {})
    confidence = _confidence(evidence_row)
    return {
        "candidate_type": "maintenance_group",
        "strain_raw": raw.get("strain", ""),
        "sex_candidate": normalized.get("sex", ""),
        "count_raw": raw.get("count", ""),
        "count_candidate": normalized.get("count"),
        "dob_raw": raw.get("dob", ""),
        "dob_start_candidate": normalized.get("dob_start", ""),
        "dob_end_candidate": normalized.get("dob_end", ""),
        "genotype_counts_raw": raw.get("genotype_counts", {}),
        "source_evidence_ids": _evidence_ids([evidence_row]),
        "confidence": confidence,
        "review_required": confidence < 0.7,
    }


def infer_litter_event_candidate(evidence_row: dict[str, Any], *, in_mating_block: bool) -> dict[str, Any]:
    raw = evidence_row.get("raw", {})
    normalized = evidence_row.get("normalized_candidate", {})
    review_required = not in_mating_block
    review_reason = "" if in_mating_block else "Litter-like label appears outside an identified mating block."
    return {
        "candidate_type": "litter_event",
        "litter_label": normalized.get("litter_label") or raw.get("litter_label", ""),
        "birth_date_raw": raw.get("dob", ""),
        "birth_date_candidate": normalized.get("birth_date", ""),
        "pup_count_raw": raw.get("pup_count", ""),
        "pup_count_candidate": normalized.get("pup_count"),
        "event_status_raw": raw.get("status", ""),
        "event_status_candidate": normalized.get("status", "unknown") if in_mating_block else "unknown",
        "source_evidence_ids": _evidence_ids([evidence_row]),
        "confidence": _confidence(evidence_row),
        "review_required": review_required,
        "review_reason": review_reason,
        "conflicts": ["outside_mating_block"] if review_required else [],
    }


def review_current_pups(
    *,
    pubs_date: str,
    observed_date: str,
    newer_resolved_litter_exists: bool,
    rule_set: dict[str, Any],
) -> dict[str, Any] | None:
    if newer_resolved_litter_exists:
        return None
    age_days = _days_between(pubs_date, observed_date)
    if age_days is None:
        return None
    thresholds = rule_set.get("thresholds", {})
    if age_days < int(thresholds.get("litter_separation_overdue_after_days", 45)):
        return None
    priority = "high" if age_days >= int(thresholds.get("litter_separation_high_overdue_after_days", 60)) else "medium"
    return _review_item(
        issue="Current pups overdue for separation review",
        review_reason="Current pups are older than the adopted separation review threshold.",
        priority=priority,
        metadata={"age_days": age_days, "suggested_actions": ["review_litter", "link_separated_cage", "mark_resolved"]},
    )


def review_parent_replacement(
    *,
    parent_dob: str,
    observed_date: str,
    has_recent_litter: bool,
    rule_set: dict[str, Any],
) -> dict[str, Any] | None:
    age_days = _days_between(parent_dob, observed_date)
    if age_days is None:
        return None
    threshold = int(rule_set.get("thresholds", {}).get("parent_replacement_review_after_days", 365))
    if age_days < threshold:
        return None
    priority = "low" if has_recent_litter else "medium"
    return _review_item(
        issue="Parent replacement review",
        review_reason="Parent is older than the adopted replacement review threshold.",
        priority=priority,
        metadata={"age_days": age_days, "suggested_actions": ["review_parent", "keep_active", "plan_replacement"]},
    )


def apply_strain_assumption(strain_text: str, assumption_key: str, rule_set: dict[str, Any]) -> Any | None:
    normalized_strain = _norm(strain_text)
    for assumption in rule_set.get("strain_specific_assumptions", []):
        if _norm(assumption.get("strain_text", "")) == normalized_strain and assumption.get("assumption_key") == assumption_key:
            return assumption.get("value")
    return None


def review_missing_birth_evidence(
    *,
    mating_date: str,
    observed_date: str,
    has_litter_evidence: bool,
    rule_set: dict[str, Any],
) -> dict[str, Any] | None:
    if has_litter_evidence or not observed_date:
        return None
    age_days = _days_between(mating_date, observed_date)
    if age_days is None:
        return None
    threshold = int(rule_set.get("thresholds", {}).get("no_birth_review_after_days", 60))
    if age_days < threshold:
        return None
    return _review_item(
        issue="No-birth review",
        review_reason="No linked litter/current-pup evidence exists after the adopted review window.",
        priority="medium",
        metadata={"age_days": age_days, "suggested_actions": ["check_source_recency", "confirm_no_birth", "update_litter_evidence"]},
    )


def _confidence(row: dict[str, Any]) -> float:
    try:
        return round(float(row.get("confidence", 0)), 2)
    except (TypeError, ValueError):
        return 0.0


def _evidence_ids(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row["evidence_id"]) for row in rows if row.get("evidence_id")]


def _review_item(issue: str, review_reason: str, priority: str, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue": issue,
        "review_reason": review_reason,
        "priority": priority,
        "assigned_role": "Colony Reviewer",
        "metadata": metadata,
    }


def _days_between(start: str, end: str) -> int | None:
    start_date = _parse_iso_date(start)
    end_date = _parse_iso_date(end)
    if not start_date or not end_date:
        return None
    return (end_date - start_date).days


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())
