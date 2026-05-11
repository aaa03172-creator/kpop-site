from __future__ import annotations

import argparse
import html
import json
import sqlite3
from pathlib import Path
from typing import Any


SOURCE_POLICY = (
    "Synthetic cage-card fixtures are local-only review test data. "
    "Do not send synthetic validation payloads to external services."
)

CASES: list[dict[str, Any]] = [
    {
        "case_id": "synthetic_clear_card",
        "coverage_tags": ["clear"],
        "photo_id": "synthetic_photo_clear",
        "photo_filename": "synthetic_clear_card.svg",
        "purpose": "A clear separated-card style fixture should parse without high-risk ambiguity.",
        "confidence": 88,
        "raw_payload": {
            "rawStrain": "B6J",
            "sexRaw": "M 3",
            "mouseCount": "3",
            "uncertainFields": [],
            "confidence": 88,
        },
        "expected_parse": {
            "status": "review",
            "min_confidence": 80,
            "field_contains": {"rawStrain": ["B6J"], "mouseCount": ["3"]},
        },
        "note_items": [
            {"raw_line_text": "101 R'", "parsed_ear_label_code": "R_PRIME", "parsed_ear_label_review_status": "auto_filled"},
            {"raw_line_text": "102 L'", "parsed_ear_label_code": "L_PRIME", "parsed_ear_label_review_status": "auto_filled"},
        ],
        "review": {
            "severity": "Low",
            "issue": "AI-extracted photo transcription needs review",
            "review_reason": "Synthetic clear card retained as traceable fixture review.",
            "attention_levels_include": ["trace_only"],
            "targets_include": ["Source photo"],
        },
    },
    {
        "case_id": "synthetic_low_confidence_blurry_card",
        "coverage_tags": ["low_confidence", "cropped_or_blurry"],
        "photo_id": "synthetic_photo_low_confidence",
        "photo_filename": "synthetic_low_confidence_blurry_card.svg",
        "purpose": "A blurry synthetic card must stay in must-review instead of being accepted.",
        "confidence": 15,
        "raw_payload": {
            "rawStrain": "",
            "sexRaw": "",
            "mouseCount": "",
            "uncertainFields": ["raw_strain", "sex_raw", "mouse_count"],
            "confidence": 15,
        },
        "expected_parse": {
            "status": "review",
            "max_confidence": 20,
            "uncertain_fields_include": ["raw_strain", "sex_raw", "mouse_count"],
        },
        "note_items": [
            {"raw_line_text": "blurred line", "parsed_ear_label_review_status": "needs_review"},
        ],
        "review": {
            "severity": "High",
            "issue": "AI-extracted photo transcription needs review",
            "review_reason": "Synthetic low-confidence card must be reviewed.",
            "attention_levels_include": ["must_review"],
            "targets_include": ["Low OCR confidence"],
        },
    },
    {
        "case_id": "synthetic_numeric_notes_card",
        "coverage_tags": ["numeric_notes"],
        "photo_id": "synthetic_photo_numeric_notes",
        "photo_filename": "synthetic_numeric_notes_card.svg",
        "purpose": "Numeric note-only lines must remain reviewable and not become clean mouse IDs.",
        "confidence": 70,
        "raw_payload": {
            "rawStrain": "ApoM Tg/Tg",
            "sexRaw": "F 6",
            "mouseCount": "6",
            "uncertainFields": ["notes"],
            "confidence": 70,
        },
        "expected_parse": {
            "status": "review",
            "min_confidence": 60,
            "field_contains": {"mouseCount": ["6"]},
        },
        "note_items": [
            {"raw_line_text": "1", "parsed_ear_label_review_status": "needs_review"},
            {"raw_line_text": "6", "parsed_ear_label_review_status": "needs_review"},
        ],
        "review": {
            "severity": "Medium",
            "issue": "Unlabeled numeric note needs review",
            "review_reason": "Synthetic numeric notes need note-line review.",
            "attention_levels_include": ["quick_check"],
            "targets_include": ["Numeric note label", "Note line anchor"],
        },
    },
    {
        "case_id": "synthetic_digit_prime_confusion_card",
        "coverage_tags": ["ear_label_ambiguity"],
        "photo_id": "synthetic_photo_digit_prime",
        "photo_filename": "synthetic_digit_prime_confusion_card.svg",
        "purpose": "A possible prime mark misread as digit 1 must stay reviewable.",
        "confidence": 64,
        "raw_payload": {
            "rawStrain": "ApoM Tg/Tg",
            "sexRaw": "M 3",
            "mouseCount": "3",
            "uncertainFields": ["notes"],
            "confidence": 64,
        },
        "expected_parse": {
            "status": "review",
            "min_confidence": 60,
            "field_contains": {"rawStrain": ["ApoM", "Tg/Tg"], "mouseCount": ["3"]},
        },
        "note_items": [
            {"raw_line_text": "300 R1", "parsed_ear_label_review_status": "needs_review"},
            {"raw_line_text": "301 L'", "parsed_ear_label_code": "L_PRIME", "parsed_ear_label_review_status": "auto_filled"},
        ],
        "review": {
            "severity": "Medium",
            "issue": "Ear label needs review",
            "review_reason": "Synthetic digit/prime ambiguity needs source-photo review.",
            "attention_levels_include": ["quick_check"],
            "targets_include": ["Ear label", "Source photo"],
        },
    },
    {
        "case_id": "synthetic_dense_mating_notes_card",
        "coverage_tags": ["dense_notes"],
        "photo_id": "synthetic_photo_dense_mating",
        "photo_filename": "synthetic_dense_mating_notes_card.svg",
        "purpose": "Dense mating-like note lines must preserve raw evidence and stay reviewable.",
        "confidence": 52,
        "raw_payload": {
            "rawStrain": "ApoM Tg/Tg",
            "sexRaw": "M/F",
            "mouseCount": "10p",
            "uncertainFields": ["mouse_count", "notes"],
            "confidence": 52,
        },
        "expected_parse": {
            "status": "review",
            "min_confidence": 40,
            "field_contains": {"rawStrain": ["ApoM", "Tg/Tg"]},
            "uncertain_fields_include": ["mouse_count", "notes"],
        },
        "note_items": [
            {"raw_line_text": "26.7.21 - 4p", "parsed_ear_label_review_status": "needs_review"},
            {"raw_line_text": "26.48 - 10p", "parsed_ear_label_review_status": "needs_review"},
        ],
        "review": {
            "severity": "Medium",
            "issue": "AI-extracted photo transcription needs review",
            "review_reason": "Synthetic dense mating notes need source review.",
            "attention_levels_include": ["must_review"],
            "targets_include": ["Mouse count", "Notes"],
        },
    },
]


