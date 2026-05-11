from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


BOUNDARY = "review item / test fixture"
SOURCE_POLICY = (
    "Use only locally generated synthetic cage-card fixtures. "
    "Do not send synthetic validation payloads to external services."
)
COVERAGE_TAGS = [
    "clear",
    "low_confidence",
    "dense_notes",
    "cropped_or_blurry",
    "ear_label_ambiguity",
    "numeric_notes",
]


CASES: list[dict[str, Any]] = [
    {
        "case_id": "synthetic_clear_card",
        "photo_filename": "synthetic_clear_card.png",
        "purpose": "Clear cage card fixture for high-confidence baseline checks.",
        "confidence": 92,
        "coverage_tags": ["clear"],
        "notes": ["MT401 R'", "MT402 L'"],
        "review_count": 0,
    },
    {
        "case_id": "synthetic_low_confidence_blurry_card",
        "photo_filename": "synthetic_low_confidence_blurry_card.png",
        "purpose": "Blurred/low-confidence fixture must stay review-blocking.",
        "confidence": 15,
        "coverage_tags": ["low_confidence", "cropped_or_blurry"],
        "notes": ["MT4? R'", "unclear DOB"],
        "review_count": 1,
    },
    {
        "case_id": "synthetic_numeric_notes_card",
        "photo_filename": "synthetic_numeric_notes_card.png",
        "purpose": "Numeric-only note lines must remain note anchors, not mouse IDs.",
        "confidence": 72,
        "coverage_tags": ["numeric_notes"],
        "notes": ["1 2 3", "4, 5"],
        "review_count": 1,
    },
    {
        "case_id": "synthetic_digit_prime_confusion_card",
        "photo_filename": "synthetic_digit_prime_confusion_card.png",
        "purpose": "Digit/prime confusion fixture preserves reviewable ear-label ambiguity.",
        "confidence": 68,
        "coverage_tags": ["ear_label_ambiguity"],
        "notes": ["MT501 R1", "MT502 L'"],
        "review_count": 1,
    },
    {
        "case_id": "synthetic_dense_mating_notes_card",
        "photo_filename": "synthetic_dense_mating_notes_card.png",
        "purpose": "Dense mating/litter note fixture preserves raw line evidence.",
        "confidence": 64,
        "coverage_tags": ["dense_notes", "mating_litter_notes"],
        "notes": ["Mating 2026.05.01", "born 6", "wean 5", "MT601 R'L'"],
        "review_count": 1,
    },
]


