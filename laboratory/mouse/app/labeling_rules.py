from __future__ import annotations

from copy import deepcopy
from typing import Any


def apply_ear_sequence(
    note_groups: list[list[dict[str, Any]]],
    sequence: list[str],
) -> list[list[dict[str, Any]]]:
    result: list[list[dict[str, Any]]] = []
    for group in note_groups:
        rewritten_group: list[dict[str, Any]] = []
        active_index = 0
        for note in group:
            rewritten = deepcopy(note)
            if str(note.get("interpreted_status") or "active") == "dead":
                rewritten["expected_ear_label_code"] = None
            else:
                rewritten["expected_ear_label_code"] = (
                    sequence[active_index] if active_index < len(sequence) else None
                )
                active_index += 1
            rewritten_group.append(rewritten)
        result.append(rewritten_group)
    return result


def interpret_crossed_out_status(strike_status: str, crossed_out_handling: str) -> str:
    normalized_strike = (strike_status or "none").strip().lower()
    normalized_rule = (crossed_out_handling or "review").strip().lower()
    if normalized_rule == "dead" and normalized_strike in {"single", "double"}:
        return "dead"
    if normalized_strike == "none":
        return "active"
    return "review"


def match_samples_to_mice(
    samples: list[dict[str, Any]],
    mice: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for sample in samples:
        matched_sample = deepcopy(sample)
        sample_id = str(sample.get("sample_id") or "").strip()
        candidates = []
        if sample_id:
            candidates = [
                mouse
                for mouse in mice
                if sample_id == str(mouse.get("display_id") or "").strip()
            ]

        if len(candidates) == 1:
            matched_sample["match_status"] = "matched"
            matched_sample["mouse_id"] = candidates[0].get("mouse_id")
        elif len(candidates) > 1:
            matched_sample["match_status"] = "duplicate_mouse_match"
            matched_sample["mouse_id"] = None
        else:
            matched_sample["match_status"] = "unmatched"
            matched_sample["mouse_id"] = None

        matches.append(matched_sample)
    return matches
