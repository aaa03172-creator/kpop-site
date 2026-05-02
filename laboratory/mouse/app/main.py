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


class GenotypingRequestCreate(BaseModel):
    mouse_id: str = Field(min_length=1)
    sample_id: str = ""
    sample_date: str = ""
    target_name: str = ""
    note: str = ""


class StrainTargetGenotypeCreate(BaseModel):
    strain_text: str = Field(min_length=1)
    target_genotype: str = Field(min_length=1)
    purpose: str = "strain_maintenance"


class CageCreate(BaseModel):
    cage_label: str = Field(min_length=1)
    location: str = ""
    rack: str = ""
    shelf: str = ""
    cage_type: str = "holding"
    status: str = "active"
    note: str = ""


class MatingCreate(BaseModel):
    mating_label: str = Field(min_length=1)
    male_mouse_id: str = ""
    female_mouse_id: str = ""
    strain_goal: str = ""
    expected_genotype: str = ""
    start_date: str = ""
    status: str = "active"
    purpose: str = ""
    note: str = ""


class LitterCreate(BaseModel):
    litter_label: str = Field(min_length=1)
    mating_id: str = Field(min_length=1)
    birth_date: str = ""
    number_born: int | None = None
    number_alive: int | None = None
    number_weaned: int | None = None
    weaning_date: str = ""
    status: str = "born"
    note: str = ""


class LitterOffspringCreate(BaseModel):
    count: int = Field(gt=0, le=100)
    display_prefix: str = ""
    start_number: int = Field(default=1, ge=1)
    sex: str = "unknown"
    cage_id: str = ""
    status: str = "weaning_pending"
    note: str = ""


class LitterWeanCreate(BaseModel):
    weaning_date: str = ""
    number_weaned: int | None = Field(default=None, ge=0)
    note: str = ""


class MouseCageMove(BaseModel):
    cage_id: str = Field(min_length=1)
    note: str = ""
    moved_at: str = ""


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


def compact_genotype(value: str) -> str:
    return re.sub(r"\s+", "", value or "").lower()


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


def target_suggestion(conn: Any, mouse_row: Any, normalized_result: str) -> dict[str, str]:
    result_key = compact_genotype(normalized_result)
    if not result_key:
        return {"target_match_status": "unknown", "use_category": "unknown", "next_action": "awaiting_result"}
    rows = conn.execute(
        """
        SELECT target_genotype, purpose
        FROM strain_target_genotype
        WHERE active = 1 AND strain_text = ?
        ORDER BY created_at DESC
        """,
        (mouse_row["raw_strain_text"],),
    ).fetchall()
    if not rows:
        return {"target_match_status": "unknown", "use_category": "unknown", "next_action": "review_result"}
    for row in rows:
        if compact_genotype(row["target_genotype"]) == result_key:
            purpose = row["purpose"] or "unknown"
            if purpose == "mating_candidate":
                return {"target_match_status": "matches_target", "use_category": "mating_candidate", "next_action": "consider_for_mating"}
            if purpose == "experimental_cross":
                return {"target_match_status": "matches_target", "use_category": "experimental_candidate", "next_action": "available_for_experiment"}
            if purpose == "backup":
                return {"target_match_status": "matches_target", "use_category": "backup", "next_action": "review_needed"}
            return {"target_match_status": "matches_target", "use_category": "maintenance_candidate", "next_action": "keep_for_maintenance"}
    return {"target_match_status": "does_not_match_target", "use_category": "cleanup_candidate", "next_action": "cleanup_or_confirm"}


