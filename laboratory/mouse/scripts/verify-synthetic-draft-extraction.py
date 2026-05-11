from __future__ import annotations

import argparse
from contextlib import closing
import gc
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import normalize_ai_draft_payload  # noqa: E402
from scripts.generate_synthetic_cage_card_fixtures import generate  # noqa: E402


SOURCE_POLICY = (
    "Local-only synthetic draft extraction. Do not send generated images, "
    "draft payloads, or source records to external OCR, LLM, or inference services."
)


def remove_tree_with_retries(path: Path, attempts: int = 5) -> None:
    gc.collect()
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.2 * (attempt + 1))
            gc.collect()


def parse_json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    return value if isinstance(value, dict) else {}


def draft_from_fixture_row(row: sqlite3.Row, note_rows: list[sqlite3.Row]) -> dict[str, Any]:
    raw_payload = parse_json_object(row["raw_payload"])
    notes = []
    uncertain_fields = list(raw_payload.get("uncertainFields") or [])
    for note in note_rows:
        raw_line = str(note["raw_line_text"] or "").strip()
        if not raw_line:
            continue
        needs_review = bool(note["needs_review"])
        if needs_review and "notes" not in uncertain_fields:
            uncertain_fields.append("notes")
        notes.append(
            {
                "raw": raw_line,
                "meaning": "reviewable_note" if needs_review else "mouse_or_note_line",
                "strike": "none",
                "confidence": float(note["confidence"] or row["confidence"] or 0),
            }
        )
    visible_lines = [
        f"Strain: {raw_payload.get('rawStrain') or ''}".strip(),
        f"Sex: {raw_payload.get('sexRaw') or ''}".strip(),
        f"Count: {raw_payload.get('mouseCount') or ''}".strip(),
        *[str(note["raw_line_text"] or "").strip() for note in note_rows],
    ]
    card_type = "Mating" if "/" in str(raw_payload.get("sexRaw") or "") else "Separated"
    return {
        "card_type": card_type,
        "raw_strain": str(raw_payload.get("rawStrain") or ""),
        "matched_strain": str(raw_payload.get("rawStrain") or ""),
        "sex_raw": str(raw_payload.get("sexRaw") or ""),
        "id_raw": "",
        "dob_raw": "",
        "dob_normalized": "",
        "mating_date_raw": "",
        "mating_date_normalized": "",
        "lmo_raw": "",
        "mouse_count": str(raw_payload.get("mouseCount") or ""),
        "notes": notes,
        "raw_visible_text_lines": [line for line in visible_lines if line and not line.endswith(":")],
        "symbol_confusions": [],
        "confidence": float(row["confidence"] or 0),
        "uncertain_fields": uncertain_fields,
        "reviewer_note": "Local synthetic OCR surrogate draft; no external inference used.",
    }


def attention_from_draft(draft: dict[str, Any]) -> str:
    if float(draft.get("confidence") or 0) <= 55:
        return "must_review"
    if draft.get("uncertain_fields") or draft.get("plausibility_findings"):
        return "quick_check"
    return "trace_only"


def verify_generated_drafts(generated: dict[str, Any]) -> dict[str, Any]:
    db_path = Path(generated["database"])
    manifest = json.loads(Path(generated["manifest"]).read_text(encoding="utf-8"))
    case_ids_by_photo = {
        str(case.get("photo_id") or ""): str(case.get("case_id") or "")
        for case in manifest.get("cases", [])
        if case.get("photo_id") and case.get("case_id")
    }
    results = []
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        parse_rows = conn.execute(
            """
            SELECT parse.parse_id, parse.photo_id, parse.raw_payload, parse.confidence,
                   photo.original_filename
            FROM parse_result parse
            JOIN photo_log photo ON photo.photo_id = parse.photo_id
            WHERE parse.source_name = 'synthetic_photo_fixture'
            ORDER BY parse.parse_id
            """
        ).fetchall()
        for row in parse_rows:
            note_rows = conn.execute(
                """
                SELECT raw_line_text, confidence, needs_review
                FROM card_note_item_log
                WHERE parse_id = ?
                ORDER BY line_number
                """,
                (row["parse_id"],),
            ).fetchall()
            draft = draft_from_fixture_row(row, note_rows)
            normalized = normalize_ai_draft_payload(draft)
            attention_level = attention_from_draft(normalized)
            failures = []
            if not row["photo_id"]:
                failures.append("missing source photo id")
            if not str(row["original_filename"] or "").endswith(".jpg"):
                failures.append("source photo is not a synthetic JPEG")
            if attention_level not in {"must_review", "quick_check", "trace_only"}:
                failures.append(f"unexpected attention level {attention_level!r}")
            results.append(
                {
                    "case_id": case_ids_by_photo.get(row["photo_id"], row["photo_id"]),
                    "source_photo_id": row["photo_id"],
                    "photo_filename": row["original_filename"],
                    "draft_boundary": "parsed or intermediate result",
                    "attention_level": attention_level,
                    "confidence": normalized["confidence"],
                    "uncertain_fields": normalized["uncertain_fields"],
                    "canonical_write": False,
                    "external_inference_used": False,
                    "source_evidence": {
                        "photo_id": row["photo_id"],
                        "photo_filename": row["original_filename"],
                        "boundary": "raw source / test fixture",
                        "note_lines": [str(note["raw_line_text"] or "") for note in note_rows],
                    },
                    "failures": failures,
                    "status": "PASS" if not failures else "FAIL",
                }
            )
    failed = len([result for result in results if result["status"] != "PASS"])
    return {
        "passed": len(results) - failed,
        "failed": failed,
        "case_count": len(results),
        "draft_boundary": "parsed or intermediate result",
        "external_inference_used": False,
        "canonical_writes": 0,
        "reviewable_cases": len(
            [result for result in results if result["attention_level"] in {"must_review", "quick_check"}]
        ),
        "trace_only_cases": len([result for result in results if result["attention_level"] == "trace_only"]),
        "results": results,
    }


def verify(output_dir: Path) -> dict[str, Any]:
    generated = generate(output_dir)
    verification = verify_generated_drafts(generated)
    return {
        "boundary": "review item / test fixture",
        "canonical": False,
        "source_policy": SOURCE_POLICY,
        "generated": generated,
        "verification": {key: value for key, value in verification.items() if key != "results"},
        "results": verification["results"],
        "exit_code": 1 if verification["failed"] else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify local synthetic cage-card draft extraction.")
    parser.add_argument("--output-dir", default="", help="Directory for generated disposable fixtures.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    temp_dir = None
    output_dir = Path(args.output_dir) if args.output_dir else Path(tempfile.mkdtemp(prefix="synthetic-draft-"))
    if not args.output_dir:
        temp_dir = output_dir
    try:
        summary = verify(output_dir)
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            verification = summary["verification"]
            print(
                "Synthetic draft extraction: "
                f"{verification['passed']}/{verification['case_count']} passed, "
                f"{verification['failed']} failed"
            )
        return int(summary["exit_code"])
    finally:
        if temp_dir is not None and temp_dir.exists():
            remove_tree_with_retries(temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
