from __future__ import annotations

import json
import re
import hashlib
import csv
import io
import html
import zipfile
import mimetypes
import base64
import os
from urllib.parse import quote
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import httpx

from .db import ROOT, connection, init_db
from .storage import new_id, save_legacy_workbook, save_upload, utc_now
from scripts.parse_legacy_workbooks import parse_workbook


STATIC_DIR = ROOT / "static"
FIXTURE_PATH = ROOT / "fixtures" / "sample_parse_results.json"
RUNTIME_OPENAI_API_KEY = ""


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
    legacy_decision: str = "resolve"
    canonical_entity_type: str = ""
    canonical_entity_id: str = ""
    correction_entity_type: str = ""
    correction_entity_id: str = ""
    correction_field_name: str = ""
    correction_before_value: str = ""
    correction_after_value: str = ""
    correction_source_record_id: str | None = None
    note_item_id: str = ""
    note_label_decision: str = ""
    note_label_mouse_id: str = ""
    note_label_count: int | None = Field(default=None, ge=0)
    note_label_interpreted_status: str = ""


class PhotoManualTranscriptionCreate(BaseModel):
    card_type: str = "Separated"
    raw_strain: str = ""
    matched_strain: str = ""
    sex_raw: str = ""
    id_raw: str = ""
    dob_raw: str = ""
    dob_normalized: str = ""
    mating_date_raw: str = ""
    mating_date_normalized: str = ""
    lmo_raw: str = ""
    mouse_count: str = ""
    confidence: float = Field(default=75, ge=0, le=100)
    notes: list[dict[str, Any]] = Field(default_factory=list)
    reviewer_note: str = ""
    extraction_method: str = "manual_entry"


class PhotoAiDraftCreate(BaseModel):
    approved_external_inference: bool = False
    detail: str = "low"


class AiDraftSettingsUpdate(BaseModel):
    api_key: str = ""


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


def current_openai_api_key() -> str:
    return RUNTIME_OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")


def ai_draft_status() -> dict[str, Any]:
    key_source = "session" if RUNTIME_OPENAI_API_KEY else ("environment" if os.environ.get("OPENAI_API_KEY") else "missing")
    return {
        "available": bool(current_openai_api_key()),
        "key_source": key_source,
        "model": os.environ.get("OPENAI_PARSE_ASSIST_MODEL", "gpt-4.1-mini"),
        "approval_required": True,
        "payload_minimization": "selected photo plus active assigned strain names only",
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "storage": "local-only",
        "ai_draft": ai_draft_status(),
    }


@app.post("/api/ai-draft-settings")
def update_ai_draft_settings(payload: AiDraftSettingsUpdate) -> dict[str, Any]:
    global RUNTIME_OPENAI_API_KEY
    RUNTIME_OPENAI_API_KEY = payload.api_key.strip()
    return {
        "status": "updated",
        "stored": "server_session_only" if RUNTIME_OPENAI_API_KEY else "cleared",
        "ai_draft": ai_draft_status(),
    }


@app.get("/api/photos")
def list_photos() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT photo.photo_id, photo.original_filename, photo.stored_path,
                   photo.uploaded_at, photo.status, photo.raw_source_kind,
                   COALESCE(review_counts.open_reviews, 0) AS open_review_count,
                   review_counts.latest_parse_id
            FROM photo_log photo
            LEFT JOIN (
                SELECT parse.photo_id, COUNT(review.review_id) AS open_reviews,
                       MAX(parse.parse_id) AS latest_parse_id
                FROM parse_result parse
                LEFT JOIN review_queue review
                    ON review.parse_id = parse.parse_id AND review.status = 'open'
                GROUP BY parse.photo_id
            ) review_counts ON review_counts.photo_id = photo.photo_id
            ORDER BY uploaded_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/photos/{photo_id}/image")
def get_photo_image(photo_id: str) -> FileResponse:
    photo, image_path, media_type = photo_image_path(photo_id)
    filename = photo["original_filename"] or image_path.name
    return FileResponse(image_path, media_type=media_type, filename=filename)


def photo_image_path(photo_id: str) -> tuple[Any, Path, str]:
    with connection() as conn:
        photo = conn.execute(
            """
            SELECT photo_id, original_filename, stored_path, uploaded_at, status
            FROM photo_log
            WHERE photo_id = ?
            """,
            (photo_id,),
        ).fetchone()
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found.")

    stored_path = str(photo["stored_path"] or "")
    image_path = (ROOT / stored_path).resolve()
    photo_root = (ROOT / "data" / "photos").resolve()
    if photo_root != image_path and photo_root not in image_path.parents:
        raise HTTPException(status_code=400, detail="Stored photo path is outside the photo evidence directory.")
    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="Stored photo file is missing.")

    filename = photo["original_filename"] or image_path.name
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return photo, image_path, media_type


def assigned_strain_scope_for_prompt() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT display_name, aliases_json
            FROM my_assigned_strain
            WHERE active = 1
            ORDER BY display_name COLLATE NOCASE
            LIMIT 25
            """
        ).fetchall()
    return [
        {
            "display_name": row["display_name"],
            "aliases": json.loads(row["aliases_json"] or "[]"),
        }
        for row in rows
    ]


def bounded_float(value: Any, *, minimum: float = 0, maximum: float = 100) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum
    return max(minimum, min(maximum, number))


def ai_draft_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "card_type": {"type": "string", "enum": ["Separated", "Mating", "unknown"]},
            "raw_strain": {"type": "string"},
            "matched_strain": {"type": "string"},
            "sex_raw": {"type": "string"},
            "id_raw": {"type": "string"},
            "dob_raw": {"type": "string"},
            "dob_normalized": {"type": "string"},
            "mating_date_raw": {"type": "string"},
            "mating_date_normalized": {"type": "string"},
            "lmo_raw": {"type": "string"},
            "mouse_count": {"type": "string"},
            "notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "raw": {"type": "string"},
                        "meaning": {"type": "string"},
                        "strike": {"type": "string", "enum": ["none", "single", "double", "unclear"]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["raw", "meaning", "strike", "confidence"],
                },
            },
            "confidence": {"type": "number"},
            "uncertain_fields": {"type": "array", "items": {"type": "string"}},
            "reviewer_note": {"type": "string"},
        },
        "required": [
            "card_type",
            "raw_strain",
            "matched_strain",
            "sex_raw",
            "id_raw",
            "dob_raw",
            "dob_normalized",
            "mating_date_raw",
            "mating_date_normalized",
            "lmo_raw",
            "mouse_count",
            "notes",
            "confidence",
            "uncertain_fields",
            "reviewer_note",
        ],
    }


def normalize_ai_draft_payload(value: Any) -> dict[str, Any]:
    draft = value if isinstance(value, dict) else {}
    notes = draft.get("notes") if isinstance(draft.get("notes"), list) else []
    normalized_notes = []
    for note in notes[:25]:
        if not isinstance(note, dict):
            continue
        raw = str(note.get("raw") or "").strip()
        if not raw:
            continue
        strike = str(note.get("strike") or "unclear")
        if strike not in {"none", "single", "double", "unclear"}:
            strike = "unclear"
        normalized_notes.append(
            {
                "raw": raw,
                "meaning": str(note.get("meaning") or ""),
                "strike": strike,
                "confidence": bounded_float(note.get("confidence")),
            }
        )
    card_type = str(draft.get("card_type") or "unknown")
    if card_type not in {"Separated", "Mating", "unknown"}:
        card_type = "unknown"
    return {
        "card_type": card_type,
        "raw_strain": str(draft.get("raw_strain") or ""),
        "matched_strain": str(draft.get("matched_strain") or ""),
        "sex_raw": str(draft.get("sex_raw") or ""),
        "id_raw": str(draft.get("id_raw") or ""),
        "dob_raw": str(draft.get("dob_raw") or ""),
        "dob_normalized": str(draft.get("dob_normalized") or ""),
        "mating_date_raw": str(draft.get("mating_date_raw") or ""),
        "mating_date_normalized": str(draft.get("mating_date_normalized") or ""),
        "lmo_raw": str(draft.get("lmo_raw") or ""),
        "mouse_count": str(draft.get("mouse_count") or ""),
        "notes": normalized_notes,
        "confidence": bounded_float(draft.get("confidence")),
        "uncertain_fields": [
            str(item)
            for item in (draft.get("uncertain_fields") if isinstance(draft.get("uncertain_fields"), list) else [])
            if str(item).strip()
        ],
        "reviewer_note": str(draft.get("reviewer_note") or ""),
    }


def request_ai_transcription_draft(photo_id: str, payload: PhotoAiDraftCreate) -> dict[str, Any]:
    if not payload.approved_external_inference:
        raise HTTPException(
            status_code=403,
            detail="External AI draft transcription requires explicit per-request approval.",
        )
    api_key = current_openai_api_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured; AI draft transcription is unavailable.",
        )
    if payload.detail not in {"low", "high", "auto"}:
        raise HTTPException(status_code=400, detail="Image detail must be low, high, or auto.")

    photo, image_path, media_type = photo_image_path(photo_id)
    if not media_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="AI draft transcription requires an image source photo.")
    image_bytes = image_path.read_bytes()
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Photo is too large for AI draft transcription.")

    data_url = f"data:{media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    assigned_scope = assigned_strain_scope_for_prompt()
    request_payload = {
        "model": os.environ.get("OPENAI_PARSE_ASSIST_MODEL", "gpt-4.1-mini"),
        "store": False,
        "instructions": (
            "You draft cage-card transcription fields for review. "
            "Never invent hidden text. Preserve visible raw text. "
            "Use unknown/empty values when uncertain. "
            "Classify all output as draft parsed evidence, not canonical state."
        ),
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Read this mouse cage card photo. Return only JSON matching the schema. "
                            "Fields: card_type, raw_strain, matched_strain, sex_raw, id_raw, dob_raw, "
                            "dob_normalized, mating_date_raw, mating_date_normalized, lmo_raw, mouse_count, "
                            "notes. sex_raw is the visible Sex field and may "
                            "include symbols such as male/female marks, mixed, or unclear handwriting. id_raw "
                            "is the visible I.D field, not the internal database id. lmo_raw preserves visible "
                            "LMO/O/N or similar checkbox marks without interpretation. Notes should preserve each "
                            "visible mouse ID, date/event line, or numeric-only temporary label line. "
                            "For numeric-only post-separation labels, keep the raw numbers as notes and mark "
                            "meaning as unlabeled_numeric_note rather than inventing mouse IDs. "
                            "Strike marks: none, single, double, unclear. "
                            f"Assigned strain scope for matching only: {json.dumps(assigned_scope, ensure_ascii=False)}"
                        ),
                    },
                    {"type": "input_image", "image_url": data_url, "detail": payload.detail},
                ],
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "cage_card_transcription_draft",
                "strict": True,
                "schema": ai_draft_schema(),
            }
        },
    }
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
            )
        response.raise_for_status()
        response_payload = response.json()
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=f"AI draft transcription request failed: {error.response.text[:500]}",
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"AI draft transcription request failed: {error}") from error

    output_text = str(response_payload.get("output_text") or "")
    if not output_text:
        for item in response_payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    output_text += str(content.get("text") or "")
    try:
        draft = normalize_ai_draft_payload(json.loads(output_text))
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=502, detail="AI draft transcription returned invalid JSON.") from error

    return {
        "boundary": "parsed or intermediate result",
        "source_layer": "parsed or intermediate result",
        "photo_id": photo_id,
        "photo_filename": photo["original_filename"],
        "external_inference_used": True,
        "payload_minimization": "Selected source photo only; active assigned strain names/aliases only; no colony records or Excel rows sent.",
        "stored": False,
        "draft": draft,
    }


@app.post("/api/photos/{photo_id}/ai-transcription-draft")
def create_photo_ai_transcription_draft(photo_id: str, payload: PhotoAiDraftCreate) -> dict[str, Any]:
    return request_ai_transcription_draft(photo_id, payload)


@app.post("/api/photos/{photo_id}/ai-extract-transcription")
def create_photo_ai_extracted_transcription(photo_id: str, payload: PhotoAiDraftCreate) -> dict[str, Any]:
    extraction = request_ai_transcription_draft(photo_id, payload)
    draft = extraction["draft"]
    transcription = create_photo_manual_transcription(
        photo_id,
        PhotoManualTranscriptionCreate(
            card_type=draft["card_type"],
            raw_strain=draft["raw_strain"],
            matched_strain=draft["matched_strain"],
            sex_raw=draft["sex_raw"],
            id_raw=draft["id_raw"],
            dob_raw=draft["dob_raw"],
            dob_normalized=draft["dob_normalized"],
            mating_date_raw=draft["mating_date_raw"],
            mating_date_normalized=draft["mating_date_normalized"],
            lmo_raw=draft["lmo_raw"],
            mouse_count=draft["mouse_count"],
            confidence=draft["confidence"],
            notes=draft["notes"],
            reviewer_note=(
                "AI-extracted cage-card draft. Reviewer must compare against the raw photo before canonical writes. "
                f"Uncertain fields: {', '.join(draft['uncertain_fields']) or 'none listed'}."
            ),
            extraction_method="ai_photo_extraction",
        ),
    )
    return {
        **transcription,
        "extraction_method": "ai_photo_extraction",
        "external_inference_used": True,
        "payload_minimization": extraction["payload_minimization"],
        "draft_confidence": draft["confidence"],
        "uncertain_fields": draft["uncertain_fields"],
    }


@app.get("/api/photo-review-workbench")
def photo_review_workbench() -> dict[str, Any]:
    with connection() as conn:
        photos = conn.execute(
            """
            SELECT photo_id, original_filename, uploaded_at, status, raw_source_kind
            FROM photo_log
            ORDER BY uploaded_at DESC
            """
        ).fetchall()
        rows = []
        for photo in photos:
            manual = conn.execute(
                """
                SELECT parse_id, parsed_at, status
                FROM parse_result
                WHERE photo_id = ?
                  AND source_name IN ('manual_photo_transcription', 'ai_photo_extraction')
                ORDER BY parsed_at DESC
                LIMIT 1
                """,
                (photo["photo_id"],),
            ).fetchone()
            manual_parse_id = manual["parse_id"] if manual is not None else ""
            note_counts = {"note_lines": 0, "mouse_note_lines": 0}
            if manual_parse_id:
                note_row = conn.execute(
                    """
                    SELECT COUNT(*) AS note_lines,
                           SUM(CASE WHEN parsed_type = 'mouse_item' THEN 1 ELSE 0 END) AS mouse_note_lines
                    FROM card_note_item_log
                    WHERE parse_id = ?
                    """,
                    (manual_parse_id,),
                ).fetchone()
                note_counts = {
                    "note_lines": int(note_row["note_lines"] or 0),
                    "mouse_note_lines": int(note_row["mouse_note_lines"] or 0),
                }
            review_counts = conn.execute(
                """
                SELECT COUNT(*) AS total_reviews,
                       SUM(CASE WHEN review.status = 'open' THEN 1 ELSE 0 END) AS open_reviews
                FROM parse_result parse
                JOIN review_queue review ON review.parse_id = parse.parse_id
                WHERE parse.photo_id = ?
                """,
                (photo["photo_id"],),
            ).fetchone()
            comparison_counts = {"comparison_reviews": 0, "open_comparison_reviews": 0, "resolved_comparison_reviews": 0}
            if manual_parse_id:
                comparison_row = conn.execute(
                    """
                    SELECT COUNT(*) AS comparison_reviews,
                           SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_comparison_reviews,
                           SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) AS resolved_comparison_reviews
                    FROM review_queue
                    WHERE parse_id = ?
                      AND issue LIKE 'Photo transcription%'
                    """,
                    (manual_parse_id,),
                ).fetchone()
                comparison_counts = {
                    "comparison_reviews": int(comparison_row["comparison_reviews"] or 0),
                    "open_comparison_reviews": int(comparison_row["open_comparison_reviews"] or 0),
                    "resolved_comparison_reviews": int(comparison_row["resolved_comparison_reviews"] or 0),
                }
            open_reviews = int(review_counts["open_reviews"] or 0)
            if not manual_parse_id:
                next_action = "transcribe_photo"
            elif open_reviews:
                next_action = "resolve_photo_reviews"
            elif comparison_counts["comparison_reviews"] == 0:
                next_action = "create_comparison_review"
            elif comparison_counts["open_comparison_reviews"]:
                next_action = "resolve_evidence_comparison"
            else:
                next_action = "ready_for_candidate_mapping"
            rows.append(
                {
                    "source_layer": "export or view",
                    "photo_id": photo["photo_id"],
                    "original_filename": photo["original_filename"],
                    "uploaded_at": photo["uploaded_at"],
                    "status": photo["status"],
                    "raw_source_kind": photo["raw_source_kind"],
                    "image_url": f"/api/photos/{quote(photo['photo_id'])}/image",
                    "manual_parse_id": manual_parse_id,
                    "manual_transcribed_at": manual["parsed_at"] if manual is not None else "",
                    "note_line_count": note_counts["note_lines"],
                    "mouse_note_line_count": note_counts["mouse_note_lines"],
                    "total_review_count": int(review_counts["total_reviews"] or 0),
                    "open_review_count": open_reviews,
                    **comparison_counts,
                    "next_action": next_action,
                }
            )
    return {
        "boundary": "export or view",
        "source_priority": ["raw source photo", "manual transcription", "review item", "canonical candidate"],
        "photo_count": len(rows),
        "pending_transcription_count": sum(1 for row in rows if row["next_action"] == "transcribe_photo"),
        "open_review_count": sum(row["open_review_count"] for row in rows),
        "rows": rows,
    }


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


def ensure_photo_review_candidate(
    conn: Any,
    *,
    photo_id: str,
    original_filename: str,
    stored_path: str,
    uploaded_at: str,
    source_record_id: str = "",
) -> dict[str, Any]:
    existing = conn.execute(
        """
        SELECT parse.parse_id, review.review_id
        FROM parse_result parse
        LEFT JOIN review_queue review ON review.parse_id = parse.parse_id
        WHERE parse.photo_id = ? AND parse.source_name = ?
        ORDER BY parse.parsed_at DESC
        LIMIT 1
        """,
        (photo_id, "photo_manual_review"),
    ).fetchone()
    if existing is not None:
        return {
            "parse_id": existing["parse_id"],
            "review_id": existing["review_id"],
            "created": False,
        }

    parse_id = new_id("parse")
    review_id = new_id("review")
    now = utc_now()
    raw_payload = {
        "layer": "review item",
        "source_layer": "raw source",
        "source_type": "cage_card_photo",
        "photo_id": photo_id,
        "source_record_id": source_record_id,
        "original_filename": original_filename,
        "stored_path": stored_path,
        "uploaded_at": uploaded_at,
        "external_processing": "none",
        "extraction_status": "not_attempted",
        "note": "Create a manual card transcription before accepting this latest photo into canonical state.",
    }
    conn.execute(
        """
        INSERT INTO parse_result
            (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            parse_id,
            photo_id,
            "photo_manual_review",
            json.dumps(raw_payload, ensure_ascii=False),
            now,
            "review",
            0,
            1,
        ),
    )
    conn.execute(
        """
        INSERT INTO review_queue
            (review_id, parse_id, severity, issue, current_value, suggested_value,
             review_reason, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            review_id,
            parse_id,
            "Medium",
            "Photo requires manual cage-card transcription",
            original_filename,
            "Review visible strain, sex, IDs, DOB, mating date, notes, and strike marks before accepting.",
            "Latest cage-card photo is raw evidence and may supersede predecessor Excel views. No OCR or inference has been accepted.",
            "open",
            now,
        ),
    )
    conn.execute("UPDATE photo_log SET status = ? WHERE photo_id = ?", ("review_pending", photo_id))
    conn.execute(
        """
        INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("action"),
            "photo_review_candidate_created",
            photo_id,
            None,
            json.dumps({"parse_id": parse_id, "review_id": review_id}, ensure_ascii=False),
            now,
        ),
    )
    return {"parse_id": parse_id, "review_id": review_id, "created": True}


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