def suggested_genotyping_fields(normalized_result: str, target: dict[str, str] | None = None) -> dict[str, str]:
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
    if target:
        return {
            "genotyping_status": "resulted",
            "genotype_result": result,
            **target,
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
    result_date = payload.result_date or (updated_at[:10] if normalized_result else "")
    with connection() as conn:
        existing = conn.execute(
            """
            SELECT mouse_id, display_id, sample_id, sample_date, genotyping_status,
                   raw_strain_text, genotype_result, genotype_result_date, next_action
            FROM mouse_master
            WHERE mouse_id = ?
            """,
            (payload.mouse_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Mouse not found.")
        before = dict(existing)
        target = target_suggestion(conn, existing, normalized_result) if normalized_result else None
        suggestions = suggested_genotyping_fields(normalized_result, target)
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
                   genotype_result, genotype_result_date, target_match_status,
                   use_category, next_action
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


@app.post("/api/genotyping/request")
def request_genotyping(payload: GenotypingRequestCreate) -> dict[str, Any]:
    requested_at = utc_now()
    sample_date = payload.sample_date or requested_at[:10]
    with connection() as conn:
        existing = conn.execute(
            """
            SELECT mouse_id, display_id, sample_id, sample_date, genotyping_status,
                   genotype_result, next_action, raw_strain_text
            FROM mouse_master
            WHERE mouse_id = ?
            """,
            (payload.mouse_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Mouse not found.")
        if existing["genotyping_status"] == "resulted":
            raise HTTPException(status_code=409, detail="Mouse already has a genotyping result.")

        before = dict(existing)
        sample_id = payload.sample_id.strip() or existing["display_id"]
        raw_payload = payload.model_dump_json()
        source_record_id = create_source_record(
            conn,
            source_type="manual_entry",
            source_label=f"Manual genotyping request: {existing['display_id']}",
            raw_payload=raw_payload,
            note="Tail biopsy / genotyping request entered from local Genotyping Worklist.",
        )
        conn.execute(
            """
            UPDATE mouse_master
            SET sample_id = ?,
                sample_date = ?,
                genotyping_status = 'submitted',
                genotype_status = 'pending',
                next_action = 'awaiting_result',
                updated_at = ?
            WHERE mouse_id = ?
            """,
            (sample_id, sample_date, requested_at, payload.mouse_id),
        )
        record_id = new_id("genotyping")
        conn.execute(
            """
            INSERT INTO genotyping_record
                (genotyping_id, mouse_id, sample_id, sample_date, submitted_date,
                 target_name, raw_result, normalized_result, result_status,
                 confidence, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                payload.mouse_id,
                sample_id,
                sample_date,
                requested_at[:10],
                payload.target_name,
                "",
                "",
                "pending",
                1.0,
                payload.note,
                requested_at,
                requested_at,
            ),
        )
        for event_type in ["tail_biopsy", "genotyping_requested"]:
            conn.execute(
                """
                INSERT INTO mouse_event
                    (event_id, mouse_id, event_type, event_date, related_entity_type,
                     related_entity_id, source_record_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("event"),
                    payload.mouse_id,
                    event_type,
                    sample_date,
                    "genotyping_record",
                    record_id,
                    source_record_id,
                    json.dumps(
                        {
                            "display_id": existing["display_id"],
                            "sample_id": sample_id,
                            "target_name": payload.target_name,
                            "note": payload.note,
                        },
                        ensure_ascii=False,
                    ),
                    requested_at,
                ),
            )
        after = conn.execute(
            """
            SELECT mouse_id, display_id, sample_id, sample_date,
                   genotyping_status, genotype_status, next_action
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
                "genotyping_requested",
                payload.mouse_id,
                json.dumps(before, ensure_ascii=False),
                json.dumps(dict(after), ensure_ascii=False),
                requested_at,
            ),
        )

    return {
        "genotyping_id": record_id,
        "source_record_id": source_record_id,
        **dict(after),
    }


@app.get("/api/strain-target-genotypes")
def list_strain_target_genotypes() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT target_id, strain_text, target_genotype, purpose, active, created_at
            FROM strain_target_genotype
            ORDER BY active DESC, strain_text COLLATE NOCASE, created_at DESC
            """
        ).fetchall()
    result = []
    for row in rows:
        payload = dict(row)
        payload["active"] = bool(payload["active"])
        result.append(payload)
    return result


@app.post("/api/strain-target-genotypes")
def create_strain_target_genotype(payload: StrainTargetGenotypeCreate) -> dict[str, Any]:
    target_id = new_id("target_genotype")
    created_at = utc_now()
    strain_text = " ".join(payload.strain_text.split())
    target_genotype = " ".join(payload.target_genotype.split())
    with connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO strain_target_genotype
                (target_id, strain_text, target_genotype, purpose, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (target_id, strain_text, target_genotype, payload.purpose, 1, created_at),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "strain_target_genotype_created",
                target_id,
                None,
                json.dumps({"strain_text": strain_text, "target_genotype": target_genotype, "purpose": payload.purpose}, ensure_ascii=False),
                created_at,
            ),
        )
    return {
        "target_id": target_id,
        "strain_text": strain_text,
        "target_genotype": target_genotype,
        "purpose": payload.purpose,
        "active": True,
        "created_at": created_at,
    }


@app.get("/api/cages")
def list_cages() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT c.cage_id, c.cage_label, c.location, c.rack, c.shelf,
                   c.cage_type, c.status, c.note, c.source_record_id,
                   c.created_at, c.updated_at,
                   COUNT(a.assignment_id) AS active_mouse_count
            FROM cage_registry c
            LEFT JOIN mouse_cage_assignment a
                ON a.cage_id = c.cage_id AND a.status = 'active'
            GROUP BY c.cage_id
            ORDER BY c.status = 'active' DESC, c.cage_label COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/cages")
def create_cage(payload: CageCreate) -> dict[str, Any]:
    cage_label = " ".join(payload.cage_label.split())
    if not cage_label:
        raise HTTPException(status_code=400, detail="Cage label is required.")
    now = utc_now()
    cage_id = new_id("cage")
    raw_payload = payload.model_dump_json()
    with connection() as conn:
        duplicate = conn.execute(
            "SELECT cage_id FROM cage_registry WHERE LOWER(cage_label) = LOWER(?)",
            (cage_label,),
        ).fetchone()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Cage label already exists.")
        source_record_id = create_source_record(
            conn,
            source_type="manual_entry",
            source_label=f"Manual cage registry entry: {cage_label}",
            raw_payload=raw_payload,
            note="Created from local Cage View form.",
        )
        conn.execute(
            """
            INSERT INTO cage_registry
                (cage_id, cage_label, location, rack, shelf, cage_type, status,
                 note, source_record_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cage_id,
                cage_label,
                payload.location,
                payload.rack,
                payload.shelf,
                payload.cage_type or "holding",
                payload.status or "active",
                payload.note,
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
            (new_id("action"), "cage_created", cage_id, None, raw_payload, now),
        )
    return {
        "cage_id": cage_id,
        "cage_label": cage_label,
        "status": payload.status or "active",
        "source_record_id": source_record_id,
        "created_at": now,
    }


@app.post("/api/mice/{mouse_id}/move-cage")
def move_mouse_to_cage(mouse_id: str, payload: MouseCageMove) -> dict[str, Any]:
    moved_at = payload.moved_at or utc_now()
    event_date = moved_at[:10]
    with connection() as conn:
        mouse = conn.execute(
            "SELECT mouse_id, display_id FROM mouse_master WHERE mouse_id = ?",
            (mouse_id,),
        ).fetchone()
        if mouse is None:
            raise HTTPException(status_code=404, detail="Mouse not found.")
        cage = conn.execute(
            "SELECT cage_id, cage_label FROM cage_registry WHERE cage_id = ?",
            (payload.cage_id,),
        ).fetchone()
        if cage is None:
            raise HTTPException(status_code=404, detail="Cage not found.")
        previous = conn.execute(
            """
            SELECT a.assignment_id, c.cage_id, c.cage_label
            FROM mouse_cage_assignment a
            JOIN cage_registry c ON c.cage_id = a.cage_id
            WHERE a.mouse_id = ? AND a.status = 'active'
            ORDER BY a.assigned_at DESC
            LIMIT 1
            """,
            (mouse_id,),
        ).fetchone()
        source_record_id = create_source_record(
            conn,
            source_type="manual_entry",
            source_label=f"Manual cage move: {mouse['display_id']} -> {cage['cage_label']}",
            raw_payload=json.dumps(
                {
                    "mouse_id": mouse_id,
                    "display_id": mouse["display_id"],
                    "cage_id": payload.cage_id,
                    "cage_label": cage["cage_label"],
                    "note": payload.note,
                },
                ensure_ascii=False,
            ),
            note="Mouse cage assignment created from local Cage View form.",
        )
        conn.execute(
            """
            UPDATE mouse_cage_assignment
            SET status = 'ended', ended_at = ?
            WHERE mouse_id = ? AND status = 'active'
            """,
            (moved_at, mouse_id),
        )
        assignment_id = new_id("cage_assignment")
        conn.execute(
            """
            INSERT INTO mouse_cage_assignment
                (assignment_id, mouse_id, cage_id, status, assigned_at,
                 source_record_id, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (assignment_id, mouse_id, payload.cage_id, "active", moved_at, source_record_id, payload.note),
        )
        event_id = new_id("event")
        details = {
            "display_id": mouse["display_id"],
            "from_cage_label": previous["cage_label"] if previous else "",
            "to_cage_label": cage["cage_label"],
            "note": payload.note,
        }
        conn.execute(
            """
            INSERT INTO mouse_event
                (event_id, mouse_id, event_type, event_date, related_entity_type,
                 related_entity_id, source_record_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                mouse_id,
                "moved",
                event_date,
                "cage",
                payload.cage_id,
                source_record_id,
                json.dumps(details, ensure_ascii=False),
                moved_at,
            ),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "mouse_cage_moved",
                mouse_id,
                json.dumps(dict(previous) if previous else {}, ensure_ascii=False),
                json.dumps({"cage_id": payload.cage_id, "cage_label": cage["cage_label"]}, ensure_ascii=False),
                moved_at,
            ),
        )
    return {
        "assignment_id": assignment_id,
        "mouse_id": mouse_id,
        "cage_id": payload.cage_id,
        "cage_label": cage["cage_label"],
        "source_record_id": source_record_id,
        "event_id": event_id,
        "assigned_at": moved_at,
    }


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


@app.get("/api/genotyping-dashboard")
def genotyping_dashboard() -> list[dict[str, Any]]:
    cards = [
        (
            "not_sampled",
            "Not sampled",
            "Separated active mice that still need tail sampling.",
            "status = 'active' AND genotyping_status = 'not_sampled'",
        ),
        (
            "awaiting_result",
            "Awaiting result",
            "Sampled or submitted mice without an accepted genotype result.",
            "status = 'active' AND (genotyping_status IN ('sampled', 'submitted', 'pending') OR next_action = 'awaiting_result')",
        ),
        (
            "failed_ambiguous",
            "Failed / ambiguous",
            "Genotyping records that need retry, interpretation, or review.",
            "status = 'active' AND (genotyping_status = 'failed' OR next_action = 'review_result')",
        ),
        (
            "target_confirmed",
            "Target genotype confirmed",
            "Mice whose result matches a configured strain-level target genotype.",
            "status = 'active' AND genotyping_status = 'resulted' AND target_match_status = 'matches_target'",
        ),
        (
            "non_target",
            "Non-target genotype",
            "Resulted mice that do not match configured target genotype.",
            "status = 'active' AND genotyping_status = 'resulted' AND target_match_status = 'does_not_match_target'",
        ),
        (
            "review_needed",
            "Review needed",
            "Mice with genotype workflow state that should not be acted on silently.",
            "status = 'active' AND (next_action = 'review_needed' OR use_category = 'unknown' OR target_match_status = 'unknown')",
        ),
    ]
    with connection() as conn:
        result = []
        for key, label, meaning, where in cards:
            row = conn.execute(
                f"SELECT COUNT(*) AS count FROM mouse_master WHERE {where}"
            ).fetchone()
            result.append(
                {
                    "key": key,
                    "label": label,
                    "count": row["count"],
                    "meaning": meaning,
                }
            )
    return result


@app.get("/api/matings")
def list_matings() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT m.mating_id, m.mating_label, m.strain_goal, m.expected_genotype,
                   m.start_date, m.end_date, m.status, m.purpose, m.note,
                   m.source_record_id, m.created_at, m.updated_at,
                   COALESCE((
                       SELECT GROUP_CONCAT(mm.mouse_id || ':' || mouse.display_id, ', ')
                       FROM mating_mouse mm
                       JOIN mouse_master mouse ON mouse.mouse_id = mm.mouse_id
                       WHERE mm.mating_id = m.mating_id AND mm.role = 'male'
                   ), '') AS male_mice,
                   COALESCE((
                       SELECT GROUP_CONCAT(mm.mouse_id || ':' || mouse.display_id, ', ')
                       FROM mating_mouse mm
                       JOIN mouse_master mouse ON mouse.mouse_id = mm.mouse_id
                       WHERE mm.mating_id = m.mating_id AND mm.role = 'female'
                   ), '') AS female_mice,
                   (
                       SELECT COUNT(*)
                       FROM litter_registry l
                       WHERE l.mating_id = m.mating_id
                   ) AS litter_count
            FROM mating_registry m
            ORDER BY m.status = 'active' DESC, m.start_date DESC, m.created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/matings")
def create_mating(payload: MatingCreate) -> dict[str, Any]:
    mating_label = " ".join(payload.mating_label.split())
    if not mating_label:
        raise HTTPException(status_code=400, detail="Mating label is required.")

    parent_ids = [
        ("male", payload.male_mouse_id.strip()),
        ("female", payload.female_mouse_id.strip()),
    ]
    parent_ids = [(role, mouse_id) for role, mouse_id in parent_ids if mouse_id]
    if not parent_ids:
        raise HTTPException(status_code=400, detail="At least one mouse is required for a mating.")

    now = utc_now()
    start_date = payload.start_date or now[:10]
    mating_id = new_id("mating")
    raw_payload = payload.model_dump_json()

    with connection() as conn:
        duplicate = conn.execute(
            "SELECT mating_id FROM mating_registry WHERE LOWER(mating_label) = LOWER(?) AND status = 'active'",
            (mating_label,),
        ).fetchone()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Active mating label already exists.")
        parent_rows: dict[str, Any] = {}
        for _, mouse_id in parent_ids:
            mouse = conn.execute(
                "SELECT mouse_id, display_id FROM mouse_master WHERE mouse_id = ?",
                (mouse_id,),
            ).fetchone()
            if mouse is None:
                raise HTTPException(status_code=404, detail=f"Mouse not found: {mouse_id}")
            parent_rows[mouse_id] = mouse

        source_record_id = create_source_record(
            conn,
            source_type="manual_entry",
            source_label=f"Manual mating entry: {mating_label}",
            raw_payload=raw_payload,
            note="Created from local Breeding / Litter View form.",
        )
        conn.execute(
            """
            INSERT INTO mating_registry
                (mating_id, mating_label, strain_goal, expected_genotype, start_date,
                 status, purpose, note, source_record_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mating_id,
                mating_label,
                payload.strain_goal,
                payload.expected_genotype,
                start_date,
                payload.status or "active",
                payload.purpose,
                payload.note,
                source_record_id,
                now,
                now,
            ),
        )
        for role, mouse_id in parent_ids:
            conn.execute(
                """
                INSERT INTO mating_mouse
                    (mating_mouse_id, mating_id, mouse_id, role, joined_date,
                     note, source_record_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id("mating_mouse"), mating_id, mouse_id, role, start_date, payload.note, source_record_id, now),
            )
            conn.execute(
                """
                INSERT INTO mouse_event
                    (event_id, mouse_id, event_type, event_date, related_entity_type,
                     related_entity_id, source_record_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("event"),
                    mouse_id,
                    "paired",
                    start_date,
                    "mating",
                    mating_id,
                    source_record_id,
                    json.dumps(
                        {
                            "mating_label": mating_label,
                            "role": role,
                            "display_id": parent_rows[mouse_id]["display_id"],
                            "strain_goal": payload.strain_goal,
                            "expected_genotype": payload.expected_genotype,
                        },
                        ensure_ascii=False,
                    ),
                    now,
                ),
            )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_id("action"), "mating_created", mating_id, None, raw_payload, now),
        )

    return {
        "mating_id": mating_id,
        "mating_label": mating_label,
        "status": payload.status or "active",
        "source_record_id": source_record_id,
        "created_at": now,
    }


@app.get("/api/litters")
def list_litters() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT l.litter_id, l.litter_label, l.mating_id, m.mating_label,
                   l.birth_date, l.number_born, l.number_alive, l.number_weaned,
                   l.weaning_date, l.status, l.note, l.source_record_id,
                   l.created_at, l.updated_at,
                   (
                       SELECT COUNT(*)
                       FROM mouse_master mouse
                       WHERE mouse.litter_id = l.litter_id
                   ) AS offspring_count
            FROM litter_registry l
            JOIN mating_registry m ON m.mating_id = l.mating_id
            ORDER BY l.birth_date DESC, l.created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/litters")
def create_litter(payload: LitterCreate) -> dict[str, Any]:
    litter_label = " ".join(payload.litter_label.split())
    if not litter_label:
        raise HTTPException(status_code=400, detail="Litter label is required.")

    now = utc_now()
    birth_date = payload.birth_date or now[:10]
    litter_id = new_id("litter")
    raw_payload = payload.model_dump_json()
    with connection() as conn:
        mating = conn.execute(
            "SELECT mating_id, mating_label FROM mating_registry WHERE mating_id = ?",
            (payload.mating_id,),
        ).fetchone()
        if mating is None:
            raise HTTPException(status_code=404, detail="Mating not found.")
        duplicate = conn.execute(
            "SELECT litter_id FROM litter_registry WHERE LOWER(litter_label) = LOWER(?) AND mating_id = ?",
            (litter_label, payload.mating_id),
        ).fetchone()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Litter label already exists for this mating.")

        source_record_id = create_source_record(
            conn,
            source_type="manual_entry",
            source_label=f"Manual litter entry: {litter_label}",
            raw_payload=raw_payload,
            note="Created from local Breeding / Litter View form.",
        )
        conn.execute(
            """
            INSERT INTO litter_registry
                (litter_id, litter_label, mating_id, birth_date, number_born,
                 number_alive, number_weaned, weaning_date, status, note,
                 source_record_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                litter_id,
                litter_label,
                payload.mating_id,
                birth_date,
                payload.number_born,
                payload.number_alive,
                payload.number_weaned,
                payload.weaning_date,
                payload.status or "born",
                payload.note,
                source_record_id,
                now,
                now,
            ),
        )
        parents = conn.execute(
            """
            SELECT mm.mouse_id, mm.role, mouse.display_id
            FROM mating_mouse mm
            JOIN mouse_master mouse ON mouse.mouse_id = mm.mouse_id
            WHERE mm.mating_id = ?
            """,
            (payload.mating_id,),
        ).fetchall()
        for parent in parents:
            conn.execute(
                """
                INSERT INTO mouse_event
                    (event_id, mouse_id, event_type, event_date, related_entity_type,
                     related_entity_id, source_record_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("event"),
                    parent["mouse_id"],
                    "litter_produced",
                    birth_date,
                    "litter",
                    litter_id,
                    source_record_id,
                    json.dumps(
                        {
                            "litter_label": litter_label,
                            "mating_label": mating["mating_label"],
                            "role": parent["role"],
                            "display_id": parent["display_id"],
                            "number_born": payload.number_born,
                            "number_alive": payload.number_alive,
                        },
                        ensure_ascii=False,
                    ),
                    now,
                ),
            )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_id("action"), "litter_created", litter_id, None, raw_payload, now),
        )

    return {
        "litter_id": litter_id,
        "litter_label": litter_label,
        "mating_id": payload.mating_id,
        "status": payload.status or "born",
        "source_record_id": source_record_id,
        "created_at": now,
    }


@app.post("/api/litters/{litter_id}/offspring")
def create_litter_offspring(litter_id: str, payload: LitterOffspringCreate) -> dict[str, Any]:
    now = utc_now()
    raw_payload = payload.model_dump_json()
    with connection() as conn:
        litter = conn.execute(
            """
            SELECT l.litter_id, l.litter_label, l.mating_id, l.birth_date,
                   l.number_born, l.number_alive, m.mating_label, m.strain_goal
            FROM litter_registry l
            JOIN mating_registry m ON m.mating_id = l.mating_id
            WHERE l.litter_id = ?
            """,
            (litter_id,),
        ).fetchone()
        if litter is None:
            raise HTTPException(status_code=404, detail="Litter not found.")
        cage = None
        cage_id = payload.cage_id.strip()
        if cage_id:
            cage = conn.execute(
                "SELECT cage_id, cage_label FROM cage_registry WHERE cage_id = ?",
                (cage_id,),
            ).fetchone()
            if cage is None:
                raise HTTPException(status_code=404, detail="Cage not found.")

        parent_rows = conn.execute(
            """
            SELECT mouse_id, role
            FROM mating_mouse
            WHERE mating_id = ? AND removed_date IS NULL
            """,
            (litter["mating_id"],),
        ).fetchall()
        father_id = next((row["mouse_id"] for row in parent_rows if row["role"] == "male"), None)
        mother_id = next((row["mouse_id"] for row in parent_rows if row["role"] == "female"), None)
        display_prefix = " ".join(payload.display_prefix.split()) or litter["litter_label"]
        planned = []
        for offset in range(payload.count):
            number = payload.start_number + offset
            display_id = f"{display_prefix}-{number:02d}"
            mouse_id = f"mouse_{litter_id}_{number:02d}".replace(" ", "_")
            planned.append((mouse_id, display_id))
        placeholders = ",".join(["?"] * len(planned))
        duplicate = conn.execute(
            f"SELECT mouse_id FROM mouse_master WHERE mouse_id IN ({placeholders}) LIMIT 1",
            [mouse_id for mouse_id, _display_id in planned],
        ).fetchone()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="One or more offspring IDs already exist for this litter.")

        source_record_id = create_source_record(
            conn,
            source_type="manual_entry",
            source_label=f"Manual offspring generation: {litter['litter_label']}",
            raw_payload=raw_payload,
            note="Generated offspring mouse cards from a reviewed litter record.",
        )
        created = []
        for mouse_id, display_id in planned:
            conn.execute(
                """
                INSERT INTO mouse_master
                    (mouse_id, display_id, id_prefix, father_id, mother_id, litter_id,
                     raw_strain_text, sex, dob_raw, dob_start, status, use_category,
                     next_action, source_record_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mouse_id,
                    display_id,
                    mouse_id_prefix(display_id),
                    father_id,
                    mother_id,
                    litter_id,
                    litter["strain_goal"] or "",
                    payload.sex or "unknown",
                    litter["birth_date"] or "",
                    litter["birth_date"] or "",
                    payload.status or "weaning_pending",
                    "stock",
                    "weaning_due" if payload.status == "weaning_pending" else "sample_needed",
                    source_record_id,
                    now,
                    now,
                ),
            )
            if cage is not None:
                conn.execute(
                    """
                    INSERT INTO mouse_cage_assignment
                        (assignment_id, mouse_id, cage_id, status, assigned_at,
                         source_record_id, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id("cage_assignment"),
                        mouse_id,
                        cage["cage_id"],
                        "active",
                        now,
                        source_record_id,
                        payload.note,
                    ),
                )
            conn.execute(
                """
                INSERT INTO mouse_event
                    (event_id, mouse_id, event_type, event_date, related_entity_type,
                     related_entity_id, source_record_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("event"),
                    mouse_id,
                    "born",
                    litter["birth_date"] or now[:10],
                    "litter",
                    litter_id,
                    source_record_id,
                    json.dumps(
                        {
                            "display_id": display_id,
                            "litter_label": litter["litter_label"],
                            "mating_label": litter["mating_label"],
                            "father_id": father_id,
                            "mother_id": mother_id,
                            "cage_label": cage["cage_label"] if cage else "",
                        },
                        ensure_ascii=False,
                    ),
                    now,
                ),
            )
            created.append({"mouse_id": mouse_id, "display_id": display_id})

        conn.execute(
            """
            UPDATE litter_registry
            SET number_alive = COALESCE(number_alive, ?),
                status = CASE WHEN status = 'born' THEN 'pre_weaning' ELSE status END,
                updated_at = ?
            WHERE litter_id = ?
            """,
            (payload.count, now, litter_id),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "offspring_created",
                litter_id,
                None,
                json.dumps(
                    {
                        "litter_id": litter_id,
                        "created_count": len(created),
                        "source_record_id": source_record_id,
                    },
                    ensure_ascii=False,
                ),
                now,
            ),
        )

    return {
        "litter_id": litter_id,
        "created_count": len(created),
        "created_mice": created,
        "source_record_id": source_record_id,
        "created_at": now,
    }


@app.post("/api/litters/{litter_id}/wean")
def wean_litter(litter_id: str, payload: LitterWeanCreate) -> dict[str, Any]:
    now = utc_now()
    weaning_date = payload.weaning_date or now[:10]
    raw_payload = payload.model_dump_json()
    with connection() as conn:
        litter = conn.execute(
            """
            SELECT l.litter_id, l.litter_label, l.mating_id, l.birth_date,
                   l.number_born, l.number_alive, l.number_weaned, l.weaning_date,
                   l.status, m.mating_label
            FROM litter_registry l
            JOIN mating_registry m ON m.mating_id = l.mating_id
            WHERE l.litter_id = ?
            """,
            (litter_id,),
        ).fetchone()
        if litter is None:
            raise HTTPException(status_code=404, detail="Litter not found.")
        if litter["status"] == "weaned":
            raise HTTPException(status_code=409, detail="Litter is already weaned.")

        offspring_rows = conn.execute(
            """
            SELECT mouse_id, display_id, status
            FROM mouse_master
            WHERE litter_id = ?
            ORDER BY display_id COLLATE NOCASE
            """,
            (litter_id,),
        ).fetchall()
        requested_count = payload.number_weaned
        if requested_count is None:
            requested_count = len(offspring_rows) if offspring_rows else (litter["number_alive"] or litter["number_born"] or 0)
        if offspring_rows and requested_count > len(offspring_rows):
            raise HTTPException(status_code=409, detail="Weaned count exceeds generated offspring records.")

        source_record_id = create_source_record(
            conn,
            source_type="manual_entry",
            source_label=f"Manual litter weaning: {litter['litter_label']}",
            raw_payload=raw_payload,
            note="Weaning completion entered from local Breeding / Litter View.",
        )
        before = dict(litter)
        selected_offspring = offspring_rows[:requested_count]
        conn.execute(
            """
            UPDATE litter_registry
            SET number_weaned = ?,
                weaning_date = ?,
                status = 'weaned',
                updated_at = ?
            WHERE litter_id = ?
            """,
            (requested_count, weaning_date, now, litter_id),
        )
        for offspring in selected_offspring:
            conn.execute(
                """
                UPDATE mouse_master
                SET status = CASE WHEN status IN ('weaning_pending', 'pre_weaning') THEN 'active' ELSE status END,
                    next_action = CASE WHEN next_action = 'weaning_due' THEN 'sample_needed' ELSE next_action END,
                    updated_at = ?
                WHERE mouse_id = ?
                """,
                (now, offspring["mouse_id"]),
            )
            conn.execute(
                """
                INSERT INTO mouse_event
                    (event_id, mouse_id, event_type, event_date, related_entity_type,
                     related_entity_id, source_record_id, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("event"),
                    offspring["mouse_id"],
                    "weaned",
                    weaning_date,
                    "litter",
                    litter_id,
                    source_record_id,
                    json.dumps(
                        {
                            "display_id": offspring["display_id"],
                            "litter_label": litter["litter_label"],
                            "mating_label": litter["mating_label"],
                            "previous_status": offspring["status"],
                            "note": payload.note,
                        },
                        ensure_ascii=False,
                    ),
                    now,
                ),
            )
        after = {
            "litter_id": litter_id,
            "status": "weaned",
            "number_weaned": requested_count,
            "weaning_date": weaning_date,
            "source_record_id": source_record_id,
            "weaned_mouse_ids": [row["mouse_id"] for row in selected_offspring],
        }
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "litter_weaned",
                litter_id,
                json.dumps(before, ensure_ascii=False),
                json.dumps(after, ensure_ascii=False),
                now,
            ),
        )

    return {
        "litter_id": litter_id,
        "status": "weaned",
        "number_weaned": requested_count,
        "weaning_date": weaning_date,
        "weaned_mouse_count": len(selected_offspring),
        "source_record_id": source_record_id,
        "updated_at": now,
    }


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


