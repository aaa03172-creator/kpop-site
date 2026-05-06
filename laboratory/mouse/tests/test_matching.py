from __future__ import annotations

from app.matching import MatchCandidate, match_candidate


def test_exact_alias_match_can_auto_fill() -> None:
    suggestion = match_candidate(
        ["GFAP Cre; S1PR1 fl/fl"],
        [
            MatchCandidate("GFAP Cre; S1PR1 fl/fl", "GFAP Cre; S1PR1 fl/fl"),
            MatchCandidate("ApoM Tg/Tg", "ApoM Tg/Tg"),
        ],
    )

    assert suggestion.canonical == "GFAP Cre; S1PR1 fl/fl"
    assert suggestion.score == 100
    assert suggestion.decision == "auto_filled"


def test_close_fuzzy_match_is_reviewable_check() -> None:
    suggestion = match_candidate(
        ["GFAP Cre S1PR1 flox"],
        [
            MatchCandidate("GFAP Cre; S1PR1 fl/fl", "GFAP Cre; S1PR1 fl/fl"),
            MatchCandidate("ApoM Tg/Tg", "ApoM Tg/Tg"),
        ],
        auto_fill_score=99,
        check_score=70,
    )

    assert suggestion.canonical == "GFAP Cre; S1PR1 fl/fl"
    assert suggestion.decision == "check"
    assert suggestion.score >= 70


def test_ambiguous_fuzzy_match_does_not_auto_fill() -> None:
    suggestion = match_candidate(
        ["ApoM Tg"],
        [
            MatchCandidate("ApoM Tg/Tg", "ApoM Tg/Tg"),
            MatchCandidate("ApoM Tg/+", "ApoM Tg/+"),
        ],
        auto_fill_score=80,
        check_score=60,
    )

    assert suggestion.canonical in {"ApoM Tg/Tg", "ApoM Tg/+"}
    assert suggestion.decision == "check"
    assert suggestion.alternatives


def test_low_confidence_match_needs_review() -> None:
    suggestion = match_candidate(
        ["Completely unrelated strain"],
        [MatchCandidate("ApoM Tg/Tg", "ApoM Tg/Tg")],
    )

    assert suggestion.decision == "needs_review"
    assert suggestion.canonical == "ApoM Tg/Tg"
