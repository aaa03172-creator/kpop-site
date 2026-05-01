from __future__ import annotations

import json
import re
import hashlib
import csv
import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import ROOT, connection, init_db
from .storage import new_id, save_upload, utc_now


STATIC_DIR = ROOT / "static"
FIXTURE_PATH = ROOT / "fixtures" / "sample_parse_results.json"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="Mouse Colony LIMS Local MVP", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AssignedStrainCreate(BaseModel):
    display_name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    source_type: str = "manual"
    source_reference: str = ""
    notes: str = ""


class DistributionImportPayload(BaseModel):
    layer: str = ""
    description: str = ""
    source_file_name: str = ""
    source_file_path: str = ""
    received_date: str = ""
    sheet_name: str = ""
    rows: list[dict[str, Any]]


class StrainRegistryCreate(BaseModel):
    strain_name: str = Field(min_length=1)
    common_name: str = ""
    official_name: str = ""
    gene: str = ""
    allele: str = ""
    background: str = ""
    source: str = ""
    status: str = "active"
    breeding_note: str = ""
    genotyping_note: str = ""
    owner: str = ""
    source_record_id: str | None = None


class CorrectionCreate(BaseModel):
    entity_type: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    field_name: str = Field(min_length=1)
    before_value: str = ""
    after_value: str = ""
    reason: str = ""
    source_record_id: str | None = None
    review_id: str | None = None


class MouseEventCreate(BaseModel):
    mouse_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    event_date: str = ""
    related_entity_type: str = ""
    related_entity_id: str = ""
    source_record_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "local_user"


class ReviewResolutionCreate(BaseModel):
    resolution_note: str = Field(min_length=1)
    resolved_value: str = ""


class GenotypingUpdate(BaseModel):
    mouse_id: str = Field(min_length=1)
    sample_id: str = ""
    sample_date: str = ""
    raw_result: str = ""
    normalized_result: str = ""
    result_date: str = ""
    target_name: str = ""
    notes: str = ""


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "storage": "local-only"}


@app.get("/api/photos")
def list_photos() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind
            FROM photo_log
            ORDER BY uploaded_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def stable_checksum(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_source_record(
    conn: Any,
    *,
    source_type: str,
    source_uri: str = "",
    source_label: str = "",
    raw_payload: str = "",
    note: str = "",
) -> str:
    source_record_id = new_id("source")
    imported_at = utc_now()
    conn.execute(
        """
        INSERT INTO source_record
            (source_record_id, source_type, source_uri, source_label,
             raw_payload, imported_at, checksum, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_record_id,
            source_type,
            source_uri,
            source_label,
            raw_payload,
            imported_at,
            stable_checksum(f"{source_type}|{source_uri}|{source_label}|{raw_payload}"),
            note,
        ),
    )
    return source_record_id


@app.get("/api/source-records")
def list_source_records() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT source_record_id, source_type, source_uri, source_label,
                   raw_payload, imported_at, checksum, note
            FROM source_record
            ORDER BY imported_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/strains")
def list_strains() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT strain_id, strain_name, common_name, official_name, gene,
                   allele, background, source, status, breeding_note,
                   genotyping_note, owner, source_record_id, created_at, updated_at
            FROM strain_registry
            ORDER BY status = 'active' DESC, strain_name COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/strains")
def create_strain(payload: StrainRegistryCreate) -> dict[str, Any]:
    strain_name = " ".join(payload.strain_name.split())
    if not strain_name:
        raise HTTPException(status_code=400, detail="Strain name is required.")

    now = utc_now()
    strain_id = new_id("strain")
    raw_payload = payload.model_dump_json()
    with connection() as conn:
        source_record_id = payload.source_record_id
        if source_record_id is None:
            source_record_id = create_source_record(
                conn,
                source_type="manual_entry",
                source_label=f"Manual strain registry entry: {strain_name}",
                raw_payload=raw_payload,
                note="Created from local Strain Registry form.",
            )
        else:
            exists = conn.execute(
                "SELECT 1 FROM source_record WHERE source_record_id = ?",
                (source_record_id,),
            ).fetchone()
            if exists is None:
                raise HTTPException(status_code=400, detail="source_record_id does not exist.")

        conn.execute(
            """
            INSERT INTO strain_registry
                (strain_id, strain_name, common_name, official_name, gene,
                 allele, background, source, status, breeding_note,
                 genotyping_note, owner, source_record_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                strain_id,
                strain_name,
                payload.common_name,
                payload.official_name,
                payload.gene,
                payload.allele,
                payload.background,
                payload.source,
                payload.status or "active",
                payload.breeding_note,
                payload.genotyping_note,
                payload.owner,
                source_record_id,
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "strain_created",
                strain_id,
                None,
                raw_payload,
                now,
            ),
        )

    return {
        "strain_id": strain_id,
        "strain_name": strain_name,
        "status": payload.status or "active",
        "source_record_id": source_record_id,
        "created_at": now,
    }


@app.get("/api/corrections")
def list_corrections() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT correction_id, entity_type, entity_id, field_name,
                   before_value, after_value, reason, source_record_id,
                   review_id, corrected_at
            FROM correction_log
            ORDER BY corrected_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/corrections")
def create_correction(payload: CorrectionCreate) -> dict[str, Any]:
    correction_id = new_id("correction")
    corrected_at = utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO correction_log
                (correction_id, entity_type, entity_id, field_name,
                 before_value, after_value, reason, source_record_id,
                 review_id, corrected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                correction_id,
                payload.entity_type,
                payload.entity_id,
                payload.field_name,
                payload.before_value,
                payload.after_value,
                payload.reason,
                payload.source_record_id,
                payload.review_id,
                corrected_at,
            ),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "correction_applied",
                payload.entity_id,
                payload.before_value,
                payload.after_value,
                corrected_at,
            ),
        )

    return {"correction_id": correction_id, "corrected_at": corrected_at}