MOUSE_SELECT = """
    SELECT mouse_id, display_id, id_prefix, strain_id, father_id, mother_id,
           litter_id, raw_strain_text, sex,
           genotype, genotype_status, dob_raw, dob_start, dob_end,
           ear_label_raw, ear_label_code, ear_label_confidence,
           ear_label_review_status, sample_id, sample_date, genotyping_status,
           genotype_result, genotype_result_date, target_match_status,
           use_category, next_action, source_note_item_id,
           current_card_snapshot_id, status, source_photo_id, source_record_id,
           created_at, updated_at,
           (
               SELECT a.cage_id
               FROM mouse_cage_assignment a
               WHERE a.mouse_id = mouse_master.mouse_id AND a.status = 'active'
               ORDER BY a.assigned_at DESC
               LIMIT 1
           ) AS current_cage_id,
           (
               SELECT c.cage_label
               FROM mouse_cage_assignment a
               JOIN cage_registry c ON c.cage_id = a.cage_id
               WHERE a.mouse_id = mouse_master.mouse_id AND a.status = 'active'
               ORDER BY a.assigned_at DESC
               LIMIT 1
           ) AS current_cage_label
    FROM mouse_master
"""


def mouse_rows(conn: Any, query: str = "") -> list[Any]:
    params: list[str] = []
    where = ""
    if query.strip():
        normalized = f"%{query.strip().lower()}%"
        clause, params = contains_filter(
            [
                "display_id",
                "raw_strain_text",
                "sex",
                "genotype",
                "genotype_status",
                "dob_raw",
                "ear_label_raw",
                "ear_label_code",
                "sample_id",
                "genotyping_status",
                "genotype_result",
                "use_category",
                "next_action",
                "status",
                "source_note_item_id",
            ],
            query.strip(),
        )
        where = f"""
        WHERE {clause}
           OR EXISTS (
               SELECT 1
               FROM mouse_cage_assignment a
               JOIN cage_registry c ON c.cage_id = a.cage_id
               WHERE a.mouse_id = mouse_master.mouse_id
                 AND a.status = 'active'
                 AND LOWER(COALESCE(c.cage_label, '') || ' ' || COALESCE(c.location, '')) LIKE ?
           )
        """
        params.append(normalized)
    return conn.execute(
        f"""
        {MOUSE_SELECT}
        {where}
        ORDER BY display_id COLLATE NOCASE, created_at
        """,
        params,
    ).fetchall()