def record_correction(conn: Any, payload: CorrectionCreate, corrected_at: str) -> str:
    correction_id = new_id("correction")
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
    return correction_id


def create_canonical_candidate_draft(
    conn: Any,
    *,
    review_id: str,
    parse_id: str,
    created_at: str,
) -> str | None:
    existing = conn.execute(
        """
        SELECT candidate_id
        FROM canonical_candidate
        WHERE review_id = ?
        """,
        (review_id,),
    ).fetchone()
    if existing is not None:
        return existing["candidate_id"]

    review = conn.execute(
        """
        SELECT review_id, current_value, suggested_value, review_reason
        FROM review_queue
        WHERE review_id = ?
        """,
        (review_id,),
    ).fetchone()
    if review is None:
        return None

    current_value = json_object(review["current_value"])
    suggested_value = json_object(review["suggested_value"])
    manual = current_value.get("manual") if isinstance(current_value.get("manual"), dict) else current_value
    legacy = current_value.get("legacy") if isinstance(current_value.get("legacy"), dict) else suggested_value
    legacy_summary = legacy.get("summary") if isinstance(legacy.get("summary"), dict) else {}
    proposed = {
        "display_id": manual.get("display_id") or legacy_summary.get("display_id") or "",
        "strain": manual.get("strain") or legacy_summary.get("strain") or "",
        "sex": manual.get("sex") or legacy_summary.get("sex") or "",
        "card_id_raw": manual.get("id") or legacy_summary.get("display_id") or "",
        "dob": manual.get("dob") or legacy_summary.get("dob") or "",
        "count": manual.get("count_raw") or manual.get("count") or legacy_summary.get("count_raw") or legacy_summary.get("count") or "",
        "manual": manual,
        "legacy": legacy,
        "review_reason": review["review_reason"],
        "boundary": "review item",
        "note": "Draft only. Does not write mouse_master or other canonical colony tables.",
    }
    candidate_id = new_id("candidate")
    conn.execute(
        """
        INSERT INTO canonical_candidate
            (candidate_id, review_id, parse_id, legacy_row_id, proposed_mouse_display_id,
             proposed_strain, proposed_dob, proposed_count, candidate_payload, status,
             created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate_id,
            review_id,
            parse_id,
            str(legacy.get("legacy_row_id") or ""),
            str(proposed["display_id"] or ""),
            str(proposed["strain"] or ""),
            str(proposed["dob"] or ""),
            str(proposed["count"] or ""),
            json.dumps(proposed, ensure_ascii=False),
            "draft",
            created_at,
            created_at,
        ),
    )
    conn.execute(
        """
        INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("action"),
            "canonical_candidate_draft_created",
            candidate_id,
            None,
            json.dumps({"review_id": review_id, "parse_id": parse_id, "boundary": "review item"}, ensure_ascii=False),
            created_at,
        ),
    )
    return candidate_id


def review_note_item_id(review_id: str, payload_note_item_id: str = "") -> str:
    if payload_note_item_id.strip():
        return payload_note_item_id.strip()
    for prefix in ("review_unlabeled_numeric_", "review_ear_"):
        if review_id.startswith(prefix):
            return review_id[len(prefix) :]
    return ""


def resolve_note_label_correction(
    conn: Any,
    *,
    review_id: str,
    parse_id: str,
    payload: ReviewResolutionCreate,
    resolved_at: str,
) -> dict[str, Any] | None:
    decision = payload.note_label_decision.strip()
    if not decision:
        return None
    allowed_decisions = {"mouse_item", "count_note", "reviewed_note", "ignored_note"}
    if decision not in allowed_decisions:
        raise HTTPException(
            status_code=400,
            detail="note_label_decision must be mouse_item, count_note, reviewed_note, or ignored_note.",
        )

    note_item_id = review_note_item_id(review_id, payload.note_item_id)
    if not note_item_id:
        raise HTTPException(status_code=400, detail="note_item_id is required for note label review corrections.")
    note = conn.execute(
        """
        SELECT note_item_id, photo_id, parse_id, card_snapshot_id, card_type, line_number, raw_line_text, strike_status,
               parsed_type, interpreted_status, parsed_mouse_display_id,
               parsed_ear_label_raw, parsed_ear_label_code, parsed_ear_label_confidence,
               parsed_ear_label_review_status, parsed_event_date, parsed_count,
               confidence, needs_review
        FROM card_note_item_log
        WHERE note_item_id = ?
        """,
        (note_item_id,),
    ).fetchone()
    if note is None:
        raise HTTPException(status_code=404, detail="Note item not found for label review correction.")
    if note["parse_id"] != parse_id:
        raise HTTPException(status_code=409, detail="Review item and note item parse IDs do not match.")

    before = dict(note)
    after = dict(before)
    after.update(
        {
            "parsed_type": decision,
            "interpreted_status": payload.note_label_interpreted_status.strip() or decision,
            "parsed_mouse_display_id": None,
            "parsed_ear_label_raw": None,
            "parsed_ear_label_code": None,
            "parsed_ear_label_confidence": None,
            "parsed_ear_label_review_status": "user_corrected",
            "parsed_event_date": None,
            "parsed_count": None,
            "confidence": 1.0,
            "needs_review": 0,
        }
    )
    if decision == "mouse_item":
        display_id = (payload.note_label_mouse_id or payload.resolved_value).strip()
        if not display_id:
            raise HTTPException(status_code=400, detail="note_label_mouse_id is required when decision is mouse_item.")
        after["parsed_mouse_display_id"] = display_id
        after["interpreted_status"] = payload.note_label_interpreted_status.strip() or interpreted_status(
            note["card_type"],
            note["strike_status"],
        )
    elif decision == "count_note":
        count_value = payload.note_label_count
        if count_value is None:
            match = re.search(r"\d+", payload.resolved_value or note["raw_line_text"] or "")
            if match:
                count_value = int(match.group(0))
        if count_value is None:
            raise HTTPException(status_code=400, detail="note_label_count is required when decision is count_note.")
        after["parsed_count"] = count_value
        after["interpreted_status"] = payload.note_label_interpreted_status.strip() or "reviewed_count"
    elif decision == "reviewed_note":
        after["interpreted_status"] = payload.note_label_interpreted_status.strip() or "reviewed_note"
    elif decision == "ignored_note":
        after["interpreted_status"] = payload.note_label_interpreted_status.strip() or "ignored"

    conn.execute(
        """
        UPDATE card_note_item_log
        SET parsed_type = ?,
            interpreted_status = ?,
            parsed_mouse_display_id = ?,
            parsed_ear_label_raw = ?,
            parsed_ear_label_code = ?,
            parsed_ear_label_confidence = ?,
            parsed_ear_label_review_status = ?,
            parsed_event_date = ?,
            parsed_count = ?,
            confidence = ?,
            needs_review = ?
        WHERE note_item_id = ?
        """,
        (
            after["parsed_type"],
            after["interpreted_status"],
            after["parsed_mouse_display_id"],
            after["parsed_ear_label_raw"],
            after["parsed_ear_label_code"],
            after["parsed_ear_label_confidence"],
            after["parsed_ear_label_review_status"],
            after["parsed_event_date"],
            after["parsed_count"],
            after["confidence"],
            after["needs_review"],
            note_item_id,
        ),
    )
    correction_id = record_correction(
        conn,
        CorrectionCreate(
            entity_type="note_item",
            entity_id=note_item_id,
            field_name="parsed_label",
            before_value=json.dumps(before, ensure_ascii=False),
            after_value=json.dumps(after, ensure_ascii=False),
            reason=payload.resolution_note,
            review_id=review_id,
        ),
        resolved_at,
    )
    conn.execute(
        """
        INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("action"),
            "note_label_reviewed",
            note_item_id,
            json.dumps(before, ensure_ascii=False),
            json.dumps(
                {
                    "review_id": review_id,
                    "decision": decision,
                    "after": after,
                    "boundary": "parsed or intermediate result",
                },
                ensure_ascii=False,
            ),
            resolved_at,
        ),
    )
    snapshot_update = refresh_card_snapshot_summary(conn, str(note["card_snapshot_id"] or ""), resolved_at)
    return {
        "note_item_id": note_item_id,
        "decision": decision,
        "correction_id": correction_id,
        "card_snapshot_update": snapshot_update,
        "boundary": "parsed or intermediate result",
    }


@app.post("/api/corrections")
def create_correction(payload: CorrectionCreate) -> dict[str, Any]:
    corrected_at = utc_now()
    with connection() as conn:
        correction_id = record_correction(conn, payload, corrected_at)

    return {"correction_id": correction_id, "corrected_at": corrected_at}


@app.get("/api/canonical-candidates")
def list_canonical_candidates() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT candidate_id, review_id, parse_id, legacy_row_id,
                   proposed_mouse_display_id, proposed_strain, proposed_dob,
                   proposed_count, candidate_payload, status, created_at, updated_at
            FROM canonical_candidate
            ORDER BY created_at DESC
            """
        ).fetchall()
    result = []
    for row in rows:
        payload = dict(row)
        payload["candidate_payload"] = json_object(payload.get("candidate_payload"))
        payload["boundary"] = "review item"
        payload["source_layer"] = "review item"
        result.append(payload)
    return result


def canonical_candidate_apply_preview(conn: Any, candidate_id: str) -> dict[str, Any]:
    candidate = conn.execute(
        """
        SELECT candidate.candidate_id, candidate.review_id, candidate.parse_id,
               candidate.legacy_row_id, candidate.proposed_strain,
               candidate.proposed_dob, candidate.candidate_payload,
               candidate.status, review.status AS review_status
        FROM canonical_candidate candidate
        JOIN review_queue review ON review.review_id = candidate.review_id
        WHERE candidate.candidate_id = ?
        """,
        (candidate_id,),
    ).fetchone()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Canonical candidate draft not found.")

    payload = json_object(candidate["candidate_payload"])
    raw_strain_text = str(candidate["proposed_strain"] or payload.get("strain") or "")
    dob_raw = str(candidate["proposed_dob"] or payload.get("dob") or "")
    dob_raw, dob_start, dob_end = split_dob_range(dob_raw, dob_raw)
    note_rows = conn.execute(
        """
        SELECT note_item_id, photo_id, line_number, raw_line_text, interpreted_status,
               parsed_mouse_display_id, parsed_ear_label_raw, parsed_ear_label_code,
               parsed_ear_label_confidence, parsed_ear_label_review_status
        FROM card_note_item_log
        WHERE parse_id = ?
          AND parsed_type = 'mouse_item'
          AND parsed_mouse_display_id IS NOT NULL
          AND parsed_mouse_display_id != ''
        ORDER BY line_number
        """,
        (candidate["parse_id"],),
    ).fetchall()
    proposed_mice = []
    duplicate_risks = []
    for note in note_rows:
        display_id = str(note["parsed_mouse_display_id"])
        mouse_id = f"mouse_{display_id}_{candidate['parse_id']}".replace(" ", "_")
        existing = conn.execute(
            "SELECT mouse_id FROM mouse_master WHERE mouse_id = ?",
            (mouse_id,),
        ).fetchone()
        duplicate = conn.execute(
            """
            SELECT mouse_id, source_note_item_id
            FROM mouse_master
            WHERE display_id = ?
              AND mouse_id != ?
              AND status IN ('active', 'mating', 'pre_weaning', 'weaning_pending')
            LIMIT 1
            """,
            (display_id, mouse_id),
        ).fetchone()
        if duplicate is not None:
            duplicate_risks.append(
                {
                    "display_id": display_id,
                    "candidate_mouse_id": mouse_id,
                    "existing_mouse_id": duplicate["mouse_id"],
                    "existing_source_note_item_id": duplicate["source_note_item_id"],
                    "source_note_item_id": note["note_item_id"],
                }
            )
        proposed_mice.append(
            {
                "mouse_id": mouse_id,
                "display_id": display_id,
                "raw_strain_text": raw_strain_text,
                "dob_raw": dob_raw,
                "dob_start": dob_start,
                "dob_end": dob_end,
                "status": note["interpreted_status"] or "active",
                "source_note_item_id": note["note_item_id"],
                "source_photo_id": note["photo_id"],
                "raw_line_text": note["raw_line_text"],
                "will_create_mouse": existing is None,
                "existing_mouse_id": existing["mouse_id"] if existing is not None else "",
                "will_create_event": True,
            }
        )
    blockers = []
    if candidate["status"] != "draft":
        blockers.append(f"Candidate status is {candidate['status']}, not draft.")
    if candidate["review_status"] != "resolved":
        blockers.append("Candidate review is not resolved.")
    if not note_rows:
        blockers.append("Candidate has no parsed mouse note lines to apply.")
    if duplicate_risks:
        blockers.append("Active duplicate display IDs must be resolved before applying.")
    return {
        "boundary": "export or view",
        "candidate_id": candidate_id,
        "candidate_status": candidate["status"],
        "review_id": candidate["review_id"],
        "review_status": candidate["review_status"],
        "parse_id": candidate["parse_id"],
        "legacy_row_id": candidate["legacy_row_id"],
        "proposed_mice": proposed_mice,
        "duplicate_risks": duplicate_risks,
        "blocked": bool(blockers),
        "blockers": blockers,
        "summary": {
            "mouse_rows": len(proposed_mice),
            "new_mouse_rows": sum(1 for item in proposed_mice if item["will_create_mouse"]),
            "existing_mouse_rows": sum(1 for item in proposed_mice if not item["will_create_mouse"]),
            "events": len(proposed_mice),
            "duplicate_risks": len(duplicate_risks),
        },
    }