@app.get("/api/mouse-events")
def list_mouse_events() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT event_id, mouse_id, event_type, event_date,
                   related_entity_type, related_entity_id, source_record_id,
                   details, created_by, created_at
            FROM mouse_event
            ORDER BY event_date DESC, created_at DESC
            """
        ).fetchall()
    result = []
    for row in rows:
        payload = dict(row)
        payload["details"] = json.loads(payload["details"] or "{}")
        result.append(payload)
    return result


@app.post("/api/mouse-events")
def create_mouse_event(payload: MouseEventCreate) -> dict[str, Any]:
    event_id = new_id("event")
    created_at = utc_now()
    event_date = payload.event_date or created_at[:10]
    with connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM mouse_master WHERE mouse_id = ?",
            (payload.mouse_id,),
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail="Mouse not found.")
        conn.execute(
            """
            INSERT INTO mouse_event
                (event_id, mouse_id, event_type, event_date, related_entity_type,
                 related_entity_id, source_record_id, details, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                payload.mouse_id,
                payload.event_type,
                event_date,
                payload.related_entity_type,
                payload.related_entity_id,
                payload.source_record_id,
                json.dumps(payload.details, ensure_ascii=False),
                payload.created_by,
                created_at,
            ),
        )
    return {"event_id": event_id, "event_date": event_date, "created_at": created_at}


def assigned_strain_row(row: Any) -> dict[str, Any]:
    result = dict(row)
    result["aliases"] = json.loads(result.pop("aliases_json") or "[]")
    result["active"] = bool(result["active"])
    return result


