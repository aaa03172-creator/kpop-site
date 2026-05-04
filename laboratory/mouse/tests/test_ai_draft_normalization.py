from __future__ import annotations

from app.main import normalize_ai_draft_payload


def base_draft(**overrides):
    draft = {
        "card_type": "Separated",
        "raw_strain": "ApoM Tg/Tg",
        "matched_strain": "ApoM Tg/Tg",
        "sex_raw": "F",
        "id_raw": "MT",
        "dob_raw": "",
        "dob_normalized": "",
        "mating_date_raw": "",
        "mating_date_normalized": "",
        "lmo_raw": "",
        "mouse_count": "2 total",
        "notes": [],
        "raw_visible_text_lines": [],
        "symbol_confusions": [],
        "confidence": 80,
        "uncertain_fields": [],
        "reviewer_note": "",
    }
    draft.update(overrides)
    return draft


def test_ai_draft_keeps_full_visible_date_normalization() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(dob_raw="2026.03.01", dob_normalized="2026-03-01")
    )

    assert draft["dob_normalized"] == "2026-03-01"


def test_ai_draft_drops_partial_date_range_normalization() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(dob_raw="25.10.20-28", dob_normalized="2025-10-20/2025-10-28")
    )

    assert draft["dob_normalized"] == ""


def test_ai_draft_drops_uncertain_date_normalization() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(
            mating_date_raw="2026.04.0?",
            mating_date_normalized="2026-04-01",
            uncertain_fields=["mating_date_normalized"],
        )
    )

    assert draft["mating_date_normalized"] == ""


def test_ai_draft_strips_uncertain_field_names_before_date_guard() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(
            dob_raw="2026.03.01",
            dob_normalized="2026-03-01",
            uncertain_fields=[" dob_normalized "],
        )
    )

    assert draft["dob_normalized"] == ""
    assert draft["uncertain_fields"] == ["dob_normalized"]


def test_ai_draft_normalizes_uncertain_field_name_case() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(
            dob_raw="2026.03.01",
            dob_normalized="2026-03-01",
            uncertain_fields=["DOB_NORMALIZED"],
        )
    )

    assert draft["dob_normalized"] == ""
    assert draft["uncertain_fields"] == ["dob_normalized"]


def test_ai_draft_deduplicates_uncertain_field_names_after_normalization() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(
            uncertain_fields=[
                "DOB_NORMALIZED",
                " dob_normalized ",
                "sex_raw",
                "SEX_RAW",
            ],
        )
    )

    assert draft["uncertain_fields"] == ["dob_normalized", "sex_raw"]


def test_ai_draft_maps_uncertain_field_aliases_before_date_guard() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(
            dob_raw="2026.03.01",
            dob_normalized="2026-03-01",
            mating_date_raw="2026.04.01",
            mating_date_normalized="2026-04-01",
            uncertain_fields=["dobNormalized", "mating date normalized"],
        )
    )

    assert draft["dob_normalized"] == ""
    assert draft["mating_date_normalized"] == ""
    assert draft["uncertain_fields"] == ["dob_normalized", "mating_date_normalized"]


def test_ai_draft_drops_non_finite_confidence() -> None:
    nan_draft = normalize_ai_draft_payload(base_draft(confidence=float("nan")))
    infinite_draft = normalize_ai_draft_payload(base_draft(confidence=float("inf")))

    assert nan_draft["confidence"] == 0
    assert infinite_draft["confidence"] == 0


def test_ai_draft_drops_non_iso_normalized_date() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(dob_raw="2026.03.01", dob_normalized="03/01/2026")
    )

    assert draft["dob_normalized"] == ""


def test_ai_draft_drops_invalid_calendar_date() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(dob_raw="2026.02.30", dob_normalized="2026-02-30")
    )

    assert draft["dob_normalized"] == ""


def test_ai_draft_drops_normalized_date_that_does_not_match_visible_raw_date() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(dob_raw="2026.03.01", dob_normalized="2026-04-01")
    )

    assert draft["dob_normalized"] == ""


def test_ai_draft_keeps_iso_date_range_when_both_dates_are_visible() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(
            dob_raw="2026.03.01-2026.03.05",
            dob_normalized="2026-03-01/2026-03-05",
        )
    )

    assert draft["dob_normalized"] == "2026-03-01/2026-03-05"


def test_ai_draft_drops_reversed_iso_date_range() -> None:
    draft = normalize_ai_draft_payload(
        base_draft(
            dob_raw="2026.03.05-2026.03.01",
            dob_normalized="2026-03-05/2026-03-01",
        )
    )

    assert draft["dob_normalized"] == ""