def canonical_candidate_audit_view(conn: Any, candidate_id: str) -> dict[str, Any]:
    candidate = conn.execute(
        """
        SELECT candidate.candidate_id, candidate.review_id, candidate.parse_id,
               candidate.legacy_row_id, candidate.proposed_mouse_display_id,
               candidate.proposed_strain, candidate.proposed_dob,
               candidate.proposed_count, candidate.candidate_payload,
               candidate.status, candidate.created_at, candidate.updated_at,
               review.status AS review_status
        FROM canonical_candidate candidate
        JOIN review_queue review ON review.review_id = candidate.review_id
        WHERE candidate.candidate_id = ?
        """,
        (candidate_id,),
    ).fetchone()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Canonical candidate not found.")

    event_rows = conn.execute(
        """
        SELECT event_id, mouse_id, event_type, event_date,
               related_entity_type, related_entity_id, source_record_id,
               details, created_by, created_at
        FROM mouse_event
        WHERE related_entity_type = 'canonical_candidate'
          AND related_entity_id = ?
        ORDER BY created_at, event_id
        """,
        (candidate_id,),
    ).fetchall()
    events = []
    applied_mouse_ids: list[str] = []
    for event in event_rows:
        payload = dict(event)
        payload["details"] = json_object(payload.get("details"))
        if payload["event_type"] == "canonical_candidate_applied":
            applied_mouse_ids.append(payload["mouse_id"])
        events.append(payload)

    unique_mouse_ids = list(dict.fromkeys(applied_mouse_ids))
    mice = []
    if unique_mouse_ids:
        placeholders = ",".join("?" for _ in unique_mouse_ids)
        mouse_rows = conn.execute(
            f"""
            SELECT mouse_id, display_id, raw_strain_text, dob_raw, dob_start, dob_end,
                   ear_label_raw, ear_label_code, source_note_item_id, source_photo_id,
                   status, updated_at
            FROM mouse_master
            WHERE mouse_id IN ({placeholders})
            ORDER BY display_id COLLATE NOCASE
            """,
            unique_mouse_ids,
        ).fetchall()
        mice = [dict(row) for row in mouse_rows]

    action_rows = conn.execute(
        """
        SELECT action_id, action_type, target_id, before_value, after_value, created_at
        FROM action_log
        WHERE target_id = ?
          AND action_type LIKE 'canonical_candidate_%'
        ORDER BY created_at, action_id
        """,
        (candidate_id,),
    ).fetchall()
    actions = []
    for action in action_rows:
        payload = dict(action)
        payload["before_value"] = json_object(payload.get("before_value"))
        payload["after_value"] = json_object(payload.get("after_value"))
        actions.append(payload)

    can_void = candidate["status"] == "applied" and bool(unique_mouse_ids)
    blockers = []
    if candidate["status"] != "applied":
        blockers.append(f"Candidate status is {candidate['status']}, not applied.")
    if not unique_mouse_ids:
        blockers.append("No applied mouse records are linked to this candidate.")

    return {
        "boundary": "export or view",
        "candidate": {
            **dict(candidate),
            "candidate_payload": json_object(candidate["candidate_payload"]),
        },
        "applied_mouse_ids": unique_mouse_ids,
        "mice": mice,
        "events": events,
        "actions": actions,
        "can_void": can_void,
        "blockers": blockers,
        "summary": {
            "applied_mouse_count": len(unique_mouse_ids),
            "current_mouse_count": len(mice),
            "event_count": len(events),
            "action_count": len(actions),
            "voided_event_count": sum(1 for item in events if item["event_type"] == "canonical_candidate_voided"),
        },
    }


@app.get("/api/canonical-candidates/{candidate_id}/apply-preview")
def preview_canonical_candidate_apply(candidate_id: str) -> dict[str, Any]:
    with connection() as conn:
        return canonical_candidate_apply_preview(conn, candidate_id)


@app.get("/api/canonical-candidates/{candidate_id}/audit")
def audit_canonical_candidate(candidate_id: str) -> dict[str, Any]:
    with connection() as conn:
        return canonical_candidate_audit_view(conn, candidate_id)


@app.post("/api/canonical-candidates/{candidate_id}/apply")
def apply_canonical_candidate(candidate_id: str) -> dict[str, Any]:
    applied_at = utc_now()
    created_mice = 0
    existing_mice = 0
    created_events = 0
    mouse_ids: list[str] = []
    with connection() as conn:
        preview = canonical_candidate_apply_preview(conn, candidate_id)
        if preview["blockers"]:
            raise HTTPException(status_code=409, detail=preview)
        candidate = conn.execute(
            """
            SELECT candidate.candidate_id, candidate.review_id, candidate.parse_id,
                   candidate.legacy_row_id, candidate.proposed_strain,
                   candidate.proposed_dob, candidate.candidate_payload,
                   candidate.status, review.status AS review_status
            FROM canonical_candidate candidate
            JOIN review_queue review ON review.review_id = candidate.review_id
            WHERE candidate.candidate_id = ?
            """,
            (candidate_id,),
        ).fetchone()
        if candidate is None:
            raise HTTPException(status_code=404, detail="Canonical candidate draft not found.")
        if candidate["status"] != "draft":
            raise HTTPException(status_code=409, detail="Only draft canonical candidates can be applied.")
        if candidate["review_status"] != "resolved":
            raise HTTPException(status_code=409, detail="Candidate review must be resolved before canonical apply.")

        payload = json_object(candidate["candidate_payload"])
        raw_strain_text = str(candidate["proposed_strain"] or payload.get("strain") or "")
        dob_raw = str(candidate["proposed_dob"] or payload.get("dob") or "")
        dob_raw, dob_start, dob_end = split_dob_range(dob_raw, dob_raw)
        note_rows = conn.execute(
            """
            SELECT note_item_id, photo_id, line_number, raw_line_text, interpreted_status,
                   parsed_mouse_display_id, parsed_ear_label_raw, parsed_ear_label_code,
                   parsed_ear_label_confidence, parsed_ear_label_review_status
            FROM card_note_item_log
            WHERE parse_id = ?
              AND parsed_type = 'mouse_item'
              AND parsed_mouse_display_id IS NOT NULL
              AND parsed_mouse_display_id != ''
            ORDER BY line_number
            """,
            (candidate["parse_id"],),
        ).fetchall()
        if not note_rows:
            raise HTTPException(status_code=400, detail="Candidate has no parsed mouse note lines to apply.")

        for note in note_rows:
            display_id = str(note["parsed_mouse_display_id"])
            mouse_id = f"mouse_{display_id}_{candidate['parse_id']}".replace(" ", "_")
            existing = conn.execute(
                "SELECT mouse_id FROM mouse_master WHERE mouse_id = ?",
                (mouse_id,),
            ).fetchone()
            duplicate = conn.execute(
                """
                SELECT mouse_id, source_note_item_id
                FROM mouse_master
                WHERE display_id = ?
                  AND mouse_id != ?
                  AND status IN ('active', 'mating', 'pre_weaning', 'weaning_pending')
                LIMIT 1
                """,
                (display_id, mouse_id),
            ).fetchone()
            if duplicate is not None:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Active mouse with this display ID already exists. Resolve duplicate evidence before applying.",
                        "display_id": display_id,
                        "existing_mouse_id": duplicate["mouse_id"],
                        "existing_source_note_item_id": duplicate["source_note_item_id"],
                        "candidate_id": candidate_id,
                        "source_note_item_id": note["note_item_id"],
                    },
                )
            reviewed_ear_code = (
                note["parsed_ear_label_code"]
                if note["parsed_ear_label_review_status"] in {"auto_filled", "verified", "user_corrected"}
                else None
            )
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO mouse_master
                        (mouse_id, display_id, id_prefix, raw_strain_text, dob_raw, dob_start, dob_end,
                         ear_label_raw, ear_label_code, ear_label_confidence, ear_label_review_status,
                         source_note_item_id, status, source_photo_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mouse_id,
                        display_id,
                        mouse_id_prefix(display_id),
                        raw_strain_text,
                        dob_raw,
                        dob_start,
                        dob_end,
                        note["parsed_ear_label_raw"],
                        reviewed_ear_code,
                        note["parsed_ear_label_confidence"],
                        note["parsed_ear_label_review_status"],
                        note["note_item_id"],
                        note["interpreted_status"] or "active",
                        note["photo_id"],
                        applied_at,
                    ),
                )
                created_mice += 1
            else:
                existing_mice += 1
            mouse_ids.append(mouse_id)

            event_id = f"event_apply_{candidate_id}_{note['note_item_id']}".replace(" ", "_")
            existing_event = conn.execute(
                "SELECT event_id FROM mouse_event WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if existing_event is None:
                conn.execute(
                    """
                    INSERT INTO mouse_event
                        (event_id, mouse_id, event_type, event_date, related_entity_type,
                         related_entity_id, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        mouse_id,
                        "canonical_candidate_applied",
                        applied_at[:10],
                        "canonical_candidate",
                        candidate_id,
                        json.dumps(
                            {
                                "review_id": candidate["review_id"],
                                "parse_id": candidate["parse_id"],
                                "legacy_row_id": candidate["legacy_row_id"],
                                "note_item_id": note["note_item_id"],
                                "raw_line_text": note["raw_line_text"],
                                "boundary": "canonical structured state",
                            },
                            ensure_ascii=False,
                        ),
                        applied_at,
                    ),
                )
                created_events += 1

        before_status = candidate["status"]
        conn.execute(
            """
            UPDATE canonical_candidate
            SET status = 'applied',
                updated_at = ?
            WHERE candidate_id = ?
            """,
            (applied_at, candidate_id),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "canonical_candidate_applied",
                candidate_id,
                json.dumps({"status": before_status}, ensure_ascii=False),
                json.dumps(
                    {
                        "status": "applied",
                        "created_mice": created_mice,
                        "existing_mice": existing_mice,
                        "created_events": created_events,
                        "mouse_ids": mouse_ids,
                    },
                    ensure_ascii=False,
                ),
                applied_at,
            ),
        )

    return {
        "candidate_id": candidate_id,
        "status": "applied",
        "applied_at": applied_at,
        "created_mice": created_mice,
        "existing_mice": existing_mice,
        "created_events": created_events,
        "mouse_ids": mouse_ids,
        "boundary": "canonical structured state",
    }


@app.post("/api/canonical-candidates/{candidate_id}/void")
def void_canonical_candidate(candidate_id: str) -> dict[str, Any]:
    voided_at = utc_now()
    created_events = 0
    updated_mice = 0
    affected_mouse_ids: list[str] = []
    with connection() as conn:
        audit = canonical_candidate_audit_view(conn, candidate_id)
        if not audit["can_void"]:
            raise HTTPException(status_code=409, detail=audit)

        before_candidate = audit["candidate"]
        affected_mouse_ids = audit["applied_mouse_ids"]
        before_mouse_statuses = {item["mouse_id"]: item["status"] for item in audit["mice"]}
        for mouse_id in affected_mouse_ids:
            current_mouse = conn.execute(
                """
                SELECT mouse_id, status
                FROM mouse_master
                WHERE mouse_id = ?
                """,
                (mouse_id,),
            ).fetchone()
            if current_mouse is None:
                continue
            before_status = current_mouse["status"]
            if before_status != "voided":
                conn.execute(
                    """
                    UPDATE mouse_master
                    SET status = 'voided',
                        updated_at = ?
                    WHERE mouse_id = ?
                    """,
                    (voided_at, mouse_id),
                )
                updated_mice += 1

            event_id = f"event_void_{candidate_id}_{mouse_id}".replace(" ", "_")
            existing_event = conn.execute(
                "SELECT event_id FROM mouse_event WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if existing_event is None:
                conn.execute(
                    """
                    INSERT INTO mouse_event
                        (event_id, mouse_id, event_type, event_date, related_entity_type,
                         related_entity_id, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        mouse_id,
                        "canonical_candidate_voided",
                        voided_at[:10],
                        "canonical_candidate",
                        candidate_id,
                        json.dumps(
                            {
                                "candidate_id": candidate_id,
                                "before_status": before_status,
                                "after_status": "voided",
                                "reason": "Applied canonical candidate was voided without deleting source-backed mouse records.",
                                "boundary": "canonical structured state",
                            },
                            ensure_ascii=False,
                        ),
                        voided_at,
                    ),
                )
                created_events += 1

        conn.execute(
            """
            UPDATE canonical_candidate
            SET status = 'voided',
                updated_at = ?
            WHERE candidate_id = ?
            """,
            (voided_at, candidate_id),
        )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "canonical_candidate_voided",
                candidate_id,
                json.dumps(
                    {
                        "status": before_candidate["status"],
                        "mouse_statuses": before_mouse_statuses,
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "status": "voided",
                        "updated_mice": updated_mice,
                        "created_events": created_events,
                        "mouse_ids": affected_mouse_ids,
                    },
                    ensure_ascii=False,
                ),
                voided_at,
            ),
        )

    return {
        "candidate_id": candidate_id,
        "status": "voided",
        "voided_at": voided_at,
        "updated_mice": updated_mice,
        "created_events": created_events,
        "mouse_ids": affected_mouse_ids,
        "boundary": "canonical structured state",
    }


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


def legacy_row_payload(row: Any) -> dict[str, Any]:
    result = dict(row)
    result["raw_row"] = json_object(result.pop("raw_row_json", "{}"))
    return result


def legacy_review_current_value(row: dict[str, Any], fallback_row_number: int) -> str:
    source_cells = row.get("source_cells") if isinstance(row.get("source_cells"), dict) else {}
    anchors = {
        "row_type": row.get("row_type") or "",
        "source_row_number": row.get("source_row_number") or fallback_row_number,
        "cage_no_raw": row.get("cage_no_raw") or row.get("group_name_raw") or "",
        "strain_raw": row.get("strain_raw") or row.get("male_raw") or "",
        "display_id_raw": row.get("display_id_raw") or row.get("female_raw") or "",
        "genotype_raw": row.get("genotype_raw") or row.get("total_raw") or "",
        "source_cells": source_cells,
    }
    return json.dumps({key: value for key, value in anchors.items() if value not in ("", None, {})}, ensure_ascii=False)