def write_synthetic_png(path: Path, label: str) -> None:
    # A small valid-enough local fixture payload for file-presence and byte-size gates.
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + f"Synthetic cage-card fixture: {label}\n".encode("utf-8")
        + (b"local-only-review-fixture\n" * 32)
    )
    path.write_bytes(payload)


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
            source_layer TEXT NOT NULL DEFAULT 'raw source'
        );

        CREATE TABLE parse_result (
            parse_id TEXT PRIMARY KEY,
            photo_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            raw_payload TEXT NOT NULL,
            parsed_at TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence REAL NOT NULL,
            needs_review INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE card_note_item_log (
            note_item_id TEXT PRIMARY KEY,
            photo_id TEXT,
            parse_id TEXT NOT NULL,
            card_type TEXT NOT NULL DEFAULT '',
            line_number INTEGER NOT NULL,
            raw_line_text TEXT NOT NULL,
            parsed_type TEXT NOT NULL DEFAULT '',
            parsed_ear_label_code TEXT NOT NULL DEFAULT '',
            parsed_ear_label_review_status TEXT NOT NULL DEFAULT '',
            interpreted_status TEXT NOT NULL DEFAULT '',
            confidence REAL NOT NULL DEFAULT 0,
            needs_review INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE review_queue (
            review_id TEXT PRIMARY KEY,
            parse_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            issue TEXT NOT NULL,
            current_value TEXT NOT NULL DEFAULT '',
            suggested_value TEXT NOT NULL DEFAULT '',
            review_reason TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )


def populate_database(conn: sqlite3.Connection, output_dir: Path) -> None:
    for index, case in enumerate(CASES, start=1):
        photo_id = f"synthetic_photo_{index:02d}"
        parse_id = f"synthetic_parse_{index:02d}"
        photo_path = output_dir / case["photo_filename"]
        raw_payload = {
            "payload_kind": "synthetic_photo_fixture",
            "source_layer": "parsed or intermediate result",
            "card_type": "Separated",
            "raw_visible_text_lines": case["notes"],
            "confidence": case["confidence"],
            "coverage_tags": case["coverage_tags"],
        }
        conn.execute(
            """
            INSERT INTO photo_log
                (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind, source_layer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                photo_id,
                case["photo_filename"],
                str(photo_path),
                "2026-05-11T00:00:00Z",
                "accepted",
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
                photo_id,
                "synthetic_photo_fixture",
                json.dumps(raw_payload, ensure_ascii=False),
                "2026-05-11T00:01:00Z",
                "review" if case["review_count"] else "accepted",
                case["confidence"],
                1 if case["review_count"] else 0,
            ),
        )
        for line_number, raw_line in enumerate(case["notes"], start=1):
            conn.execute(
                """
                INSERT INTO card_note_item_log
                    (note_item_id, photo_id, parse_id, card_type, line_number, raw_line_text,
                     parsed_type, parsed_ear_label_code, parsed_ear_label_review_status,
                     interpreted_status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"synthetic_note_{index:02d}_{line_number:02d}",
                    photo_id,
                    parse_id,
                    "Separated",
                    line_number,
                    raw_line,
                    "mouse_item" if "MT" in raw_line else "unlabeled_numeric_note",
                    "",
                    "needs_review" if "?" in raw_line or "R1" in raw_line else "accepted",
                    "active",
                    case["confidence"],
                    1 if case["review_count"] else 0,
                ),
            )
        for review_index in range(case["review_count"]):
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value, suggested_value,
                     review_reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"synthetic_review_{index:02d}_{review_index + 1:02d}",
                    parse_id,
                    "High" if case["confidence"] <= 20 else "Medium",
                    "Synthetic photo fixture review",
                    case["case_id"],
                    "Manual review required",
                    case["purpose"],
                    "open",
                    "2026-05-11T00:02:00Z",
                ),
            )


def build_manifest(output_dir: Path) -> dict[str, Any]:
    cases = []
    for case in CASES:
        image_path = output_dir / case["photo_filename"]
        cases.append(
            {
                "case_id": case["case_id"],
                "photo_id": f"synthetic_photo_{len(cases) + 1:02d}",
                "photo_filename": case["photo_filename"],
                "purpose": case["purpose"],
                "coverage_tags": case["coverage_tags"],
                "min_photo_bytes": image_path.stat().st_size,
                "expected_parse": {
                    "min_confidence": 60 if case["confidence"] >= 60 else 0,
                    "max_confidence": 20 if case["confidence"] <= 20 else 100,
                },
            }
        )
    return {
        "boundary": BOUNDARY,
        "canonical": False,
        "description": "Synthetic local cage-card regression fixtures for verifier development.",
        "source_policy": SOURCE_POLICY,
        "latest_parse_selector": {
            "source_name": "synthetic_photo_fixture",
            "order": "parsed_at DESC",
        },
        "recommended_coverage_tags": COVERAGE_TAGS,
        "cases": cases,
    }


def generate(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        write_synthetic_png(output_dir / case["photo_filename"], case["case_id"])

    manifest = build_manifest(output_dir)
    manifest_path = output_dir / "synthetic_photo_e2e_validation_cases.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    db_path = output_dir / "synthetic_photo_e2e.sqlite"
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        create_schema(conn)
        populate_database(conn, output_dir)

    return {
        "boundary": BOUNDARY,
        "canonical": False,
        "case_count": len(CASES),
        "image_count": len(CASES),
        "manifest": str(manifest_path),
        "database": str(db_path),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate local synthetic cage-card E2E fixtures.")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.output_dir), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
