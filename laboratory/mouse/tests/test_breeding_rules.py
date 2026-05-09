from __future__ import annotations

from app.breeding_rules import (
    DEFAULT_BREEDING_RULE_SET,
    apply_strain_assumption,
    infer_cage_type_candidate,
    infer_litter_event_candidate,
    infer_maintenance_group_candidate,
    review_current_pups,
    review_missing_birth_evidence,
    review_parent_replacement,
)


def test_mixed_sex_with_mating_date_and_parent_rows_is_high_confidence_mating_candidate():
    candidate = infer_cage_type_candidate(
        [
            {"normalized_candidate": {"sex": "male"}, "confidence": 0.9},
            {"normalized_candidate": {"sex": "female"}, "confidence": 0.9},
        ],
        signals={"mating_date": True, "parent_style_rows": True},
    )

    assert candidate["candidate_value"] == "mating"
    assert candidate["confidence"] >= 0.8
    assert candidate["review_required"] is False
    assert "mixed_sex" in candidate["supporting_signals"]
    assert "mating_date" in candidate["supporting_signals"]


def test_mixed_sex_without_mating_date_or_litter_evidence_stays_reviewable():
    candidate = infer_cage_type_candidate(
        [
            {"normalized_candidate": {"sex": "male"}, "confidence": 0.9},
            {"normalized_candidate": {"sex": "female"}, "confidence": 0.9},
        ],
        signals={},
    )

    assert candidate["candidate_value"] == "mating"
    assert candidate["confidence"] < 0.7
    assert candidate["review_required"] is True
    assert candidate["review_reason"] == "Mixed-sex evidence lacks mating-specific support."


def test_single_sex_count_dob_row_becomes_maintenance_candidate():
    candidate = infer_maintenance_group_candidate(
        {
            "raw": {"strain": "ApoM Tg/Tg", "sex": "female", "count": "8p", "dob": "25.12.31 - 26.01.10"},
            "normalized_candidate": {"sex": "female", "count": 8, "dob_start": "2025-12-31", "dob_end": "2026-01-10"},
            "confidence": 0.74,
        }
    )

    assert candidate["candidate_type"] == "maintenance_group"
    assert candidate["sex_candidate"] == "female"
    assert candidate["count_candidate"] == 8
    assert candidate["review_required"] is False


def test_f_label_outside_mating_block_is_reviewable_not_litter_event():
    candidate = infer_litter_event_candidate(
        {
            "raw": {"litter_label": "F1", "dob": "26.03.24", "pup_count": "9p"},
            "normalized_candidate": {"litter_label": "F1", "birth_date": "2026-03-24", "pup_count": 9},
            "confidence": 0.8,
        },
        in_mating_block=False,
    )

    assert candidate["candidate_type"] == "litter_event"
    assert candidate["review_required"] is True
    assert candidate["event_status_candidate"] == "unknown"
    assert "outside an identified mating block" in candidate["review_reason"]


def test_current_pups_overdue_review_requires_no_newer_resolved_evidence():
    review = review_current_pups(
        pubs_date="2026-03-20",
        observed_date="2026-05-09",
        newer_resolved_litter_exists=False,
        rule_set=DEFAULT_BREEDING_RULE_SET,
    )
    ignored = review_current_pups(
        pubs_date="2026-03-20",
        observed_date="2026-05-09",
        newer_resolved_litter_exists=True,
        rule_set=DEFAULT_BREEDING_RULE_SET,
    )

    assert review["issue"] == "Current pups overdue for separation review"
    assert review["priority"] == "medium"
    assert ignored is None


def test_parent_replacement_review_does_not_close_mating():
    review = review_parent_replacement(
        parent_dob="2025-01-01",
        observed_date="2026-05-09",
        has_recent_litter=True,
        rule_set=DEFAULT_BREEDING_RULE_SET,
    )

    assert review["issue"] == "Parent replacement review"
    assert review["priority"] == "low"
    assert "close_mating" not in review["metadata"]["suggested_actions"]


def test_strain_assumption_applies_only_to_matching_strain_scope():
    matching = apply_strain_assumption("ApoM Tg/Tg", "default_genotype_for_pups", DEFAULT_BREEDING_RULE_SET)
    non_matching = apply_strain_assumption("Other Strain", "default_genotype_for_pups", DEFAULT_BREEDING_RULE_SET)

    assert matching == "Tg"
    assert non_matching is None


def test_missing_litter_evidence_needs_source_recency_before_no_birth_review():
    no_review = review_missing_birth_evidence(
        mating_date="2026-01-01",
        observed_date="",
        has_litter_evidence=False,
        rule_set=DEFAULT_BREEDING_RULE_SET,
    )
    review = review_missing_birth_evidence(
        mating_date="2026-01-01",
        observed_date="2026-05-09",
        has_litter_evidence=False,
        rule_set=DEFAULT_BREEDING_RULE_SET,
    )

    assert no_review is None
    assert review["issue"] == "No-birth review"