def render_svg(case: dict[str, Any]) -> str:
    title = html.escape(case["case_id"].replace("_", " ").title())
    lines = [html.escape(item["raw_line_text"]) for item in case["note_items"]]
    notes = "\n".join(
        f'<text x="52" y="{190 + index * 34}" class="note">{line}</text>'
        for index, line in enumerate(lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="620" viewBox="0 0 900 620">
  <rect width="900" height="620" fill="#f8faf8"/>
  <rect x="36" y="32" width="828" height="556" rx="10" fill="#fffdf7" stroke="#243832" stroke-width="4"/>
  <text x="52" y="86" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#243832">{title}</text>
  <text x="52" y="132" font-family="Arial, sans-serif" font-size="26" fill="#243832">Strain: {html.escape(case["raw_payload"].get("rawStrain") or "uncertain")}</text>
  <text x="52" y="164" font-family="Arial, sans-serif" font-size="24" fill="#5f6f68">Synthetic local validation fixture</text>
  <g font-family="Comic Sans MS, Arial, sans-serif" font-size="30" fill="#1f2d2a">{notes}</g>
  <text x="52" y="546" font-family="Arial, sans-serif" font-size="18" fill="#8a4b0f">Local-only fixture; not raw colony evidence.</text>
</svg>
"""


def manifest_case(case: dict[str, Any]) -> dict[str, Any]:
    review = case["review"]
    expected_open_review = {
        "attention_levels_include": review.get("attention_levels_include", ["quick_check"]),
        "targets_include": review.get("targets_include", []),
    }
    return {
        "case_id": case["case_id"],
        "coverage_tags": case["coverage_tags"],
        "photo_id": case["photo_id"],
        "photo_filename": case["photo_filename"],
        "purpose": case["purpose"],
        "min_photo_bytes": 500,
        "expected_parse": case["expected_parse"],
        "expected_note_items": [
            {
                key: value
                for key, value in item.items()
                if key in {"raw_line_text", "parsed_ear_label_code", "parsed_ear_label_review_status"}
            }
            for item in case["note_items"]
        ],
        "expected_open_review": expected_open_review,
    }


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE photo_log (
            photo_id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            status TEXT NOT NULL,
            raw_source_kind TEXT NOT NULL,
            source_layer TEXT NOT NULL
        );
        CREATE TABLE parse_result (
            parse_id TEXT PRIMARY KEY,
            photo_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            raw_payload TEXT NOT NULL,
            parsed_at TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence REAL NOT NULL,
            needs_review INTEGER NOT NULL
        );
        CREATE TABLE card_note_item_log (
            note_item_id TEXT PRIMARY KEY,
            photo_id TEXT NOT NULL,
            parse_id TEXT NOT NULL,
            card_type TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            raw_line_text TEXT NOT NULL,
            parsed_ear_label_code TEXT,
            parsed_ear_label_review_status TEXT NOT NULL,
            confidence REAL NOT NULL,
            needs_review INTEGER NOT NULL
        );
        CREATE TABLE review_queue (
            review_id TEXT PRIMARY KEY,
            parse_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            issue TEXT NOT NULL,
            current_value TEXT NOT NULL,
            suggested_value TEXT NOT NULL,
            review_reason TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            resolved_at TEXT NOT NULL,
            resolution_note TEXT NOT NULL
        );
        """
    )


def insert_case(conn: sqlite3.Connection, output_dir: Path, case: dict[str, Any], index: int) -> None:
    parse_id = f"synthetic_parse_{index:02d}"
    photo_path = output_dir / case["photo_filename"]
    photo_path.write_text(render_svg(case), encoding="utf-8")
    conn.execute(
        """
        INSERT INTO photo_log
            (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind, source_layer)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case["photo_id"],
            case["photo_filename"],
            str(photo_path),
            f"2026-05-11T00:0{index}:00Z",
            "review_pending",
            "synthetic_cage_card_photo",
            "raw source",
        ),
    )
    conn.execute(
        """
        INSERT INTO parse_result
            (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            parse_id,
            case["photo_id"],
            "synthetic_photo_fixture",
            json.dumps(case["raw_payload"], ensure_ascii=False),
            f"2026-05-11T00:1{index}:00Z",
            "review",
            case["confidence"],
            1,
        ),
    )
    for line_number, item in enumerate(case["note_items"], start=1):
        conn.execute(
            """
            INSERT INTO card_note_item_log
                (note_item_id, photo_id, parse_id, card_type, line_number, raw_line_text,
                 parsed_ear_label_code, parsed_ear_label_review_status, confidence, needs_review)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"synthetic_note_{index:02d}_{line_number:02d}",
                case["photo_id"],
                parse_id,
                "Synthetic",
                line_number,
                item["raw_line_text"],
                item.get("parsed_ear_label_code"),
                item["parsed_ear_label_review_status"],
                70 if item["parsed_ear_label_review_status"] == "auto_filled" else 45,
                1 if item["parsed_ear_label_review_status"] == "needs_review" else 0,
            ),
        )
    review = case["review"]
    conn.execute(
        """
        INSERT INTO review_queue
            (review_id, parse_id, severity, issue, current_value, suggested_value,
             review_reason, status, created_at, resolved_at, resolution_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"synthetic_review_{index:02d}",
            parse_id,
            review["severity"],
            review["issue"],
            json.dumps(case["raw_payload"], ensure_ascii=False),
            "{}",
            review["review_reason"],
            "open",
            f"2026-05-11T00:2{index}:00Z",
            "",
            "",
        ),
    )


def generate(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "synthetic_photo_e2e.sqlite"
    if db_path.exists():
        db_path.unlink()
    manifest_path = output_dir / "synthetic_photo_e2e_validation_cases.json"

    with sqlite3.connect(db_path) as conn:
        create_schema(conn)
        for index, case in enumerate(CASES, start=1):
            insert_case(conn, output_dir, case, index)

    manifest = {
        "boundary": "review item / test fixture",
        "canonical": False,
        "description": "Synthetic local cage-card regression set for parser and review safety contracts.",
        "source_policy": SOURCE_POLICY,
        "recommended_coverage_tags": [
            "clear",
            "low_confidence",
            "dense_notes",
            "cropped_or_blurry",
            "ear_label_ambiguity",
            "numeric_notes",
        ],
        "latest_parse_selector": {
            "source_name": "synthetic_photo_fixture",
            "order": "parsed_at DESC",
            "limit": 1,
        },
        "cases": [manifest_case(case) for case in CASES],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "boundary": "review item / test fixture",
        "canonical": False,
        "case_count": len(CASES),
        "image_count": len(CASES),
        "manifest": str(manifest_path),
        "database": str(db_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate local synthetic cage-card photo E2E fixtures.")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.output_dir), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