@app.get("/api/mice")
def list_mice(query: str = "") -> list[dict[str, Any]]:
    with connection() as conn:
        rows = mouse_rows(conn, query)
    return [dict(row) for row in rows]


@app.get("/api/search")
def search_records(query: str = "") -> dict[str, Any]:
    term = query.strip()
    if not term:
        return {"query": "", "mice": [], "strains": [], "reviews": [], "sources": []}

    with connection() as conn:
        mouse_matches = [dict(row) for row in mouse_rows(conn, term)[:25]]
        strain_clause, strain_params = contains_filter(
            ["strain_name", "common_name", "official_name", "gene", "allele", "background", "source", "status", "owner"],
            term,
        )
        strains = conn.execute(
            f"""
            SELECT strain_id, strain_name, gene, allele, background, source, status, owner
            FROM strain_registry
            WHERE {strain_clause}
            ORDER BY strain_name COLLATE NOCASE
            LIMIT 25
            """,
            strain_params,
        ).fetchall()
        review_clause, review_params = contains_filter(
            ["parse_id", "severity", "issue", "current_value", "suggested_value", "review_reason", "status"],
            term,
        )
        reviews = conn.execute(
            f"""
            SELECT review_id, parse_id, severity, issue, suggested_value, status
            FROM review_queue
            WHERE {review_clause}
            ORDER BY created_at DESC
            LIMIT 25
            """,
            review_params,
        ).fetchall()
        source_clause, source_params = contains_filter(
            ["source_type", "source_uri", "source_label", "raw_payload", "note"],
            term,
        )
        sources = conn.execute(
            f"""
            SELECT source_record_id, source_type, source_label, source_uri, note, imported_at
            FROM source_record
            WHERE {source_clause}
            ORDER BY imported_at DESC
            LIMIT 25
            """,
            source_params,
        ).fetchall()

    return {
        "query": term,
        "mice": mouse_matches,
        "strains": [dict(row) for row in strains],
        "reviews": [dict(row) for row in reviews],
        "sources": [dict(row) for row in sources],
    }


