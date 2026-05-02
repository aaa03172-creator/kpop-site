from __future__ import annotations

import re
import sqlite3
from datetime import date


PREFIXES = {
    "strain": "STR",
    "gene": "GENE",
    "allele": "AL",
    "strain_allele": "SA",
    "mouse": "M",
    "cage": "C",
    "mating": "MAT",
    "litter": "LIT",
    "event": "EVT",
    "genotype": "GT",
}

YEARLY = {"mouse", "mating", "litter", "event", "genotype"}


def normalize_cage_id(value: str) -> str:
    text = value.strip().upper()
    match = re.match(r"^C-?(\d+)$", text)
    if match:
        return f"C-{int(match.group(1)):03d}"
    return text


def mouse_id_from_display(display_id: str, year: int | None = None) -> str | None:
    match = re.search(r"(\d+)$", display_id.strip())
    if not match:
        return None
    return f"M-{year or date.today().year}-{int(match.group(1)):04d}"


def next_external_id(conn: sqlite3.Connection, entity: str, year: int | None = None) -> str:
    prefix = PREFIXES[entity]
    seq_year = str(year or date.today().year) if entity in YEARLY else ""
    row = conn.execute(
        "SELECT next_value FROM id_sequence WHERE entity = ? AND year = ?",
        (entity, seq_year),
    ).fetchone()
    if row is None:
        value = 1
        conn.execute(
            "INSERT INTO id_sequence (entity, year, next_value) VALUES (?, ?, ?)",
            (entity, seq_year, 2),
        )
    else:
        value = int(row["next_value"])
        conn.execute(
            "UPDATE id_sequence SET next_value = ? WHERE entity = ? AND year = ?",
            (value + 1, entity, seq_year),
        )
    if entity in YEARLY:
        return f"{prefix}-{seq_year}-{value:04d}" if entity in {"mouse", "event", "genotype"} else f"{prefix}-{seq_year}-{value:03d}"
    return f"{prefix}-{value:04d}" if entity not in {"cage"} else f"{prefix}-{value:03d}"