def compact_strain_key(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def assigned_scope_map(conn: Any) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT display_name, aliases_json
        FROM my_assigned_strain
        WHERE active = 1
        """
    ).fetchall()
    scope: dict[str, str] = {}
    for row in rows:
        names = [row["display_name"], *json.loads(row["aliases_json"] or "[]")]
        for name in names:
            key = compact_strain_key(str(name))
            if key:
                scope[key] = row["display_name"]
    return scope


def assigned_scope_match(scope: dict[str, str], record: dict[str, Any]) -> str:
    for value in [record.get("matchedStrain"), record.get("rawStrain")]:
        key = compact_strain_key(str(value or ""))
        if key in scope:
            return scope[key]
    return ""


def parse_optional_int(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else None


def distribution_row_payload(row: Any) -> dict[str, Any]:
    result = dict(row)
    result["traceability"] = json.loads(result.get("traceability") or "{}")
    return result


def split_dob_range(raw: Any, normalized: Any) -> tuple[str, str | None, str | None]:
    dob_raw = str(raw or "")
    normalized_text = str(normalized or "")
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", normalized_text)
    if len(dates) >= 2:
        return dob_raw, dates[0], dates[1]
    if len(dates) == 1:
        return dob_raw, dates[0], dates[0]
    return dob_raw, None, None


def mouse_id_prefix(display_id: str) -> str:
    match = re.match(r"^([A-Za-z]+)", display_id)
    return match.group(1) if match else ""


def normalize_ear_label(raw: str) -> dict[str, Any]:
    text = "".join(str(raw or "").split())
    if not text:
        return {"code": None, "confidence": 0.0, "status": "needs_review", "candidates": []}
    if text.upper() == "N":
        return {"code": "NONE", "confidence": 1.0, "status": "auto_filled", "candidates": []}

    components: list[tuple[str, str, float, str]] = []
    index = 0
    while index < len(text):
        side = text[index].upper()
        if side not in {"R", "L"}:
            return {"code": None, "confidence": 0.0, "status": "needs_review", "candidates": []}
        index += 1
        if index >= len(text):
            return {
                "code": None,
                "confidence": 0.2,
                "status": "needs_review",
                "candidates": [{"code": f"{side}_PRIME", "confidence": 0.35}, {"code": f"{side}_CIRCLE", "confidence": 0.35}],
            }
        mark = text[index]
        index += 1
        if mark in {"'", "\u2032", "\u2019", "`", "."}:
            components.append((side, "PRIME", 0.98 if mark != "." else 0.75, "auto_filled" if mark != "." else "check"))
        elif mark in {"\u00b0", "\u00ba", "\u02da"}:
            components.append((side, "CIRCLE", 1.0 if mark == "\u00b0" else 0.92, "auto_filled"))
        elif mark in {"0", "o", "O"}:
            components.append((side, "CIRCLE", 0.65, "check"))
        else:
            return {"code": None, "confidence": 0.0, "status": "needs_review", "candidates": []}

    if not components:
        return {"code": None, "confidence": 0.0, "status": "needs_review", "candidates": []}

    code = "_".join(f"{side}_{mark}" for side, mark, _, _ in components)
    confidence = min(confidence for _, _, confidence, _ in components)
    status = "check" if any(status == "check" for _, _, _, status in components) else "auto_filled"
    return {"code": code, "confidence": confidence, "status": status, "candidates": []}


def interpreted_status(card_type: str, strike_status: str) -> str:
    normalized_card_type = card_type.lower()
    if strike_status == "single":
        return "separated" if normalized_card_type == "mating" else "moved"
    if strike_status == "double":
        return "dead"
    if strike_status == "unclear":
        return "needs_review"
    return "open" if normalized_card_type == "mating" else "active"


def parse_note_line(raw_line: str, card_type: str) -> dict[str, Any]:
    line = str(raw_line or "").strip()
    litter_match = re.search(r"(\d{2,4}[./-]\d{1,2}[./-]\d{1,2})\s*[-\u2013]\s*(\d+)\s*p?", line, re.IGNORECASE)
    if litter_match:
        return {
            "parsed_type": "litter_event",
            "parsed_mouse_display_id": None,
            "parsed_ear_label_raw": None,
            "parsed_ear_label_code": None,
            "parsed_ear_label_confidence": None,
            "parsed_ear_label_review_status": "needs_review",
            "parsed_event_date": litter_match.group(1),
            "parsed_count": int(litter_match.group(2)),
            "confidence": 0.9,
            "needs_review": 0,
        }

    mouse_match = re.match(r"^\s*([A-Za-z]{0,4}\d+[A-Za-z0-9-]*)\s+(.+?)\s*$", line)
    if mouse_match and "x" not in line.lower():
        ear_raw = mouse_match.group(2).strip()
        ear = normalize_ear_label(ear_raw)
        return {
            "parsed_type": "mouse_item",
            "parsed_mouse_display_id": mouse_match.group(1),
            "parsed_ear_label_raw": ear_raw,
            "parsed_ear_label_code": ear["code"],
            "parsed_ear_label_confidence": ear["confidence"],
            "parsed_ear_label_review_status": ear["status"],
            "parsed_event_date": None,
            "parsed_count": None,
            "confidence": ear["confidence"],
            "needs_review": 1 if ear["status"] in {"check", "needs_review"} else 0,
        }

    return {
        "parsed_type": "unknown",
        "parsed_mouse_display_id": None,
        "parsed_ear_label_raw": None,
        "parsed_ear_label_code": None,
        "parsed_ear_label_confidence": None,
        "parsed_ear_label_review_status": "needs_review",
        "parsed_event_date": None,
        "parsed_count": None,
        "confidence": 0.0,
        "needs_review": 1,
    }


def should_write_mouse_candidate(record: dict[str, Any], status: str) -> bool:
    if status != "auto":
        return False
    if str(record.get("type") or "").lower() != "separated":
        return False
    review_field = str(record.get("reviewField") or "").lower()
    issue = str(record.get("issue") or "").lower()
    return review_field not in {"mouseid", "mousecount"} and "count mismatch" not in issue


def active_mouse_note_count(record: dict[str, Any]) -> int:
    card_type = str(record.get("type") or "unknown").lower()
    notes = record.get("notes") if isinstance(record.get("notes"), list) else []
    active_count = 0
    for note in notes:
        raw_line = str(note.get("raw") if isinstance(note, dict) else note)
        strike_status = str(note.get("strike") or "none") if isinstance(note, dict) else "none"
        parsed = parse_note_line(raw_line, card_type)
        if parsed["parsed_type"] == "mouse_item" and interpreted_status(card_type, strike_status) == "active":
            active_count += 1
    return active_count


def declared_total_count(record: dict[str, Any]) -> int | None:
    mouse_count = str(record.get("mouseCount") or "")
    if "total" not in mouse_count.lower():
        return None
    match = re.search(r"\d+", mouse_count)
    return int(match.group(0)) if match else None


def validation_review_for_record(conn: Any, record: dict[str, Any], status: str) -> dict[str, str] | None:
    if status in {"review", "conflict"}:
        return None

    review_field = str(record.get("reviewField") or "").lower()
    issue = str(record.get("issue") or "").lower()
    card_type = str(record.get("type") or "").lower()

    if card_type == "separated" and (review_field == "mousecount" or "count mismatch" in issue):
        expected = declared_total_count(record)
        active_count = active_mouse_note_count(record)
        if expected is None or expected != active_count:
            return {
                "severity": "Medium",
                "issue": "Count mismatch",
                "currentValue": str(record.get("mouseCount") or ""),
                "suggestedValue": f"{active_count} active parsed note line{'s' if active_count != 1 else ''}",
                "reviewReason": "Parsed sex/count does not match the active unstruck mouse note lines. Review before creating canonical mouse candidates.",
            }

    if review_field == "mouseid" or "duplicate active" in issue:
        mouse_id = str(record.get("currentValue") or "").strip()
        if mouse_id:
            existing = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM mouse_master
                WHERE display_id = ? AND status IN ('active', 'mating')
                """,
                (mouse_id,),
            ).fetchone()["count"]
        else:
            existing = 0
        return {
            "severity": "High" if existing else str(record.get("severity") or "High"),
            "issue": "Duplicate active mouse",
            "currentValue": mouse_id or str(record.get("currentValue") or ""),
            "suggestedValue": "Resolve movement or confirm this is a different mouse before accepting",
            "reviewReason": "Mouse ID appears as a duplicate-active risk. Review movement/source evidence before writing mouse state.",
        }

    return None


