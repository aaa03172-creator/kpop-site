from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
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


@app.post("/api/photos")
def upload_photo(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    photo_id = new_id("photo")
    stored_path = save_upload(file, photo_id)
    uploaded_at = utc_now()
    try:
        with connection() as conn:
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

    return {"imported_parse_results": imported, "created_or_updated_review_items": reviews}