def legacy_review_reason(row: dict[str, Any], source_file_name: str, sheet_name: str, fallback_row_number: int) -> str:
    row_number = parse_optional_int(row.get("source_row_number")) or fallback_row_number
    source_sheet = str(row.get("source_sheet") or sheet_name or "")
    cells = row.get("source_cells") if isinstance(row.get("source_cells"), dict) else {}
    cell_refs = ", ".join(f"{key}:{value}" for key, value in cells.items() if value) or "no cell refs"
    return (
        f"Legacy workbook row from {source_file_name}, sheet {source_sheet or '--'}, row {row_number}; "
        f"source cells {cell_refs}. Imported as a review candidate only; do not write canonical mouse, cage, "
        "litter, or genotype state until a human resolves the row."
    )


def json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {"raw": value}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


def compact_compare_value(value: Any) -> str:
    return "".join(char for char in str(value or "").lower() if char.isalnum())


def date_tokens(value: Any) -> set[str]:
    text = str(value or "")
    tokens = set(re.findall(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{2}[-./]\d{1,2}[-./]\d{1,2}", text))
    return {token.replace("/", ".").replace("-", ".") for token in tokens}


def first_count(value: Any) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


def manual_transcription_summary(record: dict[str, Any]) -> dict[str, Any]:
    notes = record.get("notes") if isinstance(record.get("notes"), list) else []
    return {
        "strain": record.get("matchedStrain") or record.get("rawStrain") or "",
        "sex": record.get("sexRaw") or "",
        "id": record.get("idRaw") or "",
        "dob": record.get("dobRaw") or record.get("dobNormalized") or "",
        "count": first_count(record.get("mouseCount")) or len(notes) or None,
        "count_raw": record.get("mouseCount") or "",
        "card_type": record.get("type") or "",
        "note_count": len(notes),
    }


def legacy_candidate_summary(row: dict[str, Any]) -> dict[str, Any]:
    row_type = str(row.get("row_type") or "")
    return {
        "strain": row.get("strain_raw") or row.get("group_name_raw") or row.get("male_raw") or "",
        "dob": row.get("dob_raw") or "",
        "count": row.get("count_candidate") or first_count(row.get("total_raw") or row.get("display_id_raw")),
        "count_raw": row.get("total_raw") or row.get("display_id_raw") or row.get("pubs_raw") or "",
        "row_type": row_type,
    }


def comparison_score(manual: dict[str, Any], legacy: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    matched: list[str] = []
    mismatched: list[str] = []
    score = 0

    manual_strain = compact_compare_value(manual.get("strain"))
    legacy_strain = compact_compare_value(legacy.get("strain"))
    if manual_strain and legacy_strain:
        if manual_strain == legacy_strain or manual_strain in legacy_strain or legacy_strain in manual_strain:
            score += 3
            matched.append("strain")
        else:
            mismatched.append("strain")

    manual_dates = date_tokens(manual.get("dob"))
    legacy_dates = date_tokens(legacy.get("dob"))
    if manual_dates and legacy_dates:
        if manual_dates & legacy_dates:
            score += 2
            matched.append("dob")
        else:
            mismatched.append("dob")

    manual_count = manual.get("count")
    legacy_count = legacy.get("count")
    if manual_count is not None and legacy_count is not None:
        if manual_count == legacy_count:
            score += 1
            matched.append("count")
        else:
            mismatched.append("count")

    return score, matched, mismatched


def comparison_review_id(manual_parse_id: str, legacy_row_id: str) -> str:
    raw_id = f"review_comparison_{manual_parse_id}_{legacy_row_id}"
    return re.sub(r"[^A-Za-z0-9_-]+", "_", raw_id)


def build_evidence_comparison_payload(conn: Any) -> dict[str, Any]:
    manual_rows = conn.execute(
        """
        SELECT parse.parse_id, parse.photo_id, parse.raw_payload, parse.parsed_at,
               photo.original_filename
        FROM parse_result parse
        LEFT JOIN photo_log photo ON photo.photo_id = parse.photo_id
        WHERE parse.source_name IN ('manual_photo_transcription', 'ai_photo_extraction')
        ORDER BY parse.parsed_at DESC
        LIMIT 50
        """
    ).fetchall()
    legacy_rows = conn.execute(
        """
        SELECT row.legacy_row_id, row.review_id, row.row_type, row.source_sheet,
               row.source_row_number, row.raw_row_json,
               legacy.source_file_name
        FROM legacy_workbook_row row
        LEFT JOIN legacy_workbook_import legacy ON legacy.legacy_import_id = row.legacy_import_id
        ORDER BY legacy.imported_at DESC, row.source_row_number
        """
    ).fetchall()

    legacy_candidates = []
    for row in legacy_rows:
        raw_row = json_object(row["raw_row_json"])
        summary = legacy_candidate_summary(raw_row)
        legacy_candidates.append(
            {
                "legacy_row_id": row["legacy_row_id"],
                "review_id": row["review_id"],
                "source_file_name": row["source_file_name"] or "",
                "source_sheet": row["source_sheet"] or "",
                "source_row_number": row["source_row_number"],
                "raw_row": raw_row,
                "summary": summary,
            }
        )

    comparisons = []
    for manual in manual_rows:
        record = json_object(manual["raw_payload"])
        manual_summary = manual_transcription_summary(record)
        ranked = []
        for legacy in legacy_candidates:
            score, matched, mismatched = comparison_score(manual_summary, legacy["summary"])
            if score >= 2:
                ranked.append((score, matched, mismatched, legacy))
        ranked.sort(key=lambda item: item[0], reverse=True)
        best = ranked[0] if ranked else None
        if best is None:
            status = "no_legacy_candidate"
            matched_fields: list[str] = []
            mismatched_fields: list[str] = []
            legacy_payload: dict[str, Any] | None = None
            detail = "No predecessor Excel candidate matched strain, DOB, or count."
        else:
            score, matched_fields, mismatched_fields, legacy_payload = best
            status = "exact_match" if score >= 6 and not mismatched_fields else "value_mismatch"
            detail = (
                f"Matched {', '.join(matched_fields) or 'none'}"
                + (f"; differs on {', '.join(mismatched_fields)}" if mismatched_fields else "")
            )
        legacy_row_id = (
            str(legacy_payload.get("legacy_row_id"))
            if isinstance(legacy_payload, dict) and legacy_payload.get("legacy_row_id")
            else "no_legacy_candidate"
        )
        review_id = comparison_review_id(manual["parse_id"], legacy_row_id)
        comparisons.append(
            {
                "source_layer": "export or view",
                "manual_parse_id": manual["parse_id"],
                "photo_id": manual["photo_id"],
                "photo_filename": manual["original_filename"] or "",
                "manual_summary": manual_summary,
                "legacy_candidate": legacy_payload,
                "status": status,
                "matched_fields": matched_fields,
                "mismatched_fields": mismatched_fields,
                "detail": detail,
                "review_required": status != "exact_match",
                "review_id": review_id,
                "review_status": "not_created" if status != "exact_match" else "not_required",
            }
        )

    review_ids = [comparison["review_id"] for comparison in comparisons if comparison.get("review_required")]
    if review_ids:
        placeholders = ",".join("?" for _ in review_ids)
        review_rows = conn.execute(
            f"""
            SELECT review_id, status, severity, issue
            FROM review_queue
            WHERE review_id IN ({placeholders})
            """,
            review_ids,
        ).fetchall()
        reviews_by_id = {row["review_id"]: dict(row) for row in review_rows}
        for comparison in comparisons:
            review = reviews_by_id.get(comparison["review_id"])
            if review:
                comparison["review_status"] = review["status"]
                comparison["review_severity"] = review["severity"]
                comparison["review_issue"] = review["issue"]

    return {
        "boundary": "export or view",
        "source_priority": ["raw source photo", "manual transcription", "predecessor Excel view"],
        "manual_transcription_count": len(manual_rows),
        "legacy_candidate_count": len(legacy_candidates),
        "comparison_count": len(comparisons),
        "comparisons": comparisons,
    }


def split_dob_range(raw: Any, normalized: Any) -> tuple[str, str | None, str | None]:
    dob_raw = str(raw or "")
    normalized_text = str(normalized or "")
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", normalized_text)
    if len(dates) >= 2:
        return dob_raw, dates[0], dates[1]
    if len(dates) == 1:
        return dob_raw, dates[0], dates[0]
    return dob_raw, None, None


def normalize_sex_raw(raw: Any) -> str:
    text = str(raw or "").strip()
    lowered = text.lower()
    if "\u2642" in text or lowered in {"m", "male", "man"}:
        return "male"
    if "\u2640" in text or lowered in {"f", "female", "woman"}:
        return "female"
    if any(token in lowered for token in ["mixed", "both", "m/f", "f/m", "mf"]):
        return "mixed"
    return "unknown" if text else ""


def first_int(value: Any) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


def unlabeled_numeric_metadata(raw_line: str) -> dict[str, Any]:
    labels = re.findall(r"\d+", raw_line)
    return {
        "labels": labels,
        "count": len(labels),
        "display": f"Label pending {', '.join(labels)} ({len(labels)}p)" if labels else "Label pending",
        "display_ko": f"라벨 미정 {', '.join(labels)} ({len(labels)}p)" if labels else "라벨 미정",
        "export_policy": "block_final_export_until_labeled_or_confirmed",
    }


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
    numeric_tokens = re.findall(r"\d+", line)
    numeric_only = bool(numeric_tokens) and re.fullmatch(r"[\d\s,./\\-]+", line)
    if numeric_only and not re.search(r"\d{2,4}[./-]\d{1,2}[./-]\d{1,2}", line):
        metadata = unlabeled_numeric_metadata(line)
        return {
            "parsed_type": "unlabeled_numeric_note",
            "parsed_mouse_display_id": None,
            "parsed_ear_label_raw": None,
            "parsed_ear_label_code": None,
            "parsed_ear_label_confidence": None,
            "parsed_ear_label_review_status": "needs_review",
            "parsed_event_date": None,
            "parsed_count": metadata["count"],
            "parsed_metadata": metadata,
            "confidence": 0.5,
            "needs_review": 1,
        }

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
            "parsed_metadata": {},
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
            "parsed_metadata": {},
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
        "parsed_metadata": {},
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


def card_note_summary(record: dict[str, Any]) -> dict[str, Any]:
    card_type = str(record.get("type") or "unknown")
    notes = record.get("notes") if isinstance(record.get("notes"), list) else []
    summary = {
        "note_count": 0,
        "mouse_item_count": 0,
        "litter_event_count": 0,
        "unlabeled_numeric_count": 0,
        "unlabeled_numeric_labels": [],
        "unlabeled_numeric_display": [],
        "unknown_count": 0,
        "needs_review_count": 0,
    }
    for note in notes:
        raw_line = str(note.get("raw") if isinstance(note, dict) else note)
        if not raw_line.strip():
            continue
        parsed = parse_note_line(raw_line, card_type)
        summary["note_count"] += 1
        parsed_type = parsed["parsed_type"]
        if parsed_type == "mouse_item":
            summary["mouse_item_count"] += 1
        elif parsed_type == "litter_event":
            summary["litter_event_count"] += 1
        elif parsed_type == "unlabeled_numeric_note":
            metadata = parsed.get("parsed_metadata") or {}
            summary["unlabeled_numeric_count"] += int(metadata.get("count") or 0)
            summary["unlabeled_numeric_labels"].extend(metadata.get("labels") or [])
            summary["unlabeled_numeric_display"].append(metadata.get("display_ko") or raw_line)
        else:
            summary["unknown_count"] += 1
        if parsed["needs_review"]:
            summary["needs_review_count"] += 1
    return summary


def create_card_snapshot(conn: Any, parse_id: str, photo_id: str | None, record: dict[str, Any], created_at: str) -> str:
    card_snapshot_id = new_id("card_snapshot")
    dob_raw, dob_start, dob_end = split_dob_range(record.get("dobRaw"), record.get("dobNormalized"))
    note_summary = card_note_summary(record)
    conn.execute(
        """
        INSERT INTO card_snapshot
            (card_snapshot_id, photo_id, parse_id, card_type, card_id_raw,
             raw_strain_text, matched_strain_text, sex_raw, sex_normalized,
             sex_count_raw, count_value, dob_raw, dob_start, dob_end,
             mating_date_raw, mating_date_normalized, lmo_raw, note_summary_json,
             status, source_layer, confidence, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            card_snapshot_id,
            photo_id,
            parse_id,
            str(record.get("type") or "unknown"),
            str(record.get("idRaw") or ""),
            str(record.get("rawStrain") or ""),
            str(record.get("matchedStrain") or ""),
            str(record.get("sexRaw") or ""),
            normalize_sex_raw(record.get("sexRaw")),
            str(record.get("mouseCount") or ""),
            first_int(record.get("mouseCount")),
            dob_raw,
            dob_start,
            dob_end,
            str(record.get("matingDateRaw") or ""),
            str(record.get("matingDateNormalized") or ""),
            str(record.get("lmoRaw") or ""),
            json.dumps(note_summary, ensure_ascii=False),
            "review",
            "parsed or intermediate result",
            bounded_float(record.get("confidence")),
            created_at,
            created_at,
        ),
    )
    return card_snapshot_id


def refresh_card_snapshot_summary(conn: Any, card_snapshot_id: str, updated_at: str) -> dict[str, Any] | None:
    if not card_snapshot_id:
        return None
    rows = conn.execute(
        """
        SELECT parsed_type, raw_line_text, parsed_count, parsed_metadata_json, needs_review
        FROM card_note_item_log
        WHERE card_snapshot_id = ?
        ORDER BY line_number
        """,
        (card_snapshot_id,),
    ).fetchall()
    if not rows:
        return None

    summary: dict[str, Any] = {
        "note_count": len(rows),
        "mouse_item_count": 0,
        "litter_event_count": 0,
        "unlabeled_numeric_count": 0,
        "unlabeled_numeric_labels": [],
        "unlabeled_numeric_display": [],
        "count_note_total": 0,
        "count_note_lines": 0,
        "reviewed_note_count": 0,
        "ignored_note_count": 0,
        "unknown_count": 0,
        "needs_review_count": 0,
    }
    for row in rows:
        parsed_type = row["parsed_type"]
        if parsed_type == "mouse_item":
            summary["mouse_item_count"] += 1
        elif parsed_type == "litter_event":
            summary["litter_event_count"] += 1
        elif parsed_type == "unlabeled_numeric_note":
            metadata = json_object(row["parsed_metadata_json"])
            summary["unlabeled_numeric_count"] += int(metadata.get("count") or 0)
            summary["unlabeled_numeric_labels"].extend(metadata.get("labels") or [])
            summary["unlabeled_numeric_display"].append(metadata.get("display_ko") or row["raw_line_text"])
        elif parsed_type == "count_note":
            summary["count_note_lines"] += 1
            summary["count_note_total"] += int(row["parsed_count"] or 0)
        elif parsed_type == "reviewed_note":
            summary["reviewed_note_count"] += 1
        elif parsed_type == "ignored_note":
            summary["ignored_note_count"] += 1
        else:
            summary["unknown_count"] += 1
        if row["needs_review"]:
            summary["needs_review_count"] += 1

    status = "review" if summary["needs_review_count"] else "reviewed"
    conn.execute(
        """
        UPDATE card_snapshot
        SET note_summary_json = ?,
            status = ?,
            updated_at = ?
        WHERE card_snapshot_id = ?
        """,
        (json.dumps(summary, ensure_ascii=False), status, updated_at, card_snapshot_id),
    )
    return {"card_snapshot_id": card_snapshot_id, "status": status, "note_summary": summary}


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


def write_note_items_and_mouse_candidates(
    conn: Any,
    parse_id: str,
    record: dict[str, Any],
    status: str,
    card_snapshot_id: str = "",
) -> tuple[int, int, int]:
    card_type = str(record.get("type") or "unknown").lower()
    notes = record.get("notes") if isinstance(record.get("notes"), list) else []
    note_count = 0
    mouse_count = 0
    ear_review_count = 0
    write_mouse = should_write_mouse_candidate(record, status)
    dob_raw, dob_start, dob_end = split_dob_range(record.get("dobRaw"), record.get("dobNormalized"))
    raw_strain_text = str(record.get("matchedStrain") or record.get("rawStrain") or "")
    photo_id = str(record.get("sourcePhotoId") or "")
    snapshot_id = card_snapshot_id or str(record.get("cardSnapshotId") or "")

    for index, note in enumerate(notes, start=1):
        raw_line = str(note.get("raw") if isinstance(note, dict) else note)
        strike_status = str(note.get("strike") or "none") if isinstance(note, dict) else "none"
        parsed = parse_note_line(raw_line, card_type)
        status_from_strike = interpreted_status(card_type, strike_status)
        interpreted = (
            "needs_label_review"
            if parsed["parsed_type"] == "unlabeled_numeric_note"
            else status_from_strike if parsed["parsed_type"] != "unknown" else "unknown"
        )
        note_item_id = f"note_{parse_id}_{index}"
        conn.execute(
            """
            INSERT OR REPLACE INTO card_note_item_log
                (note_item_id, photo_id, parse_id, card_snapshot_id, card_type, line_number, raw_line_text, strike_status,
                 parsed_type, interpreted_status, parsed_mouse_display_id, parsed_ear_label_raw,
                 parsed_ear_label_code, parsed_ear_label_confidence, parsed_ear_label_review_status,
                 parsed_event_date, parsed_count, parsed_metadata_json, confidence, needs_review)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_item_id,
                photo_id or None,
                parse_id,
                snapshot_id or None,
                card_type,
                index,
                raw_line,
                strike_status,
                parsed["parsed_type"],
                interpreted,
                parsed["parsed_mouse_display_id"],
                parsed["parsed_ear_label_raw"],
                parsed["parsed_ear_label_code"],
                parsed["parsed_ear_label_confidence"],
                parsed["parsed_ear_label_review_status"],
                parsed["parsed_event_date"],
                parsed["parsed_count"],
                json.dumps(parsed.get("parsed_metadata") or {}, ensure_ascii=False),
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

        if parsed["parsed_type"] == "unlabeled_numeric_note":
            review_id = f"review_unlabeled_numeric_{note_item_id}"
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
                    "Unlabeled numeric note needs review",
                    raw_line,
                    parsed.get("parsed_metadata", {}).get("display_ko") or "라벨 미정",
                    f"Note item {note_item_id} contains only numbers. Treat it as temporary unlabeled cage evidence until labels are assigned.",
                    "open",
                    utc_now(),
                ),
            )

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


@app.get("/api/legacy-workbook-imports")
def list_legacy_workbook_imports() -> list[dict[str, Any]]:
    with connection() as conn:
        imports = conn.execute(
            """
            SELECT legacy_import_id, source_record_id, source_file_name, source_file_path,
                   workbook_kind, sheet_name, imported_at, status, notes,
                   (
                       SELECT COUNT(*)
                       FROM review_queue review
                       WHERE review.parse_id = 'legacy_parse_' || legacy_workbook_import.legacy_import_id
                   ) AS review_count,
                   (
                       SELECT COUNT(*)
                       FROM review_queue review
                       WHERE review.parse_id = 'legacy_parse_' || legacy_workbook_import.legacy_import_id
                         AND review.status = 'open'
                   ) AS open_review_count
            FROM legacy_workbook_import
            ORDER BY imported_at DESC
            """
        ).fetchall()
        rows = conn.execute(
            """
            SELECT legacy_row_id, legacy_import_id, review_id, row_type, source_sheet,
                   source_row_number, raw_row_json, review_status
            FROM legacy_workbook_row
            ORDER BY legacy_import_id, source_row_number
            """
        ).fetchall()

    rows_by_import: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        payload = legacy_row_payload(row)
        rows_by_import.setdefault(payload["legacy_import_id"], []).append(payload)

    return [
        {**dict(import_row), "rows": rows_by_import.get(import_row["legacy_import_id"], [])}
        for import_row in imports
    ]


@app.post("/api/legacy-workbook-imports")
def create_legacy_workbook_import(
    file: UploadFile = File(...),
    kind: str = Form("auto"),
    sheet_name: str = Form(""),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    if kind not in {"auto", "animal", "separation"}:
        raise HTTPException(status_code=400, detail="Legacy workbook kind must be auto, animal, or separation.")

    import_id = new_id("legacy_import")
    parse_id = f"legacy_parse_{import_id}"
    stored_path = save_legacy_workbook(file, import_id)
    source_uri = str(stored_path.relative_to(ROOT))
    try:
        parsed = parse_workbook(stored_path, kind=kind, sheet_name=sheet_name.strip() or None)
    except Exception as error:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not parse legacy workbook: {error}") from error

    rows = parsed.get("rows") or []
    if not isinstance(rows, list):
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Legacy workbook parser returned an invalid row payload.")

    imported_at = utc_now()
    raw_payload = json.dumps(parsed, ensure_ascii=False)
    inserted_rows = 0
    created_review_items = 0
    try:
        with connection() as conn:
            source_record_id = create_source_record(
                conn,
                source_type="legacy_workbook",
                source_uri=source_uri,
                source_label=file.filename,
                raw_payload=raw_payload,
                note="Predecessor Excel workbook preserved as an export/view source; parsed rows stay review candidates.",
            )
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parse_id,
                    None,
                    file.filename,
                    raw_payload,
                    imported_at,
                    "review",
                    1,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO legacy_workbook_import
                    (legacy_import_id, source_record_id, source_file_name, source_file_path,
                     workbook_kind, sheet_name, imported_at, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_id,
                    source_record_id,
                    file.filename,
                    source_uri,
                    str(parsed.get("workbook_kind") or ""),
                    str(parsed.get("sheet_name") or ""),
                    imported_at,
                    "parsed",
                    "Legacy Excel rows are parsed/intermediate review candidates, not canonical colony state.",
                ),
            )
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    continue
                row_number = parse_optional_int(row.get("source_row_number")) or index
                legacy_row_id = new_id("legacy_row")
                review_id = new_id("review")
                conn.execute(
                    """
                    INSERT INTO review_queue
                        (review_id, parse_id, severity, issue, current_value, suggested_value,
                         review_reason, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        review_id,
                        parse_id,
                        "Medium",
                        "Legacy workbook row requires review",
                        legacy_review_current_value(row, row_number),
                        str(row.get("row_type") or "candidate"),
                        legacy_review_reason(
                            row,
                            file.filename,
                            str(parsed.get("sheet_name") or ""),
                            row_number,
                        ),
                        "open",
                        imported_at,
                    ),
                )
                created_review_items += 1
                conn.execute(
                    """
                    INSERT INTO legacy_workbook_row
                        (legacy_row_id, legacy_import_id, review_id, row_type, source_sheet,
                         source_row_number, raw_row_json, review_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        legacy_row_id,
                        import_id,
                        review_id,
                        str(row.get("row_type") or ""),
                        str(row.get("source_sheet") or parsed.get("sheet_name") or ""),
                        row_number,
                        json.dumps(row, ensure_ascii=False),
                        str(row.get("review_status") or "candidate"),
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
                    "legacy_workbook_import_created",
                    import_id,
                    None,
                    json.dumps(
                        {
                            "source_file_name": file.filename,
                            "source_record_id": source_record_id,
                            "parse_id": parse_id,
                            "workbook_kind": parsed.get("workbook_kind"),
                            "rows": inserted_rows,
                            "created_review_items": created_review_items,
                            "boundary": "parsed or intermediate result",
                        },
                        ensure_ascii=False,
                    ),
                    imported_at,
                ),
            )
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise

    return {
        "legacy_import_id": import_id,
        "parse_id": parse_id,
        "source_record_id": source_record_id,
        "source_file_name": file.filename,
        "source_file_path": source_uri,
        "workbook_kind": parsed.get("workbook_kind"),
        "sheet_name": parsed.get("sheet_name"),
        "imported_at": imported_at,
        "status": "parsed",
        "stored_rows": inserted_rows,
        "created_review_items": created_review_items,
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
            review_candidate = ensure_photo_review_candidate(
                conn,
                photo_id=photo_id,
                original_filename=file.filename,
                stored_path=str(stored_path.relative_to(ROOT)),
                uploaded_at=uploaded_at,
                source_record_id=source_record_id,
            )
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise
    return {
        "photo_id": photo_id,
        "original_filename": file.filename,
        "stored_path": str(stored_path.relative_to(ROOT)),
        "uploaded_at": uploaded_at,
        "status": "review_pending",
        "source_record_id": source_record_id,
        "review_candidate": review_candidate,
    }


@app.post("/api/photos/review-candidates")
def create_missing_photo_review_candidates() -> dict[str, Any]:
    created = 0
    existing = 0
    with connection() as conn:
        photos = conn.execute(
            """
            SELECT photo.photo_id, photo.original_filename, photo.stored_path,
                   photo.uploaded_at,
                   source.source_record_id
            FROM photo_log photo
            LEFT JOIN source_record source
                ON source.source_type = 'photo'
               AND source.source_uri = photo.stored_path
               AND source.source_label = photo.original_filename
            ORDER BY photo.uploaded_at
            """
        ).fetchall()
        for photo in photos:
            result = ensure_photo_review_candidate(
                conn,
                photo_id=photo["photo_id"],
                original_filename=photo["original_filename"],
                stored_path=photo["stored_path"],
                uploaded_at=photo["uploaded_at"],
                source_record_id=photo["source_record_id"] or "",
            )
            if result["created"]:
                created += 1
            else:
                existing += 1
    return {
        "created_review_candidates": created,
        "existing_review_candidates": existing,
        "boundary": "review item",
        "source_layer": "raw source",
    }


@app.post("/api/photos/{photo_id}/manual-transcription")
def create_photo_manual_transcription(photo_id: str, payload: PhotoManualTranscriptionCreate) -> dict[str, Any]:
    now = utc_now()
    source_name = "ai_photo_extraction" if payload.extraction_method == "ai_photo_extraction" else "manual_photo_transcription"
    issue = "AI-extracted photo transcription needs review" if source_name == "ai_photo_extraction" else "Manual photo transcription needs review"
    review_reason = "Photo transcription is parsed/intermediate evidence. Review it before writing canonical mouse or cage state."
    action_note = (
        "Review AI-extracted fields against the raw cage-card photo before canonical writes."
        if source_name == "ai_photo_extraction"
        else "Keep manual transcription reviewable."
    )
    with connection() as conn:
        photo = conn.execute(
            """
            SELECT photo_id, original_filename, stored_path, uploaded_at, status
            FROM photo_log
            WHERE photo_id = ?
            """,
            (photo_id,),
        ).fetchone()
        if photo is None:
            raise HTTPException(status_code=404, detail="Photo not found.")

        parse_id = new_id("parse")
        notes = [
            {
                "raw": str(note.get("raw") or "").strip(),
                "meaning": str(note.get("meaning") or ""),
                "strike": str(note.get("strike") or "none"),
            }
            for note in payload.notes
            if isinstance(note, dict) and str(note.get("raw") or "").strip()
        ]
        record = {
            "id": parse_id,
            "uploaded": photo["original_filename"],
            "type": payload.card_type or "Separated",
            "rawStrain": payload.raw_strain,
            "matchedStrain": payload.matched_strain or payload.raw_strain,
            "sexRaw": payload.sex_raw,
            "idRaw": payload.id_raw,
            "dobRaw": payload.dob_raw,
            "dobNormalized": payload.dob_normalized,
            "matingDateRaw": payload.mating_date_raw,
            "matingDateNormalized": payload.mating_date_normalized,
            "lmoRaw": payload.lmo_raw,
            "mouseCount": payload.mouse_count,
            "confidence": payload.confidence,
            "status": "review",
            "issue": issue,
            "severity": "Medium",
            "reviewField": "manualTranscription",
            "currentValue": payload.mouse_count or payload.raw_strain or photo["original_filename"],
            "suggestedValue": "Compare against latest cage-card photo and predecessor Excel candidate rows.",
            "reviewReason": review_reason,
            "notes": notes,
            "actions": [
                "Preserve latest photo as raw source evidence.",
                action_note,
                "Compare against predecessor Excel rows before accepting changes.",
            ],
            "sourcePhotoId": photo_id,
            "sourceLayer": "parsed or intermediate result",
            "reviewerNote": payload.reviewer_note,
            "extractionMethod": payload.extraction_method,
        }
        conn.execute(
            """
            INSERT INTO parse_result
                (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parse_id,
                photo_id,
                source_name,
                json.dumps(record, ensure_ascii=False),
                now,
                "review",
                payload.confidence,
                1,
            ),
        )
        card_snapshot_id = create_card_snapshot(conn, parse_id, photo_id, record, now)
        record = {**record, "cardSnapshotId": card_snapshot_id}
        conn.execute(
            "UPDATE parse_result SET raw_payload = ? WHERE parse_id = ?",
            (json.dumps(record, ensure_ascii=False), parse_id),
        )
        note_count, mouse_count, ear_review_count = write_note_items_and_mouse_candidates(
            conn,
            parse_id,
            record,
            "review",
            card_snapshot_id,
        )
        review_id = f"review_{parse_id}"
        conn.execute(
            """
            INSERT INTO review_queue
                (review_id, parse_id, severity, issue, current_value, suggested_value,
                 review_reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                parse_id,
                "Medium",
                issue,
                payload.mouse_count or payload.raw_strain or photo["original_filename"],
                "Compare with raw photo and predecessor Excel before accepting.",
                "Latest cage-card photo should drive updates, but the parsed transcription itself must be reviewed before canonical writes.",
                "open",
                now,
            ),
        )
        conn.execute("UPDATE photo_log SET status = ? WHERE photo_id = ?", ("transcribed_review_pending", photo_id))
        photo_review_rows = conn.execute(
            """
            SELECT review.review_id
            FROM review_queue review
            JOIN parse_result parse ON parse.parse_id = review.parse_id
            WHERE parse.photo_id = ?
              AND parse.source_name = 'photo_manual_review'
              AND review.status = 'open'
            """,
            (photo_id,),
        ).fetchall()
        resolved_photo_review_ids = [row["review_id"] for row in photo_review_rows]
        if resolved_photo_review_ids:
            placeholders = ",".join("?" for _ in resolved_photo_review_ids)
            conn.execute(
                f"""
                UPDATE review_queue
                SET status = 'resolved',
                    resolved_at = ?,
                    resolution_note = ?
                WHERE review_id IN ({placeholders})
                """,
                [
                    now,
                    "Manual cage-card transcription was entered; review the parsed transcription before canonical writes.",
                    *resolved_photo_review_ids,
                ],
            )
        conn.execute(
            """
            INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("action"),
                "manual_photo_transcription_created",
                photo_id,
                json.dumps({"resolved_photo_review_ids": resolved_photo_review_ids}, ensure_ascii=False),
                json.dumps(
                    {
                    "parse_id": parse_id,
                    "card_snapshot_id": card_snapshot_id,
                    "review_id": review_id,
                    "note_count": note_count,
                    "source_name": source_name,
                    "resolved_photo_review_items": len(resolved_photo_review_ids),
                },
                ensure_ascii=False,
                ),
                now,
            ),
        )

    return {
        "parse_id": parse_id,
        "review_id": review_id,
        "card_snapshot_id": card_snapshot_id,
        "photo_id": photo_id,
        "created_note_items": note_count,
        "created_mouse_candidates": mouse_count,
        "created_ear_review_items": ear_review_count,
        "resolved_photo_review_items": len(resolved_photo_review_ids),
        "boundary": "parsed or intermediate result",
        "source_name": source_name,
    }


@app.get("/api/review-items")
def list_review_items() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT review.review_id, review.parse_id, review.severity, review.issue,
                   review.current_value, review.suggested_value, review.review_reason,
                   review.status, review.created_at, review.resolved_at, review.resolution_note,
                   parse.source_name, parse.photo_id, photo.original_filename,
                   review_note.note_item_id, review_note.raw_line_text AS review_note_raw_line,
                   review_note.parsed_type AS review_note_parsed_type,
                   review_note.interpreted_status AS review_note_interpreted_status,
                   review_note.parsed_mouse_display_id AS review_note_mouse_display_id,
                   review_note.parsed_count AS review_note_count,
                   review_snapshot.card_snapshot_id,
                   review_snapshot.card_type AS review_card_type,
                   review_snapshot.card_id_raw AS review_card_id_raw,
                   review_snapshot.raw_strain_text AS review_raw_strain_text,
                   review_snapshot.matched_strain_text AS review_matched_strain_text,
                   review_snapshot.sex_raw AS review_sex_raw,
                   review_snapshot.sex_normalized AS review_sex_normalized,
                   review_snapshot.count_value AS review_count_value,
                   review_snapshot.dob_raw AS review_dob_raw,
                   review_snapshot.note_summary_json AS review_note_summary_json,
                   (
                       SELECT COUNT(*)
                       FROM card_note_item_log note
                       WHERE note.parse_id = review.parse_id
                   ) AS note_line_count,
                   COALESCE((
                       SELECT GROUP_CONCAT(note.raw_line_text, ' | ')
                       FROM card_note_item_log note
                       WHERE note.parse_id = review.parse_id
                   ), '') AS evidence_preview
            FROM review_queue review
            LEFT JOIN parse_result parse ON parse.parse_id = review.parse_id
            LEFT JOIN photo_log photo ON photo.photo_id = parse.photo_id
            LEFT JOIN card_note_item_log review_note
                ON review_note.note_item_id = CASE
                    WHEN review.review_id LIKE 'review_unlabeled_numeric_note_%'
                        THEN SUBSTR(review.review_id, LENGTH('review_unlabeled_numeric_') + 1)
                    WHEN review.review_id LIKE 'review_ear_note_%'
                        THEN SUBSTR(review.review_id, LENGTH('review_ear_') + 1)
                    ELSE ''
                END
            LEFT JOIN card_snapshot review_snapshot
                ON review_snapshot.card_snapshot_id = review_note.card_snapshot_id
            ORDER BY review.created_at DESC
            """
        ).fetchall()
    result = []
    for row in rows:
        payload = dict(row)
        payload["image_url"] = f"/api/photos/{quote(payload['photo_id'])}/image" if payload.get("photo_id") else ""
        payload["review_note_summary"] = json_object(payload.pop("review_note_summary_json", "{}"))
        result.append(payload)
    return result


@app.post("/api/review-items/{review_id}/resolve")
def resolve_review_item(review_id: str, payload: ReviewResolutionCreate) -> dict[str, Any]:
    resolved_at = utc_now()
    allowed_legacy_decisions = {
        "resolve",
        "accept_legacy_candidate",
        "reject_legacy_candidate",
        "map_to_canonical_candidate",
    }
    legacy_decision = payload.legacy_decision.strip() or "resolve"
    if legacy_decision not in allowed_legacy_decisions:
        raise HTTPException(status_code=400, detail="Legacy decision must be resolve, accept, reject, or map.")
    legacy_status_by_decision = {
        "accept_legacy_candidate": "accepted",
        "reject_legacy_candidate": "rejected",
        "map_to_canonical_candidate": "mapped_candidate",
    }
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
        if existing["status"] == "resolved":
            raise HTTPException(status_code=409, detail="Review item is already resolved.")
        correction_id = None
        correction_identity_fields = [
            payload.correction_entity_type.strip(),
            payload.correction_entity_id.strip(),
            payload.correction_field_name.strip(),
        ]
        correction_fields = [
            *correction_identity_fields,
            payload.correction_before_value,
            payload.correction_after_value,
            payload.correction_source_record_id or "",
        ]
        if any(correction_fields) and not all(correction_identity_fields):
            raise HTTPException(
                status_code=400,
                detail="Correction entity type, entity id, and field name are required when recording a review correction.",
            )
        before = dict(existing)
        canonical_candidate_id = None
        note_label_update = None
        after = {
            "status": "resolved",
            "resolved_value": payload.resolved_value,
            "resolution_note": payload.resolution_note,
            "legacy_decision": legacy_decision,
            "canonical_entity_type": payload.canonical_entity_type,
            "canonical_entity_id": payload.canonical_entity_id,
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
        note_label_update = resolve_note_label_correction(
            conn,
            review_id=review_id,
            parse_id=existing["parse_id"],
            payload=payload,
            resolved_at=resolved_at,
        )
        legacy_row_review_status = None
        if legacy_decision in legacy_status_by_decision:
            legacy_row_review_status = legacy_status_by_decision[legacy_decision]
            legacy_row = conn.execute(
                """
                SELECT legacy_row_id, review_status
                FROM legacy_workbook_row
                WHERE review_id = ?
                """,
                (review_id,),
            ).fetchone()
            if legacy_row is not None:
                conn.execute(
                    """
                    UPDATE legacy_workbook_row
                    SET review_status = ?
                    WHERE legacy_row_id = ?
                    """,
                    (legacy_row_review_status, legacy_row["legacy_row_id"]),
                )
                conn.execute(
                    """
                    INSERT INTO action_log (action_id, action_type, target_id, before_value, after_value, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id("action"),
                        "legacy_workbook_row_reviewed",
                        legacy_row["legacy_row_id"],
                        json.dumps({"review_status": legacy_row["review_status"]}, ensure_ascii=False),
                        json.dumps(
                            {
                                "review_status": legacy_row_review_status,
                                "legacy_decision": legacy_decision,
                                "canonical_entity_type": payload.canonical_entity_type,
                                "canonical_entity_id": payload.canonical_entity_id,
                                "review_id": review_id,
                            },
                            ensure_ascii=False,
                        ),
                        resolved_at,
                    ),
                )
        if legacy_decision == "map_to_canonical_candidate":
            canonical_candidate_id = create_canonical_candidate_draft(
                conn,
                review_id=review_id,
                parse_id=existing["parse_id"],
                created_at=resolved_at,
            )
        if all(correction_identity_fields):
            correction_id = record_correction(
                conn,
                CorrectionCreate(
                    entity_type=payload.correction_entity_type,
                    entity_id=payload.correction_entity_id,
                    field_name=payload.correction_field_name,
                    before_value=payload.correction_before_value,
                    after_value=payload.correction_after_value or payload.resolved_value,
                    reason=payload.resolution_note,
                    source_record_id=payload.correction_source_record_id,
                    review_id=review_id,
                ),
                resolved_at,
            )
    return {
        "review_id": review_id,
        "status": "resolved",
        "resolved_at": resolved_at,
        "resolution_note": payload.resolution_note,
        "resolved_value": payload.resolved_value,
        "legacy_decision": legacy_decision,
        "legacy_row_review_status": legacy_row_review_status,
        "canonical_candidate_id": canonical_candidate_id,
        "correction_id": correction_id,
        "note_label_update": note_label_update,
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
                   parsed_metadata_json, confidence, needs_review, created_at
            FROM card_note_item_log
            ORDER BY parse_id, line_number
            """
        ).fetchall()
    result = []
    for row in rows:
        payload = dict(row)
        payload["parsed_metadata"] = json_object(payload.pop("parsed_metadata_json", "{}"))
        payload["display_value"] = (
            payload["parsed_metadata"].get("display_ko")
            if payload["parsed_type"] == "unlabeled_numeric_note"
            else payload["raw_line_text"]
        )
        result.append(payload)
    return result


@app.get("/api/card-snapshots")
def list_card_snapshots() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT snapshot.card_snapshot_id, snapshot.photo_id, snapshot.parse_id,
                   snapshot.card_type, snapshot.card_id_raw, snapshot.raw_strain_text,
                   snapshot.matched_strain_text, snapshot.sex_raw, snapshot.sex_normalized,
                   snapshot.sex_count_raw, snapshot.count_value, snapshot.dob_raw,
                   snapshot.dob_start, snapshot.dob_end, snapshot.mating_date_raw,
                   snapshot.mating_date_normalized, snapshot.lmo_raw, snapshot.note_summary_json,
                   snapshot.status, snapshot.source_layer, snapshot.confidence,
                   snapshot.created_at, snapshot.updated_at, photo.original_filename
            FROM card_snapshot snapshot
            LEFT JOIN photo_log photo ON photo.photo_id = snapshot.photo_id
            ORDER BY snapshot.updated_at DESC, snapshot.card_snapshot_id
            """
        ).fetchall()
    result = []
    for row in rows:
        payload = dict(row)
        payload["note_summary"] = json_object(payload.pop("note_summary_json", "{}"))
        payload["boundary"] = payload["source_layer"]
        result.append(payload)
    return result


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


def xlsx_column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def xlsx_cell_xml(row_number: int, column_number: int, value: Any, style_id: int = 0) -> str:
    ref = f"{xlsx_column_name(column_number)}{row_number}"
    text = html.escape("" if value is None else str(value), quote=False)
    style_attr = f' s="{style_id}"' if style_id else ""
    return f'<c r="{ref}"{style_attr} t="inlineStr"><is><t>{text}</t></is></c>'


def xlsx_sheet_xml(headers: list[str], rows: list[list[Any]], column_widths: list[int] | None = None) -> str:
    matrix = [headers, *rows]
    row_xml = []
    for row_index, values in enumerate(matrix, start=1):
        style_id = 1 if row_index == 1 else 0
        cells = "".join(
            xlsx_cell_xml(row_index, column_index, value, style_id)
            for column_index, value in enumerate(values, start=1)
        )
        row_xml.append(f'<row r="{row_index}">{cells}</row>')
    last_col = xlsx_column_name(max(len(headers), 1))
    last_row = max(len(matrix), 1)
    widths = column_widths or [max(12, min(35, len(str(header)) + 4)) for header in headers]
    cols_xml = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:{last_col}{last_row}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>{cols_xml}</cols>
  <sheetData>{''.join(row_xml)}</sheetData>
</worksheet>"""


def build_xlsx(
    sheet_name: str,
    headers: list[str],
    rows: list[list[Any]],
    trace_rows: list[list[Any]] | None = None,
    column_widths: list[int] | None = None,
) -> bytes:
    sheets = [
        {
            "name": sheet_name[:31] or "Sheet1",
            "xml": xlsx_sheet_xml(headers, rows, column_widths),
            "target": "worksheets/sheet1.xml",
        }
    ]
    if trace_rows:
        trace_headers = [
            "Row",
            "Source note",
            "Source record",
            "Boundary",
            "Export note",
            "Source photo",
            "Card snapshot",
            "Raw note line",
            "Uncertainty",
        ]
        sheets.append(
            {
                "name": "Export_Trace",
                "xml": xlsx_sheet_xml(trace_headers, trace_rows, [10, 28, 28, 24, 40, 26, 28, 42, 36]),
                "target": "worksheets/sheet2.xml",
            }
        )
    sheet_entries = "".join(
        f'<sheet name="{html.escape(sheet["name"], quote=True)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, sheet in enumerate(sheets, start=1)
    )
    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>{sheet_entries}</sheets>
</workbook>"""
    rel_entries = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="{sheet["target"]}"/>'
        for index, sheet in enumerate(sheets, start=1)
    )
    rel_entries += f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    workbook_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {rel_entries}
</Relationships>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
  <dxfs count="0"/>
  <tableStyles count="0" defaultTableStyle="TableStyleMedium9" defaultPivotStyle="PivotStyleLight16"/>
</styleSheet>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    sheet_overrides = "".join(
        f'<Override PartName="/xl/{sheet["target"]}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for sheet in sheets
    )
    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  {sheet_overrides}
</Types>"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as workbook:
        workbook.writestr("[Content_Types].xml", content_types)
        workbook.writestr("_rels/.rels", root_rels)
        workbook.writestr("xl/workbook.xml", workbook_xml)
        workbook.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        workbook.writestr("xl/styles.xml", styles_xml)
        for sheet in sheets:
            workbook.writestr(f"xl/{sheet['target']}", sheet["xml"])
    return output.getvalue()


def export_filename(export_kind: str, preview: dict[str, Any], query: str = "") -> str:
    if query.strip():
        strain = query.strip()
    elif export_kind == "animal":
        strain = next((row.get("strain") for row in preview["animal_sheet_rows"] if row.get("strain")), "selected strain")
    else:
        strain = next((row.get("strain") for row in preview["separation_rows"] if row.get("strain")), "selected strain")
    safe_strain = re.sub(r'[<>:"/\\|?*]+', " ", strain).strip() or "selected strain"
    safe_strain = re.sub(r"\s+", " ", safe_strain)
    date_label = utc_now()[:10].replace("-", "")
    suffix = "animal sheet" if export_kind == "animal" else "분리 현황표"
    return f"{date_label} {safe_strain} {suffix}.xlsx"


def trace_rows_from_export_rows(rows: list[dict[str, Any]], source_key: str) -> list[list[Any]]:
    trace_rows = []
    for index, row in enumerate(rows, start=2):
        source_value = row.get(source_key) or row.get("source") or ""
        trace_rows.append(
            [
                index,
                source_value,
                row.get("source_record_id", ""),
                "export or view",
                row.get("export_note", "Generated from accepted structured state."),
                row.get("source_photo_ids", "") or row.get("source_photo_id", ""),
                row.get("card_snapshot_ids", "") or row.get("card_snapshot_id", ""),
                row.get("raw_note_lines", "") or row.get("raw_note_line", ""),
                row.get("uncertainty", ""),
            ]
        )
    return trace_rows


def workbook_content_disposition(filename: str, fallback: str) -> str:
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


def log_workbook_export(
    export_type: str,
    filename: str,
    query: str,
    row_count: int,
    blocked_review_count: int,
    status: str,
) -> None:
    note = (
        "Blocked final XLSX export because open review items remain."
        if status == "blocked"
        else "XLSX generated from workbook preview."
    )
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO export_log
                (export_id, export_type, filename, query, row_count,
                 blocked_review_count, status, exported_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("export"),
                export_type,
                filename,
                query.strip(),
                row_count,
                blocked_review_count,
                status,
                utc_now(),
                note,
            ),
        )


def export_staleness(conn: Any) -> dict[str, Any]:
    latest_data_change = conn.execute(
        """
        SELECT MAX(changed_at) AS changed_at
        FROM (
            SELECT uploaded_at AS changed_at FROM photo_log
            UNION ALL SELECT parsed_at FROM parse_result
            UNION ALL SELECT created_at FROM review_queue
            UNION ALL SELECT resolved_at FROM review_queue WHERE resolved_at IS NOT NULL
            UNION ALL SELECT imported_at FROM source_record
            UNION ALL SELECT updated_at FROM strain_registry
            UNION ALL SELECT corrected_at FROM correction_log
            UNION ALL SELECT updated_at FROM card_snapshot
            UNION ALL SELECT created_at FROM mouse_event
            UNION ALL SELECT updated_at FROM genotyping_record
            UNION ALL SELECT updated_at FROM cage_registry
            UNION ALL SELECT assigned_at FROM mouse_cage_assignment
            UNION ALL SELECT ended_at FROM mouse_cage_assignment WHERE ended_at IS NOT NULL
            UNION ALL SELECT updated_at FROM mating_registry
            UNION ALL SELECT updated_at FROM litter_registry
            UNION ALL SELECT updated_at FROM mouse_master
            UNION ALL SELECT created_at FROM action_log
        )
        """
    ).fetchone()["changed_at"]
    latest_generated_export = conn.execute(
        """
        SELECT MAX(exported_at) AS exported_at
        FROM export_log
        WHERE status = 'generated'
        """
    ).fetchone()["exported_at"]
    return {
        "latest_data_change_at": latest_data_change or "",
        "latest_generated_export_at": latest_generated_export or "",
        "export_stale": bool(latest_data_change and (not latest_generated_export or latest_data_change > latest_generated_export)),
    }


def open_review_blockers(conn: Any, limit: int = 10) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT review.review_id, review.parse_id, review.severity, review.issue,
               review.suggested_value, review.review_reason, review.created_at,
               parse.source_name, parse.photo_id, photo.original_filename,
               (
                   SELECT COUNT(*)
                   FROM card_note_item_log note
                   WHERE note.parse_id = review.parse_id
               ) AS note_line_count,
               COALESCE((
                   SELECT GROUP_CONCAT(note.raw_line_text, ' | ')
                   FROM card_note_item_log note
                   WHERE note.parse_id = review.parse_id
               ), '') AS evidence_preview
        FROM review_queue review
        LEFT JOIN parse_result parse ON parse.parse_id = review.parse_id
        LEFT JOIN photo_log photo ON photo.photo_id = parse.photo_id
        WHERE review.status = 'open'
        ORDER BY review.severity DESC, review.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/mice")
def list_mice(query: str = "") -> list[dict[str, Any]]:
    with connection() as conn:
        rows = mouse_rows(conn, query)
    return [dict(row) for row in rows]


@app.get("/api/mice/{mouse_id}/audit-trace")
@app.get("/api/mice/{mouse_id}/audit-trail")
def mouse_audit_trace(mouse_id: str) -> dict[str, Any]:
    with connection() as conn:
        mouse = conn.execute(
            f"""
            {MOUSE_SELECT}
            WHERE mouse_id = ?
            """,
            (mouse_id,),
        ).fetchone()
        if mouse is None:
            raise HTTPException(status_code=404, detail="Mouse not found.")

        note_items = conn.execute(
            """
            SELECT note_item_id, photo_id, parse_id, line_number, raw_line_text,
                   strike_status, parsed_type, interpreted_status,
                   parsed_ear_label_raw, parsed_ear_label_code,
                   parsed_ear_label_review_status, confidence, needs_review, created_at
            FROM card_note_item_log
            WHERE note_item_id = ?
               OR parsed_mouse_display_id = ?
            ORDER BY created_at, line_number
            """,
            (mouse["source_note_item_id"], mouse["display_id"]),
        ).fetchall()
        parse_ids = sorted({row["parse_id"] for row in note_items if row["parse_id"]})

        event_rows = conn.execute(
            """
            SELECT event_id, event_type, event_date, related_entity_type,
                   related_entity_id, source_record_id, details, created_by, created_at
            FROM mouse_event
            WHERE mouse_id = ?
            ORDER BY event_date, created_at, event_id
            """,
            (mouse_id,),
        ).fetchall()
        correction_rows = conn.execute(
            """
            SELECT correction_id, entity_type, entity_id, field_name,
                   before_value, after_value, reason, source_record_id,
                   review_id, corrected_at
            FROM correction_log
            WHERE entity_type = 'mouse' AND entity_id IN (?, ?)
            ORDER BY corrected_at, correction_id
            """,
            (mouse_id, mouse["display_id"]),
        ).fetchall()
        genotype_rows = conn.execute(
            """
            SELECT genotyping_id, sample_id, sample_date, submitted_date, result_date,
                   target_name, raw_result, normalized_result, result_status, source_photo_id,
                   confidence, notes, created_at
            FROM genotyping_record
            WHERE mouse_id = ? OR sample_id IN (?, ?)
            ORDER BY created_at, genotyping_id
            """,
            (mouse_id, mouse["sample_id"] or "", mouse["display_id"]),
        ).fetchall()
        cage_assignment_rows = conn.execute(
            """
            SELECT a.assignment_id, a.cage_id, c.cage_label, c.location,
                   a.status, a.assigned_at, a.ended_at, a.source_record_id, a.note
            FROM mouse_cage_assignment a
            JOIN cage_registry c ON c.cage_id = a.cage_id
            WHERE a.mouse_id = ?
            ORDER BY a.assigned_at, a.assignment_id
            """,
            (mouse_id,),
        ).fetchall()

        action_target_ids = {mouse_id, mouse["display_id"]}
        if mouse["litter_id"]:
            action_target_ids.add(mouse["litter_id"])
        action_target_ids = {target_id for target_id in action_target_ids if target_id}
        action_rows = []
        if action_target_ids:
            placeholders = ", ".join("?" for _ in action_target_ids)
            action_rows = conn.execute(
                f"""
                SELECT action_id, action_type, target_id, before_value, after_value, created_at
                FROM action_log
                WHERE target_id IN ({placeholders})
                ORDER BY created_at, action_id
                """,
                sorted(action_target_ids),
            ).fetchall()

        father = (
            conn.execute(f"{MOUSE_SELECT} WHERE mouse_id = ?", (mouse["father_id"],)).fetchone()
            if mouse["father_id"]
            else None
        )
        mother = (
            conn.execute(f"{MOUSE_SELECT} WHERE mouse_id = ?", (mouse["mother_id"],)).fetchone()
            if mouse["mother_id"]
            else None
        )
        litter = (
            conn.execute(
                """
                SELECT l.litter_id, l.litter_label, l.mating_id, m.mating_label,
                       l.birth_date, l.number_born, l.number_alive, l.number_weaned,
                       l.weaning_date, l.status, l.source_record_id
                FROM litter_registry l
                LEFT JOIN mating_registry m ON m.mating_id = l.mating_id
                WHERE l.litter_id = ?
                """,
                (mouse["litter_id"],),
            ).fetchone()
            if mouse["litter_id"]
            else None
        )

        display_like = f"%{mouse['display_id']}%"
        mouse_id_like = f"%{mouse_id}%"
        review_clause = """
            (current_value LIKE ? OR suggested_value LIKE ? OR review_reason LIKE ?
             OR issue LIKE ? OR parse_id LIKE ?
             OR current_value LIKE ? OR suggested_value LIKE ? OR review_reason LIKE ?
             OR issue LIKE ? OR parse_id LIKE ?)
        """
        review_clauses = [review_clause]
        review_params: list[Any] = [display_like] * 5 + [mouse_id_like] * 5
        if parse_ids:
            placeholders = ", ".join("?" for _ in parse_ids)
            review_clauses.append(f"parse_id IN ({placeholders})")
            review_params.extend(parse_ids)
        review_rows = conn.execute(
            f"""
            SELECT review_id, parse_id, severity, issue, current_value,
                   suggested_value, review_reason, status, created_at,
                   resolved_at, resolution_note
            FROM review_queue
            WHERE {' OR '.join(review_clauses)}
            ORDER BY created_at, review_id
            """,
            review_params,
        ).fetchall()

        source_ids = {
            mouse["source_record_id"],
            *[row["source_record_id"] for row in event_rows],
            *[row["source_record_id"] for row in correction_rows],
            *[row["source_record_id"] for row in cage_assignment_rows],
            litter["source_record_id"] if litter else None,
        }
        source_ids = {source_id for source_id in source_ids if source_id}
        source_rows = []
        if source_ids:
            placeholders = ", ".join("?" for _ in source_ids)
            source_rows = conn.execute(
                f"""
                SELECT source_record_id, source_type, source_uri, source_label,
                       checksum, note, imported_at
                FROM source_record
                WHERE source_record_id IN ({placeholders})
                ORDER BY imported_at, source_record_id
                """,
                sorted(source_ids),
            ).fetchall()

    timeline = []
    for row in note_items:
        timeline.append(
            {
                "category": "note_line",
                "at": row["created_at"],
                "title": f"Note line {row['line_number'] or ''}".strip(),
                "evidence_id": row["note_item_id"],
                "source_record_id": None,
                "details": {
                    "raw_line_text": row["raw_line_text"],
                    "strike_status": row["strike_status"],
                    "interpreted_status": row["interpreted_status"],
                    "ear_label_raw": row["parsed_ear_label_raw"],
                    "ear_label_code": row["parsed_ear_label_code"],
                    "review_status": row["parsed_ear_label_review_status"],
                },
            }
        )
    for row in event_rows:
        timeline.append(
            {
                "category": "mouse_event",
                "at": row["event_date"],
                "title": row["event_type"],
                "evidence_id": row["event_id"],
                "source_record_id": row["source_record_id"],
                "details": {
                    "related": ":".join([row["related_entity_type"] or "", row["related_entity_id"] or ""]).strip(":"),
                    "details": json_object(row["details"]),
                    "created_by": row["created_by"],
                },
            }
        )
    for row in cage_assignment_rows:
        timeline.append(
            {
                "category": "cage_assignment",
                "at": row["assigned_at"],
                "title": f"{row['status']} cage {row['cage_label']}",
                "evidence_id": row["assignment_id"],
                "source_record_id": row["source_record_id"],
                "details": {
                    "cage_id": row["cage_id"],
                    "location": row["location"],
                    "ended_at": row["ended_at"],
                    "note": row["note"],
                },
            }
        )
    for row in review_rows:
        timeline.append(
            {
                "category": "review",
                "at": row["created_at"],
                "title": row["issue"],
                "evidence_id": row["review_id"],
                "source_record_id": None,
                "details": {
                    "status": row["status"],
                    "severity": row["severity"],
                    "current_value": row["current_value"],
                    "suggested_value": row["suggested_value"],
                    "resolution_note": row["resolution_note"],
                },
            }
        )
    for row in correction_rows:
        timeline.append(
            {
                "category": "correction",
                "at": row["corrected_at"],
                "title": row["field_name"],
                "evidence_id": row["correction_id"],
                "source_record_id": row["source_record_id"],
                "details": {
                    "before": row["before_value"],
                    "after": row["after_value"],
                    "reason": row["reason"],
                    "review_id": row["review_id"],
                },
            }
        )
    for row in genotype_rows:
        timeline.append(
            {
                "category": "genotyping",
                "at": row["result_date"] or row["submitted_date"] or row["sample_date"] or row["created_at"],
                "title": row["result_status"],
                "evidence_id": row["genotyping_id"],
                "source_record_id": None,
                "details": {
                    "sample_id": row["sample_id"],
                    "target_name": row["target_name"],
                    "raw_result": row["raw_result"],
                    "normalized_result": row["normalized_result"],
                    "confidence": row["confidence"],
                    "notes": row["notes"],
                },
            }
        )
    for row in action_rows:
        timeline.append(
            {
                "category": "action_log",
                "at": row["created_at"],
                "title": row["action_type"],
                "evidence_id": row["action_id"],
                "source_record_id": None,
                "details": {
                    "target_id": row["target_id"],
                    "before": json_object(row["before_value"]),
                    "after": json_object(row["after_value"]),
                },
            }
        )
    timeline.sort(key=lambda item: (item["at"] or "", item["category"], item["evidence_id"] or ""))

    return {
        "source_layer": "export or view",
        "mouse": dict(mouse),
        "lineage": {
            "father": dict(father) if father else None,
            "mother": dict(mother) if mother else None,
            "litter": dict(litter) if litter else None,
        },
        "source_records": [dict(row) for row in source_rows],
        "note_items": [dict(row) for row in note_items],
        "review_items": [dict(row) for row in review_rows],
        "corrections": [dict(row) for row in correction_rows],
        "events": [dict(row) | {"details": json_object(row["details"])} for row in event_rows],
        "cage_assignments": [dict(row) for row in cage_assignment_rows],
        "actions": [dict(row) for row in action_rows],
        "genotyping_records": [dict(row) for row in genotype_rows],
        "timeline": timeline,
    }


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


@app.get("/api/evidence-reconciliation")
def evidence_reconciliation() -> dict[str, Any]:
    with connection() as conn:
        photo_summary = conn.execute(
            """
            SELECT COUNT(*) AS total_photos,
                   SUM(CASE WHEN status = 'review_pending' THEN 1 ELSE 0 END) AS review_pending_photos,
                   MAX(uploaded_at) AS latest_photo_uploaded_at
            FROM photo_log
            """
        ).fetchone()
        photo_review_summary = conn.execute(
            """
            SELECT COUNT(*) AS photo_review_candidates,
                   SUM(CASE WHEN review.status = 'open' THEN 1 ELSE 0 END) AS open_photo_reviews
            FROM parse_result parse
            LEFT JOIN review_queue review ON review.parse_id = parse.parse_id
            WHERE parse.source_name = 'photo_manual_review'
            """
        ).fetchone()
        manual_transcription_summary = conn.execute(
            """
            SELECT COUNT(*) AS manual_transcriptions,
                   SUM(CASE WHEN review.status = 'open' THEN 1 ELSE 0 END) AS open_manual_transcription_reviews
            FROM parse_result parse
            LEFT JOIN review_queue review ON review.parse_id = parse.parse_id
            WHERE parse.source_name IN ('manual_photo_transcription', 'ai_photo_extraction')
            """
        ).fetchone()
        legacy_summary = conn.execute(
            """
            SELECT COUNT(DISTINCT legacy.legacy_import_id) AS legacy_imports,
                   COUNT(row.legacy_row_id) AS legacy_rows,
                   MAX(legacy.imported_at) AS latest_legacy_imported_at
            FROM legacy_workbook_import legacy
            LEFT JOIN legacy_workbook_row row ON row.legacy_import_id = legacy.legacy_import_id
            """
        ).fetchone()
        canonical_summary = conn.execute(
            """
            SELECT COUNT(*) AS accepted_mice,
                   SUM(CASE WHEN source_record_id IS NOT NULL OR source_note_item_id IS NOT NULL OR source_photo_id IS NOT NULL THEN 1 ELSE 0 END)
                       AS mice_with_evidence
            FROM mouse_master
            """
        ).fetchone()
        open_reviews = conn.execute(
            "SELECT COUNT(*) AS count FROM review_queue WHERE status = 'open'"
        ).fetchone()["count"]

    total_photos = int(photo_summary["total_photos"] or 0)
    photo_review_candidates = int(photo_review_summary["photo_review_candidates"] or 0)
    open_photo_reviews = int(photo_review_summary["open_photo_reviews"] or 0)
    manual_transcriptions = int(manual_transcription_summary["manual_transcriptions"] or 0)
    open_manual_transcription_reviews = int(manual_transcription_summary["open_manual_transcription_reviews"] or 0)
    legacy_rows = int(legacy_summary["legacy_rows"] or 0)
    accepted_mice = int(canonical_summary["accepted_mice"] or 0)
    mice_with_evidence = int(canonical_summary["mice_with_evidence"] or 0)
    return {
        "boundary": "export or view",
        "source_priority": ["raw source photo", "reviewed note line", "predecessor Excel view"],
        "total_photos": total_photos,
        "photo_review_candidates": photo_review_candidates,
        "photos_missing_review_candidates": max(total_photos - photo_review_candidates, 0),
        "open_photo_reviews": open_photo_reviews,
        "manual_transcriptions": manual_transcriptions,
        "open_manual_transcription_reviews": open_manual_transcription_reviews,
        "legacy_imports": int(legacy_summary["legacy_imports"] or 0),
        "legacy_rows": legacy_rows,
        "accepted_mice": accepted_mice,
        "mice_with_evidence": mice_with_evidence,
        "open_reviews": int(open_reviews or 0),
        "latest_photo_uploaded_at": photo_summary["latest_photo_uploaded_at"] or "",
        "latest_legacy_imported_at": legacy_summary["latest_legacy_imported_at"] or "",
        "ready_for_comparison": total_photos > 0 and legacy_rows > 0,
        "comparison_rows": [
            {
                "check": "Latest photo evidence",
                "status": "ready" if total_photos else "missing",
                "detail": f"{total_photos} photo(s), {open_photo_reviews} open manual review(s)",
            },
            {
                "check": "Predecessor Excel view",
                "status": "ready" if legacy_rows else "missing",
                "detail": f"{legacy_rows} candidate row(s) across {int(legacy_summary['legacy_imports'] or 0)} import(s)",
            },
            {
                "check": "Manual photo transcription",
                "status": "ready" if manual_transcriptions else "pending",
                "detail": f"{manual_transcriptions} transcription(s), {open_manual_transcription_reviews} open review(s)",
            },
            {
                "check": "Canonical acceptance",
                "status": "blocked" if open_reviews else "ready",
                "detail": f"{accepted_mice} accepted mouse row(s), {mice_with_evidence} with source evidence",
            },
        ],
        "next_action": (
            "Review latest photo cards and resolve blockers before treating Excel differences as accepted state."
            if open_reviews
            else "Comparison view is clear of open review blockers."
        ),
    }


@app.get("/api/evidence-comparison")
def evidence_comparison() -> dict[str, Any]:
    with connection() as conn:
        return build_evidence_comparison_payload(conn)


@app.post("/api/evidence-comparison/review-candidates")
def create_evidence_comparison_reviews() -> dict[str, Any]:
    created = 0
    existing = 0
    skipped = 0
    review_ids: list[str] = []
    now = utc_now()
    with connection() as conn:
        payload = build_evidence_comparison_payload(conn)
        for comparison in payload["comparisons"]:
            if not comparison.get("review_required"):
                skipped += 1
                continue
            review_id = str(comparison.get("review_id") or "")
            current = conn.execute(
                "SELECT review_id FROM review_queue WHERE review_id = ?",
                (review_id,),
            ).fetchone()
            if current is not None:
                existing += 1
                review_ids.append(review_id)
                continue
            manual = comparison.get("manual_summary") or {}
            legacy = comparison.get("legacy_candidate") or {}
            legacy_summary = legacy.get("summary") or {}
            current_value = json.dumps(
                {
                    "manual": manual,
                    "legacy": {
                        "legacy_row_id": legacy.get("legacy_row_id"),
                        "source_file_name": legacy.get("source_file_name"),
                        "source_row_number": legacy.get("source_row_number"),
                        "summary": legacy_summary,
                    },
                    "status": comparison.get("status"),
                },
                ensure_ascii=False,
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value, suggested_value,
                     review_reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    comparison["manual_parse_id"],
                    "High" if comparison["status"] == "value_mismatch" else "Medium",
                    (
                        "Photo transcription differs from predecessor Excel"
                        if comparison["status"] == "value_mismatch"
                        else "Photo transcription missing predecessor Excel match"
                    ),
                    current_value,
                    "Resolve the latest photo transcription against the predecessor Excel candidate before export.",
                    (
                        f"{comparison.get('detail') or 'Manual photo transcription requires predecessor Excel comparison review.'} "
                        "This is a review item from an export/view comparison; do not write canonical mouse state "
                        "until a reviewer resolves the source photo and predecessor Excel evidence."
                    ),
                    "open",
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
                    "evidence_comparison_review_created",
                    review_id,
                    None,
                    json.dumps(
                        {
                            "manual_parse_id": comparison["manual_parse_id"],
                            "legacy_row_id": legacy.get("legacy_row_id") or "no_legacy_candidate",
                            "comparison_status": comparison["status"],
                            "boundary": "review item",
                        },
                        ensure_ascii=False,
                    ),
                    now,
                ),
            )
            created += 1
            review_ids.append(review_id)
    return {
        "boundary": "review item",
        "created_review_candidates": created,
        "existing_review_candidates": existing,
        "skipped_exact_matches": skipped,
        "created_review_items": created,
        "existing_review_items": existing,
        "skipped_comparisons": skipped,
        "review_ids": review_ids,
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
                "review_blockers": open_review_blockers(conn),
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


@app.get("/api/exports/separation.xlsx")
def export_separation_xlsx(query: str = "", require_ready: bool = True) -> Response:
    preview = export_preview()
    filtered_rows = [
        row
        for row in preview["separation_rows"]
        if not query.strip() or query.strip().lower() in row["strain"].lower()
    ]
    rows = [
        [
            row["cage_number"],
            row["strain"],
            row["genotype"],
            row["total"],
            row["dob"],
            row["wt"],
            row["tg"],
            row["sampling_point"],
            row["source_note_item_ids"],
        ]
        for row in filtered_rows
    ]
    filename = export_filename("separation", preview, query)
    blocked_count = preview["blocked_review_items"]
    if require_ready and blocked_count:
        log_workbook_export("separation_xlsx", filename, query, len(rows), blocked_count, "blocked")
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Resolve open review items before final separation workbook export.",
                "blocked_review_count": blocked_count,
                "review_blockers": preview["review_blockers"],
                "filename": filename,
                "source_layer": "export or view",
            },
        )
    payload = build_xlsx(
        "분리 현황표",
        preview["separation_columns"],
        rows,
        trace_rows_from_export_rows(filtered_rows, "source_note_item_ids"),
        [14, 22, 22, 12, 18, 10, 10, 22, 32],
    )
    log_workbook_export("separation_xlsx", filename, query, len(rows), blocked_count, "generated")
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": workbook_content_disposition(filename, "separation.xlsx")},
    )


@app.get("/api/exports/animal-sheet.xlsx")
def export_animal_sheet_xlsx(query: str = "", require_ready: bool = True) -> Response:
    preview = export_preview()
    filtered_rows = [
        row
        for row in preview["animal_sheet_rows"]
        if not query.strip() or not row["strain"] or query.strip().lower() in row["strain"].lower()
    ]
    rows = [
        [
            row["cage_no"],
            row["strain"],
            row["sex"],
            row["mouse_id"],
            row["genotype"],
            row["dob"],
            row["mating_date"],
            row["pubs"],
            row["status"],
            row["source"],
        ]
        for row in filtered_rows
    ]
    filename = export_filename("animal", preview, query)
    blocked_count = preview["blocked_review_items"]
    if require_ready and blocked_count:
        log_workbook_export("animal_sheet_xlsx", filename, query, len(rows), blocked_count, "blocked")
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Resolve open review items before final animal sheet workbook export.",
                "blocked_review_count": blocked_count,
                "review_blockers": preview["review_blockers"],
                "filename": filename,
                "source_layer": "export or view",
            },
        )
    payload = build_xlsx(
        "animal sheet",
        preview["animal_sheet_columns"],
        rows,
        trace_rows_from_export_rows(filtered_rows, "source"),
        [10, 22, 10, 18, 16, 16, 16, 18, 16, 32],
    )
    log_workbook_export("animal_sheet_xlsx", filename, query, len(rows), blocked_count, "generated")
    return Response(
        content=payload,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": workbook_content_disposition(filename, "animal sheet.xlsx")},
    )


def compact_export_values(values: list[Any], limit: int = 3) -> str:
    seen: list[str] = []
    for value in values:
        text_value = str(value or "").strip()
        if text_value and text_value not in seen:
            seen.append(text_value)
    if len(seen) > limit:
        return f"{', '.join(seen[:limit])}, +{len(seen) - limit}"
    return ", ".join(seen)


def export_uncertainty_label(row: Any) -> str:
    status = str(row["ear_label_review_status"] or "").strip()
    if not status or status in {"auto_filled", "verified", "user_corrected"}:
        return ""
    raw_label = row["ear_label_raw"] or row["ear_label_code"] or "ear label"
    confidence = row["ear_label_confidence"]
    confidence_text = f"; confidence {confidence:.2f}" if isinstance(confidence, (int, float)) else ""
    return f"Ear label {raw_label}: {status}{confidence_text}"


def load_export_note_evidence(conn: Any, note_item_ids: list[str]) -> dict[str, dict[str, Any]]:
    note_item_ids = [note_id for note_id in dict.fromkeys(note_item_ids) if note_id]
    if not note_item_ids:
        return {}
    placeholders = ", ".join("?" for _ in note_item_ids)
    rows = conn.execute(
        f"""
        SELECT note.note_item_id, note.photo_id, photo.original_filename,
               note.card_snapshot_id, note.raw_line_text,
               note.parsed_ear_label_review_status, note.confidence
        FROM card_note_item_log note
        LEFT JOIN photo_log photo ON photo.photo_id = note.photo_id
        WHERE note.note_item_id IN ({placeholders})
        """,
        note_item_ids,
    ).fetchall()
    return {row["note_item_id"]: dict(row) for row in rows}


@app.get("/api/export-preview")
def export_preview() -> dict[str, Any]:
    with connection() as conn:
        photos = conn.execute("SELECT COUNT(*) AS count FROM photo_log").fetchone()["count"]
        review_rows = open_review_blockers(conn)
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
                   mouse.ear_label_code, mouse.ear_label_confidence,
                   mouse.ear_label_review_status, mouse.genotype, mouse.genotype_result,
                   mouse.dob_raw, mouse.dob_start, mouse.source_note_item_id,
                   mouse.current_card_snapshot_id, mouse.source_photo_id, mouse.source_record_id
            FROM mating_registry m
            LEFT JOIN mating_mouse mm ON mm.mating_id = m.mating_id AND mm.removed_date IS NULL
            LEFT JOIN mouse_master mouse ON mouse.mouse_id = mm.mouse_id
            ORDER BY m.created_at, m.mating_label COLLATE NOCASE,
                     CASE mm.role WHEN 'male' THEN 1 WHEN 'female' THEN 2 ELSE 3 END,
                     mouse.display_id COLLATE NOCASE
            LIMIT 120
            """
        ).fetchall()
        note_item_ids = [
            str(row["source_note_item_id"])
            for row in list(mice) + list(mating_rows)
            if row["source_note_item_id"]
        ]
        note_evidence = load_export_note_evidence(conn, note_item_ids)
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
        stale_state = export_staleness(conn)
    rows = []
    separation_groups: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for mouse in mice:
        sex = mouse["sex"] or ""
        sex_symbol = {"male": "\u2642", "female": "\u2640"}.get(sex.lower(), sex)
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
                "source_photo_ids": [],
                "card_snapshot_ids": [],
                "raw_note_lines": [],
                "uncertainties": [],
            }
        group = separation_groups[group_key]
        note_source = note_evidence.get(mouse["source_note_item_id"] or "", {})
        source_photo_id = mouse["source_photo_id"] or note_source.get("photo_id") or ""
        card_snapshot_id = mouse["current_card_snapshot_id"] or note_source.get("card_snapshot_id") or ""
        raw_note_line = note_source.get("raw_line_text") or ""
        uncertainty = export_uncertainty_label(mouse)
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
        if source_photo_id:
            group["source_photo_ids"].append(source_photo_id)
        if card_snapshot_id:
            group["card_snapshot_ids"].append(card_snapshot_id)
        if raw_note_line:
            group["raw_note_lines"].append(raw_note_line)
        if uncertainty:
            group["uncertainties"].append(uncertainty)
        rows.append(
            {
                "mouse_id": mouse["mouse_id"],
                "display_id": mouse["display_id"],
                "strain": mouse["raw_strain_text"] or "",
                "genotype": mouse["genotype_result"] or mouse["genotype"] or "",
                "dob": mouse["dob_raw"] or mouse["dob_start"] or "",
                "ear_label": mouse["ear_label_raw"] or mouse["ear_label_code"] or "",
                "ear_label_code": mouse["ear_label_code"] or "",
                "ear_label_confidence": mouse["ear_label_confidence"],
                "ear_label_review_status": mouse["ear_label_review_status"] or "",
                "status": mouse["status"],
                "current_cage": mouse["current_cage_label"] or "",
                "next_action": mouse["next_action"],
                "source_note_item_id": mouse["source_note_item_id"] or "",
                "source_photo_id": source_photo_id,
                "source_photo_filename": note_source.get("original_filename") or "",
                "card_snapshot_id": card_snapshot_id,
                "raw_note_line": raw_note_line,
                "uncertainty": uncertainty,
                "source_evidence": compact_export_values(
                    [
                        mouse["source_note_item_id"] and f"note {mouse['source_note_item_id']}",
                        source_photo_id and f"photo {source_photo_id}",
                        card_snapshot_id and f"snapshot {card_snapshot_id}",
                    ],
                    limit=4,
                ),
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
                "source_record_id": compact_export_values(group["source_record_ids"]),
                "source_photo_ids": compact_export_values(group["source_photo_ids"]),
                "card_snapshot_ids": compact_export_values(group["card_snapshot_ids"]),
                "raw_note_lines": compact_export_values(group["raw_note_lines"], limit=2),
                "uncertainty": compact_export_values(group["uncertainties"], limit=2),
                "export_note": "Grouped from source-backed mouse records; raw note/photo evidence is on this trace sheet.",
            }
        )
    litter_by_mating: dict[str, list[Any]] = {}
    for litter in litter_rows:
        litter_by_mating.setdefault(litter["mating_id"], []).append(litter)
    mating_groups: dict[str, dict[str, Any]] = {}
    for mating in mating_rows:
        mating_id = mating["mating_id"]
        if mating_id not in mating_groups:
            mating_groups[mating_id] = {"mating": mating, "parents": []}
        if mating["display_id"]:
            mating_groups[mating_id]["parents"].append(mating)
    animal_rows = []
    for cage_no, group in enumerate(mating_groups.values(), start=1):
        mating = group["mating"]
        for index, parent in enumerate(group["parents"]):
            sex_value = {"male": "\u2642", "female": "\u2640"}.get(
                (parent["sex"] or "").lower(), parent["sex"] or parent["role"] or ""
            )
            mouse_label = " ".join([parent["display_id"] or "", parent["ear_label_raw"] or ""]).strip()
            note_source = note_evidence.get(parent["source_note_item_id"] or "", {})
            parent_photo_id = parent["source_photo_id"] or note_source.get("photo_id") or ""
            parent_snapshot_id = parent["current_card_snapshot_id"] or note_source.get("card_snapshot_id") or ""
            animal_rows.append(
                {
                    "cage_no": str(cage_no) if index == 0 else "",
                    "strain": mating["strain_goal"] or "",
                    "sex": sex_value,
                    "mouse_id": mouse_label,
                    "genotype": parent["genotype_result"] or parent["genotype"] or mating["expected_genotype"] or "",
                    "dob": parent["dob_raw"] or parent["dob_start"] or "",
                    "mating_date": mating["start_date"] if index == 0 else "",
                    "pubs": "",
                    "status": mating["mating_status"] or "",
                    "source": parent["source_note_item_id"] or parent["source_record_id"] or "",
                    "source_note_item_ids": parent["source_note_item_id"] or "",
                    "source_record_id": parent["source_record_id"] or "",
                    "source_photo_ids": parent_photo_id,
                    "card_snapshot_ids": parent_snapshot_id,
                    "raw_note_lines": note_source.get("raw_line_text") or "",
                    "uncertainty": export_uncertainty_label(parent),
                    "export_note": "Parent row generated from accepted mating state; source note/photo evidence is on this trace sheet.",
                }
            )
        for litter_index, litter in enumerate(litter_by_mating.get(mating["mating_id"], []), start=1):
            born_count = litter["number_alive"] if litter["number_alive"] is not None else litter["number_born"]
            animal_rows.append(
                {
                    "cage_no": "",
                    "strain": "",
                    "sex": f"F{litter_index}",
                    "mouse_id": f"{born_count or ''}p".strip(),
                    "genotype": litter["status"] or "",
                    "dob": litter["birth_date"] or "",
                    "mating_date": "",
                    "pubs": f"{litter['birth_date']} {litter['number_born']}p".strip() if litter["number_born"] else "",
                    "status": litter["status"] or "",
                    "source": litter["source_record_id"] or "",
                    "source_record_id": litter["source_record_id"] or "",
                    "source_note_item_ids": "",
                    "source_photo_ids": "",
                    "card_snapshot_ids": "",
                    "raw_note_lines": "",
                    "uncertainty": "",
                    "export_note": "Litter row generated from accepted litter state.",
                }
            )
    return {
        "source_layer": "export or view",
        "export_type": "separation_preview",
        "expected_filename": "mouse_records_preview.csv",
        **stale_state,
        "expected_separation_filename": export_filename(
            "separation",
            {"separation_rows": separation_rows, "animal_sheet_rows": animal_rows},
        ),
        "expected_animal_sheet_filename": export_filename(
            "animal",
            {"separation_rows": separation_rows, "animal_sheet_rows": animal_rows},
        ),
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
