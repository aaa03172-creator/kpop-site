from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any


def today_iso() -> str:
    return date.today().isoformat()


def parse_year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).year
    except ValueError:
        return None


def age_days(dob: str | None, as_of: date | None = None) -> int | None:
    if not dob:
        return None
    try:
        born = date.fromisoformat(dob)
    except ValueError:
        return None
    return ((as_of or date.today()) - born).days


def print_result(payload: Any, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    if isinstance(payload, list):
        for item in payload:
            print(_compact(item))
    elif isinstance(payload, dict):
        print(_compact(payload))
    else:
        print(payload)


def _compact(payload: dict[str, Any]) -> str:
    preferred = [
        "strain_id",
        "strain_name",
        "mouse_id",
        "display_id",
        "cage_id",
        "cage_label",
        "mating_id",
        "litter_id",
        "event_id",
        "genotype_result_id",
        "status",
        "current_status",
    ]
    parts = []
    for key in preferred:
        if key in payload and payload[key] not in (None, ""):
            parts.append(f"{key}={payload[key]}")
    if parts:
        return " ".join(parts)
    return json.dumps(payload, ensure_ascii=False, default=str)