def write_note_items_and_mouse_candidates(conn: Any, parse_id: str, record: dict[str, Any], status: str) -> tuple[int, int, int]:
    card_type = str(record.get("type") or "unknown").lower()
    notes = record.get("notes") if isinstance(record.get("notes"), list) else []
    note_count = 0
    mouse_count = 0
    ear_review_count = 0
    write_mouse = should_write_mouse_candidate(record, status)
    dob_raw, dob_start, dob_end = split_dob_range(record.get("dobRaw"), record.get("dobNormalized"))
    raw_strain_text = str(record.get("matchedStrain") or record.get("rawStrain") or "")

    for index, note in enumerate(notes, start=1):
        raw_line = str(note.get("raw") if isinstance(note, dict) else note)
        strike_status = str(note.get("strike") or "none") if isinstance(note, dict) else "none"
        parsed = parse_note_line(raw_line, card_type)
        status_from_strike = interpreted_status(card_type, strike_status)
        note_item_id = f"note_{parse_id}_{index}"
        conn.execute(
            """
            INSERT OR REPLACE INTO card_note_item_log
                (note_item_id, parse_id, card_type, line_number, raw_line_text, strike_status,
                 parsed_type, interpreted_status, parsed_mouse_display_id, parsed_ear_label_raw,
                 parsed_ear_label_code, parsed_ear_label_confidence, parsed_ear_label_review_status,
                 parsed_event_date, parsed_count, confidence, needs_review)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_item_id,
                parse_id,
                card_type,
                index,
                raw_line,
                strike_status,
                parsed["parsed_type"],
                status_from_strike if parsed["parsed_type"] != "unknown" else "unknown",
                parsed["parsed_mouse_display_id"],
                parsed["parsed_ear_label_raw"],
                parsed["parsed_ear_label_code"],
                parsed["parsed_ear_label_confidence"],
                parsed["parsed_ear_label_review_status"],
                parsed["parsed_event_date"],
                parsed["parsed_count"],
                parsed["confidence"],
                parsed["needs_review"],
            ),
        )
        note_count += 1
        if parsed["parsed_type"] == "mouse_item" and parsed["parsed_ear_label_review_status"] in {"check", "needs_review"}:
            review_id = f"review_ear_{note_item_id}"
            suggested_value = parsed["parsed_ear_label_code"] or "Confirm raw note line before normalization"
            conn.execute(
                """
                INSERT OR REPLACE INTO review_queue
                    (review_id, parse_id, severity, issue, current_value, suggested_value,
                     review_reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    parse_id,
                    "Medium",
                    "Ear label needs review",
                    str(parsed["parsed_ear_label_raw"] or raw_line),
                    str(suggested_value),
                    f"Note item {note_item_id} has uncertain ear label evidence. Confirm against the source cage card before using a normalized ear label.",
                    "open",
                    utc_now(),
                ),
            )
            ear_review_count += 1

        if write_mouse and parsed["parsed_type"] == "mouse_item" and parsed["parsed_mouse_display_id"]:
            display_id = str(parsed["parsed_mouse_display_id"])
            mouse_id = f"mouse_{display_id}_{parse_id}".replace(" ", "_")
            reviewed_ear_code = (
                parsed["parsed_ear_label_code"]
                if parsed["parsed_ear_label_review_status"] == "auto_filled"
                else None
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO mouse_master
                    (mouse_id, display_id, id_prefix, raw_strain_text, dob_raw, dob_start, dob_end,
                     ear_label_raw, ear_label_code, ear_label_confidence, ear_label_review_status,
                     source_note_item_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mouse_id,
                    display_id,
                    mouse_id_prefix(display_id),
                    raw_strain_text,
                    dob_raw,
                    dob_start,
                    dob_end,
                    parsed["parsed_ear_label_raw"],
                    reviewed_ear_code,
                    parsed["parsed_ear_label_confidence"],
                    parsed["parsed_ear_label_review_status"],
                    note_item_id,
                    status_from_strike,
                ),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO mouse_event
                    (event_id, mouse_id, event_type, event_date, related_entity_type,
                     related_entity_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"event_{mouse_id}_{index}",
                    mouse_id,
                    "note_added",
                    dob_start or utc_now()[:10],
                    "note_item",
                    note_item_id,
                    json.dumps(
                        {
                            "display_id": display_id,
                            "interpreted_status": status_from_strike,
                            "raw_line_text": raw_line,
                            "raw_strain_text": raw_strain_text,
                        },
                        ensure_ascii=False,
                    ),
                    utc_now(),
                ),
            )
            mouse_count += 1
    return note_count, mouse_count, ear_review_count


