from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from rapidfuzz import fuzz


AUTO_FILL_SCORE = 96.0
CHECK_SCORE = 86.0
AMBIGUOUS_MARGIN = 5.0


@dataclass(frozen=True)
class MatchCandidate:
    canonical: str
    alias: str


@dataclass(frozen=True)
class MatchSuggestion:
    raw_value: str
    canonical: str
    matched_alias: str
    score: float
    decision: str
    reason: str
    alternatives: tuple[dict[str, str | float], ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "raw_value": self.raw_value,
            "canonical": self.canonical,
            "matched_alias": self.matched_alias,
            "score": round(self.score, 2),
            "decision": self.decision,
            "reason": self.reason,
            "alternatives": list(self.alternatives),
        }


def compact_key(value: str) -> str:
    return "".join(character for character in normalize_text(value) if not character.isspace())


def normalize_text(value: str) -> str:
    return " ".join(str(value or "").replace(";", " ; ").replace("/", " / ").split()).lower()


def match_candidate(
    raw_values: Iterable[str],
    candidates: Iterable[MatchCandidate],
    *,
    auto_fill_score: float = AUTO_FILL_SCORE,
    check_score: float = CHECK_SCORE,
    ambiguous_margin: float = AMBIGUOUS_MARGIN,
) -> MatchSuggestion:
    queries = [str(value or "").strip() for value in raw_values if str(value or "").strip()]
    candidate_list = [
        candidate
        for candidate in candidates
        if candidate.canonical.strip() and candidate.alias.strip()
    ]
    if not queries:
        return MatchSuggestion("", "", "", 0.0, "needs_review", "No raw value was available to match.")
    raw_value = queries[0]
    if not candidate_list:
        return MatchSuggestion(raw_value, "", "", 0.0, "needs_review", "No active configured candidates were available.")

    exact_lookup: dict[str, MatchCandidate] = {}
    for candidate in candidate_list:
        exact_lookup.setdefault(compact_key(candidate.alias), candidate)
    for query in queries:
        exact = exact_lookup.get(compact_key(query))
        if exact:
            return MatchSuggestion(
                query,
                exact.canonical,
                exact.alias,
                100.0,
                "auto_filled",
                "Exact match against configured display name or alias.",
            )

    scored: list[tuple[float, str, MatchCandidate]] = []
    for query in queries:
        normalized_query = normalize_text(query)
        for candidate in candidate_list:
            score = float(fuzz.WRatio(normalized_query, normalize_text(candidate.alias)))
            scored.append((score, query, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return MatchSuggestion(raw_value, "", "", 0.0, "needs_review", "No match candidates could be scored.")

    best_score, best_query, best_candidate = scored[0]
    alternatives = []
    seen: set[tuple[str, str]] = set()
    for score, _, candidate in scored[1:]:
        key = (candidate.canonical, candidate.alias)
        if key in seen:
            continue
        seen.add(key)
        alternatives.append(
            {
                "canonical": candidate.canonical,
                "alias": candidate.alias,
                "score": round(score, 2),
            }
        )
        if len(alternatives) >= 3:
            break

    ambiguous = any(
        alt["canonical"] != best_candidate.canonical
        and float(alt["score"]) >= best_score - ambiguous_margin
        for alt in alternatives
    )
    if best_score >= auto_fill_score and not ambiguous:
        decision = "auto_filled"
        reason = "High-confidence fuzzy match against configured display name or alias."
    elif best_score >= check_score:
        decision = "check"
        reason = "Fuzzy match needs review because confidence or margin is not high enough."
    else:
        decision = "needs_review"
        reason = "No configured candidate matched with sufficient confidence."

    return MatchSuggestion(
        best_query,
        best_candidate.canonical,
        best_candidate.alias,
        best_score,
        decision,
        reason,
        tuple(alternatives),
    )