@app.get("/api/exports/mice.csv")
def export_mice_csv(query: str = "", require_ready: bool = False) -> Response:
    output = io.StringIO()
    fieldnames = [
        "mouse_id",
        "display_id",
        "raw_strain_text",
        "father_id",
        "mother_id",
        "litter_id",
        "sex",
        "dob_raw",
        "dob_start",
        "dob_end",
        "ear_label_raw",
        "ear_label_code",
        "status",
        "current_cage_label",
        "genotyping_status",
        "sample_id",
        "sample_date",
        "genotype_result",
        "genotype_result_date",
        "target_match_status",
        "use_category",
        "next_action",
        "source_note_item_id",
        "source_record_id",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    row_count = 0
    blocked_error: dict[str, Any] | None = None
    with connection() as conn:
        for row in mouse_rows(conn, query):
            payload = dict(row)
            writer.writerow({field: payload.get(field, "") for field in fieldnames})
            row_count += 1
        blocked_review_count = conn.execute(
            "SELECT COUNT(*) AS count FROM review_queue WHERE status = 'open'"
        ).fetchone()["count"]
        suffix = "_filtered" if query.strip() else ""
        filename = f"mouse_records{suffix}.csv"
        export_status = "blocked" if require_ready and blocked_review_count else "generated"
        note = (
            "Blocked final CSV export because open review items remain."
            if export_status == "blocked"
            else "Generated from local mouse records CSV endpoint."
        )
        conn.execute(
            """
            INSERT INTO export_log
                (export_id, export_type, filename, query, row_count,
                 blocked_review_count, status, exported_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("export"),
                "mouse_csv",
                filename,
                query.strip(),
                row_count,
                blocked_review_count,
                export_status,
                utc_now(),
                note,
            ),
        )
        if export_status == "blocked":
            blocked_error = {
                "blocked_review_count": blocked_review_count,
                "filename": filename,
                "source_layer": "export or view",
            }

    if blocked_error:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Resolve open review items before final export.",
                **blocked_error,
            },
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/exports/genotyping-worklist.csv")
def export_genotyping_worklist_csv(query: str = "") -> Response:
    output = io.StringIO()
    fieldnames = [
        "display_id",
        "ear_label",
        "strain",
        "dob",
        "current_cage",
        "sample_id",
        "sample_date",
        "genotyping_status",
        "genotype_result",
        "genotype_result_date",
        "target_match_status",
        "use_category",
        "next_action",
        "source_note_item_id",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    row_count = 0
    with connection() as conn:
        for row in mouse_rows(conn, query):
            payload = dict(row)
            writer.writerow(
                {
                    "display_id": payload.get("display_id", ""),
                    "ear_label": payload.get("ear_label_raw") or payload.get("ear_label_code") or "",
                    "strain": payload.get("raw_strain_text", ""),
                    "dob": payload.get("dob_raw") or payload.get("dob_start") or "",
                    "current_cage": payload.get("current_cage_label") or "",
                    "sample_id": payload.get("sample_id") or "",
                    "sample_date": payload.get("sample_date") or "",
                    "genotyping_status": payload.get("genotyping_status") or "",
                    "genotype_result": payload.get("genotype_result") or "",
                    "genotype_result_date": payload.get("genotype_result_date") or "",
                    "target_match_status": payload.get("target_match_status") or "",
                    "use_category": payload.get("use_category") or "",
                    "next_action": payload.get("next_action") or "",
                    "source_note_item_id": payload.get("source_note_item_id") or "",
                }
            )
            row_count += 1
        blocked_review_count = conn.execute(
            "SELECT COUNT(*) AS count FROM review_queue WHERE status = 'open'"
        ).fetchone()["count"]
        suffix = "_filtered" if query.strip() else ""
        filename = f"genotyping_worklist{suffix}.csv"
        conn.execute(
            """
            INSERT INTO export_log
                (export_id, export_type, filename, query, row_count,
                 blocked_review_count, status, exported_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("export"),
                "genotyping_worklist_csv",
                filename,
                query.strip(),
                row_count,
                blocked_review_count,
                "generated",
                utc_now(),
                "Generated as a companion genotyping worklist export without changing lab workbook shape.",
            ),
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/export-log")
def list_export_log() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT export_id, export_type, filename, query, row_count,
                   blocked_review_count, status, exported_at, source_layer, note
            FROM export_log
            ORDER BY exported_at DESC, rowid DESC
            LIMIT 25
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/export-preview")
def export_preview() -> dict[str, Any]:
    with connection() as conn:
        photos = conn.execute("SELECT COUNT(*) AS count FROM photo_log").fetchone()["count"]
        review_rows = conn.execute(
            """
            SELECT review_id, parse_id, severity, issue, suggested_value, review_reason, created_at
            FROM review_queue
            WHERE status = 'open'
            ORDER BY severity DESC, created_at DESC
            LIMIT 10
            """
        ).fetchall()
        open_reviews = conn.execute(
            "SELECT COUNT(*) AS count FROM review_queue WHERE status = 'open'"
        ).fetchone()["count"]
        parsed = conn.execute("SELECT COUNT(*) AS count FROM parse_result").fetchone()["count"]
        mice = conn.execute(
            f"""
            {MOUSE_SELECT}
            WHERE status IN ('active', 'moved')
            ORDER BY raw_strain_text COLLATE NOCASE, dob_start, display_id COLLATE NOCASE
            LIMIT 50
            """
        ).fetchall()
        mating_rows = conn.execute(
            """
            SELECT m.mating_id, m.mating_label, m.strain_goal, m.expected_genotype,
                   m.start_date, m.status AS mating_status,
                   mm.role, mouse.display_id, mouse.sex, mouse.ear_label_raw,
                   mouse.genotype, mouse.genotype_result, mouse.dob_raw, mouse.dob_start,
                   mouse.source_note_item_id, mouse.source_record_id
            FROM mating_registry m
            LEFT JOIN mating_mouse mm ON mm.mating_id = m.mating_id AND mm.removed_date IS NULL
            LEFT JOIN mouse_master mouse ON mouse.mouse_id = mm.mouse_id
            ORDER BY m.created_at, m.mating_label COLLATE NOCASE,
                     CASE mm.role WHEN 'male' THEN 1 WHEN 'female' THEN 2 ELSE 3 END,
                     mouse.display_id COLLATE NOCASE
            LIMIT 120
            """
        ).fetchall()
        litter_rows = conn.execute(
            """
            SELECT l.litter_id, l.litter_label, l.mating_id, l.birth_date,
                   l.number_born, l.number_alive, l.number_weaned, l.weaning_date,
                   l.status, l.source_record_id
            FROM litter_registry l
            ORDER BY l.birth_date, l.created_at
            LIMIT 120
            """
        ).fetchall()
    rows = []
    separation_groups: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for mouse in mice:
        sex = mouse["sex"] or ""
        sex_symbol = {"male": "♂", "female": "♀"}.get(sex.lower(), sex)
        genotype = mouse["genotype_result"] or mouse["genotype"] or ""
        dob = mouse["dob_raw"] or mouse["dob_start"] or ""
        cage = mouse["current_cage_label"] or ""
        group_key = (cage, mouse["raw_strain_text"] or "", genotype, sex_symbol, dob)
        if group_key not in separation_groups:
            separation_groups[group_key] = {
                "cage_number": cage,
                "strain": mouse["raw_strain_text"] or "",
                "genotype": genotype,
                "sex": sex_symbol,
                "count": 0,
                "dob": dob,
                "wt": "",
                "tg": "",
                "sampling_point": "",
                "source_note_item_ids": [],
                "source_record_ids": [],
            }
        group = separation_groups[group_key]
        group["count"] += 1
        if "wt" in genotype.lower():
            group["wt"] = str(int(group["wt"] or "0") + 1)
        elif "tg" in genotype.lower():
            group["tg"] = str(int(group["tg"] or "0") + 1)
        elif mouse["genotyping_status"] and mouse["genotyping_status"] != "resulted":
            group["wt"] = mouse["genotyping_status"]
        if mouse["next_action"]:
            group["sampling_point"] = mouse["next_action"]
        if mouse["source_note_item_id"]:
            group["source_note_item_ids"].append(mouse["source_note_item_id"])
        if mouse["source_record_id"]:
            group["source_record_ids"].append(mouse["source_record_id"])
        rows.append(
            {
                "mouse_id": mouse["mouse_id"],
                "display_id": mouse["display_id"],
                "strain": mouse["raw_strain_text"] or "",
                "genotype": mouse["genotype_result"] or mouse["genotype"] or "",
                "dob": mouse["dob_raw"] or mouse["dob_start"] or "",
                "ear_label": mouse["ear_label_raw"] or mouse["ear_label_code"] or "",
                "status": mouse["status"],
                "current_cage": mouse["current_cage_label"] or "",
                "next_action": mouse["next_action"],
                "source_note_item_id": mouse["source_note_item_id"] or "",
            }
        )
    separation_rows = []
    for group in separation_groups.values():
        source_notes = ", ".join(group["source_note_item_ids"][:3])
        if len(group["source_note_item_ids"]) > 3:
            source_notes = f"{source_notes}, +{len(group['source_note_item_ids']) - 3}"
        separation_rows.append(
            {
                "cage_number": group["cage_number"],
                "strain": group["strain"],
                "genotype": group["genotype"],
                "total": f"{group['sex']} {group['count']}p".strip(),
                "dob": group["dob"],
                "wt": group["wt"],
                "tg": group["tg"],
                "sampling_point": group["sampling_point"],
                "source_note_item_ids": source_notes,
            }
        )
    litter_by_mating: dict[str, list[Any]] = {}
    for litter in litter_rows:
        litter_by_mating.setdefault(litter["mating_id"], []).append(litter)
    animal_rows = []
    current_mating = None
    cage_no = 0
    litter_sequence: dict[str, int] = {}
    for mating in mating_rows:
        if mating["mating_id"] != current_mating:
            current_mating = mating["mating_id"]
            cage_no += 1
            litter_sequence[current_mating] = 0
            first_parent_for_mating = True
        else:
            first_parent_for_mating = False
        if mating["display_id"]:
            sex_value = {"male": "♂", "female": "♀"}.get((mating["sex"] or "").lower(), mating["sex"] or mating["role"] or "")
            mouse_label = " ".join([mating["display_id"] or "", mating["ear_label_raw"] or ""]).strip()
            animal_rows.append(
                {
                    "cage_no": str(cage_no) if first_parent_for_mating else "",
                    "strain": mating["strain_goal"] or "",
                    "sex": sex_value,
                    "mouse_id": mouse_label,
                    "genotype": mating["genotype_result"] or mating["genotype"] or mating["expected_genotype"] or "",
                    "dob": mating["dob_raw"] or mating["dob_start"] or "",
                    "mating_date": mating["start_date"] if first_parent_for_mating else "",
                    "pubs": "",
                    "status": mating["mating_status"] or "",
                    "source": mating["source_note_item_id"] or mating["source_record_id"] or "",
                }
            )
        for litter in litter_by_mating.get(current_mating, []):
            if litter_sequence[current_mating] >= litter_by_mating[current_mating].index(litter) + 1:
                continue
            litter_sequence[current_mating] += 1
            born_count = litter["number_alive"] if litter["number_alive"] is not None else litter["number_born"]
            animal_rows.append(
                {
                    "cage_no": "",
                    "strain": "",
                    "sex": f"F{litter_sequence[current_mating]}",
                    "mouse_id": f"{born_count or ''}p".strip(),
                    "genotype": litter["status"] or "",
                    "dob": litter["birth_date"] or "",
                    "mating_date": "",
                    "pubs": f"{litter['birth_date']} {litter['number_born']}p".strip() if litter["number_born"] else "",
                    "status": litter["status"] or "",
                    "source": litter["source_record_id"] or "",
                }
            )
    return {
        "source_layer": "export or view",
        "export_type": "separation_preview",
        "expected_filename": "mouse_records_preview.csv",
        "separation_columns": ["Cage number", "Strain", "Genotype", "total", "DOB", "WT", "Tg", "Sampling point", "Source note"],
        "animal_sheet_columns": ["Cage No.", "Strain", "Sex", "I.D", "genotype", "DOB", "Mating date", "Pubs", "Status", "Source"],
        "photos": photos,
        "parsed_results": parsed,
        "blocked_review_items": open_reviews,
        "ready": open_reviews == 0 and bool(rows),
        "preview_rows": rows,
        "separation_rows": separation_rows,
        "animal_sheet_rows": animal_rows,
        "preview_row_count": len(rows),
        "separation_row_count": len(separation_rows),
        "animal_sheet_row_count": len(animal_rows),
        "review_blockers": [dict(row) for row in review_rows],
        "generated_at": utc_now(),
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