@app.get("/api/assigned-strains")
def list_assigned_strains() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT assigned_strain_id, display_name, aliases_json, source_type,
                   source_reference, active, assigned_at, removed_at, notes
            FROM my_assigned_strain
            ORDER BY active DESC, display_name COLLATE NOCASE
            """
        ).fetchall()
    return [assigned_strain_row(row) for row in rows]


@app.post("/api/assigned-strains")
def create_assigned_strain(payload: AssignedStrainCreate) -> dict[str, Any]:
    display_name = " ".join(payload.display_name.split())
    aliases = sorted({" ".join(alias.split()) for alias in payload.aliases if alias.strip()})
    if not display_name:
        raise HTTPException(status_code=400, detail="Assigned strain display name is required.")

    assigned_strain_id = new_id("assigned_strain")
    assigned_at = utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO my_assigned_strain
                (assigned_strain_id, display_name, aliases_json, source_type,
                 source_reference, active, assigned_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assigned_strain_id,
                display_name,
                json.dumps(aliases, ensure_ascii=False),
                payload.source_type,
                payload.source_reference,
                1,
                assigned_at,
                payload.notes,
            ),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "assigned_strain_created",
                assigned_strain_id,
                None,
                json.dumps({"display_name": display_name, "aliases": aliases}, ensure_ascii=False),
                assigned_at,
            ),
        )

    return {
        "assigned_strain_id": assigned_strain_id,
        "display_name": display_name,
        "aliases": aliases,
        "source_type": payload.source_type,
        "source_reference": payload.source_reference,
        "active": True,
        "assigned_at": assigned_at,
        "removed_at": None,
        "notes": payload.notes,
    }


@app.post("/api/assigned-strains/{assigned_strain_id}/deactivate")
def deactivate_assigned_strain(assigned_strain_id: str) -> dict[str, Any]:
    removed_at = utc_now()
    with connection() as conn:
        existing = conn.execute(
            "SELECT display_name, active FROM my_assigned_strain WHERE assigned_strain_id = ?",
            (assigned_strain_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Assigned strain not found.")
        conn.execute(
            """
            UPDATE my_assigned_strain
            SET active = 0, removed_at = ?
            WHERE assigned_strain_id = ?
            """,
            (removed_at, assigned_strain_id),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "assigned_strain_deactivated",
                assigned_strain_id,
                json.dumps({"active": bool(existing["active"])}, ensure_ascii=False),
                json.dumps({"active": False}, ensure_ascii=False),
                removed_at,
            ),
        )
    return {"assigned_strain_id": assigned_strain_id, "active": False, "removed_at": removed_at}


@app.get("/api/distribution-imports")
def list_distribution_imports() -> list[dict[str, Any]]:
    with connection() as conn:
        imports = conn.execute(
            """
            SELECT distribution_import_id, source_file_name, source_file_path,
                   received_date, sheet_name, imported_at, status, notes
            FROM distribution_import
            ORDER BY imported_at DESC
            """
        ).fetchall()
        rows = conn.execute(
            """
            SELECT assignment_row_id, distribution_import_id, source_sheet,
                   source_row_number, institution_or_group, responsible_person_raw,
                   mating_type_raw, matched_strain_id, cage_count_raw,
                   mating_cage_count_raw, confidence, review_status, traceability
            FROM distribution_assignment_row
            ORDER BY distribution_import_id, source_row_number
            """
        ).fetchall()

    rows_by_import: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        payload = distribution_row_payload(row)
        rows_by_import.setdefault(payload["distribution_import_id"], []).append(payload)

    return [
        {**dict(import_row), "rows": rows_by_import.get(import_row["distribution_import_id"], [])}
        for import_row in imports
    ]


@app.post("/api/distribution-imports")
def create_distribution_import(payload: DistributionImportPayload) -> dict[str, Any]:
    if payload.layer and payload.layer != "parsed or intermediate result":
        raise HTTPException(status_code=400, detail="Distribution import must be parsed/intermediate JSON.")
    if not payload.rows:
        raise HTTPException(status_code=400, detail="Distribution import requires parsed rows.")

    import_id = new_id("distribution_import")
    imported_at = utc_now()
    source_file_name = payload.source_file_name or "distribution_import.json"
    with connection() as conn:
        source_record_id = create_source_record(
            conn,
            source_type="excel_row_import",
            source_uri=payload.source_file_path,
            source_label=source_file_name,
            raw_payload=payload.model_dump_json(),
            note="Distribution assignment import remains parsed/intermediate until reviewed.",
        )
        conn.execute(
            """
            INSERT INTO distribution_import
                (distribution_import_id, source_file_name, source_file_path,
                 received_date, sheet_name, imported_at, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                import_id,
                source_file_name,
                payload.source_file_path,
                payload.received_date,
                payload.sheet_name,
                imported_at,
                "parsed",
                payload.description,
            ),
        )
        inserted_rows = 0
        for index, row in enumerate(payload.rows, start=1):
            mating_type = str(row.get("mating_type_raw") or row.get("matingTypeRaw") or "").strip()
            if not mating_type:
                continue
            source_row = parse_optional_int(row.get("source_row_number") or row.get("sourceRowNumber"))
            conn.execute(
                """
                INSERT INTO distribution_assignment_row
                    (assignment_row_id, distribution_import_id, source_sheet,
                     source_row_number, institution_or_group, responsible_person_raw,
                     mating_type_raw, matched_strain_id, cage_count_raw,
                     mating_cage_count_raw, confidence, review_status, traceability)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("assignment_row"),
                    import_id,
                    payload.sheet_name,
                    source_row,
                    str(row.get("institution_or_group") or row.get("institutionOrGroup") or ""),
                    str(row.get("responsible_person_raw") or row.get("responsiblePersonRaw") or ""),
                    mating_type,
                    str(row.get("matched_strain_id") or row.get("matchedStrainId") or "") or None,
                    str(row.get("cage_count_raw") or row.get("cageCountRaw") or ""),
                    str(row.get("mating_cage_count_raw") or row.get("matingCageCountRaw") or ""),
                    float(row.get("confidence") or 0),
                    str(row.get("review_status") or row.get("reviewStatus") or "candidate"),
                    json.dumps(
                        {
                            "source_file_name": source_file_name,
                            "sheet_name": payload.sheet_name,
                            "source_row_number": source_row or index,
                            "source_cells": row.get("source_cells") or row.get("sourceCells") or {},
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            inserted_rows += 1
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "distribution_import_created",
                import_id,
                None,
                json.dumps(
                    {
                        "source_file_name": source_file_name,
                        "rows": inserted_rows,
                        "source_record_id": source_record_id,
                    },
                    ensure_ascii=False,
                ),
                imported_at,
            ),
        )

    return {
        "distribution_import_id": import_id,
        "source_record_id": source_record_id,
        "source_file_name": source_file_name,
        "sheet_name": payload.sheet_name,
        "imported_at": imported_at,
        "status": "parsed",
        "stored_rows": inserted_rows,
        "boundary": "parsed or intermediate result",
    }


@app.post("/api/photos")
def upload_photo(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    photo_id = new_id("photo")
    stored_path = save_upload(file, photo_id)
    uploaded_at = utc_now()
    try:
        with connection() as conn:
            source_record_id = create_source_record(
                conn,
                source_type="photo",
                source_uri=str(stored_path.relative_to(ROOT)),
                source_label=file.filename,
                raw_payload=json.dumps({"original_filename": file.filename}, ensure_ascii=False),
                note="Uploaded cage card photo retained as raw source evidence.",
            )
            conn.execute(
                """
                INSERT INTO photo_log (photo_id, original_filename, stored_path, uploaded_at, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (photo_id, file.filename, str(stored_path.relative_to(ROOT)), uploaded_at, "uploaded"),
            )
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise
    return {
        "photo_id": photo_id,
        "original_filename": file.filename,
        "stored_path": str(stored_path.relative_to(ROOT)),
        "uploaded_at": uploaded_at,
        "status": "uploaded",
        "source_record_id": source_record_id,
    }


@app.get("/api/review-items")
def list_review_items() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT review_id, parse_id, severity, issue, current_value, suggested_value,
                   review_reason, status, created_at, resolved_at, resolution_note
            FROM review_queue
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/review-items/{review_id}/resolve")
def resolve_review_item(review_id: str, payload: ReviewResolutionCreate) -> dict[str, Any]:
    resolved_at = utc_now()
    with connection() as conn:
        existing = conn.execute(
            """
            SELECT review_id, parse_id, severity, issue, current_value, suggested_value,
                   review_reason, status, resolution_note
            FROM review_queue
            WHERE review_id = ?
            """,
            (review_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Review item not found.")
        before = dict(existing)
        after = {
            "status": "resolved",
            "resolved_value": payload.resolved_value,
            "resolution_note": payload.resolution_note,
        }
        conn.execute(
            """
            UPDATE review_queue
            SET status = 'resolved',
                resolved_at = ?,
                resolution_note = ?
            WHERE review_id = ?
            """,
            (resolved_at, payload.resolution_note, review_id),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "review_resolved",
                review_id,
                json.dumps(before, ensure_ascii=False),
                json.dumps(after, ensure_ascii=False),
                resolved_at,
            ),
        )
    return {
        "review_id": review_id,
        "status": "resolved",
        "resolved_at": resolved_at,
        "resolution_note": payload.resolution_note,
        "resolved_value": payload.resolved_value,
    }


def suggested_genotyping_fields(normalized_result: str) -> dict[str, str]:
    result = normalized_result.strip()
    if not result:
        return {
            "genotyping_status": "sampled",
            "genotype_result": "",
            "genotype_result_date": "",
            "target_match_status": "unknown",
            "use_category": "unknown",
            "next_action": "awaiting_result",
        }
    if result.lower() in {"failed", "fail", "no result"}:
        return {
            "genotyping_status": "failed",
            "genotype_result": result,
            "target_match_status": "unknown",
            "use_category": "unknown",
            "next_action": "review_result",
        }
    return {
        "genotyping_status": "resulted",
        "genotype_result": result,
        "target_match_status": "unknown",
        "use_category": "unknown",
        "next_action": "review_result",
    }


@app.post("/api/genotyping/update")
def update_genotyping(payload: GenotypingUpdate) -> dict[str, Any]:
    updated_at = utc_now()
    sample_date = payload.sample_date or updated_at[:10]
    normalized_result = payload.normalized_result.strip() or payload.raw_result.strip()
    suggestions = suggested_genotyping_fields(normalized_result)
    result_date = payload.result_date or (updated_at[:10] if normalized_result else "")
    with connection() as conn:
        existing = conn.execute(
            """
            SELECT mouse_id, display_id, sample_id, sample_date, genotyping_status,
                   genotype_result, genotype_result_date, next_action
            FROM mouse_master
            WHERE mouse_id = ?
            """,
            (payload.mouse_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Mouse not found.")
        before = dict(existing)
        conn.execute(
            """
            UPDATE mouse_master
            SET sample_id = ?,
                sample_date = ?,
                genotyping_status = ?,
                genotype = COALESCE(NULLIF(?, ''), genotype),
                genotype_status = ?,
                genotype_result = ?,
                genotype_result_date = ?,
                target_match_status = ?,
                use_category = ?,
                next_action = ?,
                updated_at = ?
            WHERE mouse_id = ?
            """,
            (
                payload.sample_id or before["display_id"],
                sample_date,
                suggestions["genotyping_status"],
                suggestions["genotype_result"],
                "confirmed" if suggestions["genotyping_status"] == "resulted" else "pending",
                suggestions["genotype_result"],
                result_date,
                suggestions["target_match_status"],
                suggestions["use_category"],
                suggestions["next_action"],
                updated_at,
                payload.mouse_id,
            ),
        )
        record_id = new_id("genotyping")
        conn.execute(
            """
            INSERT INTO genotyping_record
                (genotyping_id, mouse_id, sample_id, sample_date, result_date,
                 target_name, raw_result, normalized_result, result_status,
                 confidence, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                payload.mouse_id,
                payload.sample_id or before["display_id"],
                sample_date,
                result_date,
                payload.target_name,
                payload.raw_result,
                normalized_result,
                suggestions["genotyping_status"] if suggestions["genotyping_status"] != "sampled" else "pending",
                1.0 if normalized_result else 0.8,
                payload.notes,
                updated_at,
                updated_at,
            ),
        )
        after = conn.execute(
            """
            SELECT mouse_id, sample_id, sample_date, genotyping_status,
                   genotype_result, genotype_result_date, next_action
            FROM mouse_master
            WHERE mouse_id = ?
            """,
            (payload.mouse_id,),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "genotyping_resulted" if normalized_result else "sample_collected",
                payload.mouse_id,
                json.dumps(before, ensure_ascii=False),
                json.dumps(dict(after), ensure_ascii=False),
                updated_at,
            ),
        )
    return {"genotyping_id": record_id, **dict(after)}


@app.get("/api/genotyping-records")
def list_genotyping_records() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT genotyping_id, mouse_id, sample_id, sample_date, submitted_date,
                   result_date, target_name, raw_result, normalized_result,
                   result_status, source_photo_id, confidence, notes, created_at, updated_at
            FROM genotyping_record
            ORDER BY updated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def contains_filter(columns: list[str], query: str) -> tuple[str, list[str]]:
    normalized = f"%{query.lower()}%"
    clause = " OR ".join([f"LOWER(COALESCE({column}, '')) LIKE ?" for column in columns])
    return f"({clause})", [normalized for _ in columns]


@app.get("/api/note-items")
def list_note_items() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT note_item_id, photo_id, parse_id, card_type, line_number, raw_line_text,
                   strike_status, parsed_type, interpreted_status, parsed_mouse_display_id,
                   parsed_ear_label_raw, parsed_ear_label_code, parsed_ear_label_confidence,
                   parsed_ear_label_review_status, parsed_event_date, parsed_count,
                   confidence, needs_review, created_at
            FROM card_note_item_log
            ORDER BY parse_id, line_number
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/mice")
def list_mice() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT mouse_id, display_id, id_prefix, strain_id, raw_strain_text, sex,
                   genotype, genotype_status, dob_raw, dob_start, dob_end,
                   ear_label_raw, ear_label_code, ear_label_confidence,
                   ear_label_review_status, sample_id, sample_date, genotyping_status,
                   genotype_result, genotype_result_date, target_match_status,
                   use_category, next_action, source_note_item_id,
                   current_card_snapshot_id, status, source_photo_id,
                   created_at, updated_at
            FROM mouse_master
            ORDER BY display_id COLLATE NOCASE, created_at
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/export-preview")
def export_preview() -> dict[str, Any]:
    with connection() as conn:
        photos = conn.execute("SELECT COUNT(*) AS count FROM photo_log").fetchone()["count"]
        open_reviews = conn.execute(
            "SELECT COUNT(*) AS count FROM review_queue WHERE status = 'open'"
        ).fetchone()["count"]
        parsed = conn.execute("SELECT COUNT(*) AS count FROM parse_result").fetchone()["count"]
    return {
        "source_layer": "export or view",
        "photos": photos,
        "parsed_results": parsed,
        "blocked_review_items": open_reviews,
        "ready": open_reviews == 0 and parsed > 0,
    }


@app.post("/api/fixtures/import-sample")
def import_sample_fixture() -> dict[str, Any]:
    if not FIXTURE_PATH.exists():
        raise HTTPException(status_code=404, detail="Sample fixture not found.")
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise HTTPException(status_code=400, detail="Fixture records must be a list.")

    imported = 0
    reviews = 0
    note_items = 0
    mouse_candidates = 0
    with connection() as conn:
        scope = assigned_scope_map(conn)
        for record in records:
            parse_id = record.get("id") or new_id("parse")
            status = str(record.get("status") or "review")
            matched_scope = assigned_scope_match(scope, record)
            if status == "auto" and not matched_scope:
                status = "review"
                record = {
                    **record,
                    "status": status,
                    "issue": "Outside assigned strain scope",
                    "severity": "Medium",
                    "currentValue": record.get("matchedStrain") or record.get("rawStrain") or "",
                    "suggestedValue": "Confirm assigned strain or add to My Assigned Strains",
                    "reviewReason": "Parsed strain is not in My Assigned Strains. Confirm scope before accepting this cage card.",
                }
            elif matched_scope:
                record = {**record, "matchedStrain": matched_scope}
            validation_review = validation_review_for_record(conn, record, status)
            if validation_review:
                status = "review"
                record = {**record, "status": status, **validation_review}
            confidence = float(record.get("confidence") or 0)
            needs_review = 1 if status in {"review", "conflict"} else 0
            conn.execute(
                """
                INSERT OR REPLACE INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parse_id,
                    None,
                    "fixtures/sample_parse_results.json",
                    json.dumps(record, ensure_ascii=False),
                    utc_now(),
                    status,
                    confidence,
                    needs_review,
                ),
            )
            imported += 1
            written_notes, written_mice, written_ear_reviews = write_note_items_and_mouse_candidates(conn, parse_id, record, status)
            note_items += written_notes
            mouse_candidates += written_mice
            reviews += written_ear_reviews
            if needs_review:
                review_id = f"review_{parse_id}"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO review_queue
                        (review_id, parse_id, severity, issue, current_value, suggested_value,
                         review_reason, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        review_id,
                        parse_id,
                        str(record.get("severity") or "Medium"),
                        str(record.get("issue") or "Needs review"),
                        str(record.get("currentValue") or ""),
                        str(record.get("suggestedValue") or ""),
                        str(record.get("reviewReason") or ""),
                        "open",
                        utc_now(),
                    ),
                )
                reviews += 1
            else:
                conn.execute(
                    "DELETE FROM review_queue WHERE review_id = ?",
                    (f"review_{parse_id}",),
                )

    return {
        "imported_parse_results": imported,
        "created_or_updated_review_items": reviews,
        "created_or_updated_note_items": note_items,
        "created_or_updated_mouse_candidates": mouse_candidates,
    }
