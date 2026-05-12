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
from scripts.local_ocr_provider import extract_text_with_tesseract, tesseract_provider_status  # noqa: E402


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


def normalize_ocr_match_text(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def note_hint_matched(ocr_text: str, hint: str) -> bool:
    normalized_ocr = normalize_ocr_match_text(ocr_text)
    normalized_hint = normalize_ocr_match_text(hint)
    return bool(normalized_hint and normalized_hint in normalized_ocr)


def ocr_quality_grade(text_length: int, expected_hint_count: int, matched_hint_count: int) -> str:
    if text_length == 0:
        return "empty"
    if matched_hint_count == 0:
        return "garbled"
    if matched_hint_count < expected_hint_count:
        return "partial_note_match"
    return "usable_note_match"


def ocr_case_action(quality_grade: str) -> dict[str, Any]:
    if quality_grade == "empty":
        return {
            "review_required": True,
            "recommended_action": "Treat empty OCR as review-only and require source photo or manual note-line evidence.",
        }
    if quality_grade == "garbled":
        return {
            "review_required": True,
            "recommended_action": "Route this card type to review and tune image preprocessing before trusting raw OCR text.",
        }
    return {
        "review_required": False,
        "recommended_action": (
            "Use OCR note-line hints as review aids only; keep fixture draft and source photo as the evidence anchors."
        ),
    }


def empty_ocr_quality_report() -> dict[str, Any]:
    return {
        "case_count": 0,
        "empty_ocr_case_count": 0,
        "hint_matched_case_count": 0,
        "text_length_min": 0,
        "text_length_max": 0,
        "quality_grade_counts": {},
        "by_coverage_tag": {},
        "quality_findings": [],
    }


def ocr_quality_findings(by_coverage_tag: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    findings = []
    for tag, summary in sorted(by_coverage_tag.items()):
        empty_count = summary["empty_ocr_case_count"]
        garbled_count = summary["garbled_case_count"]
        if empty_count:
            findings.append(
                {
                    "coverage_tag": tag,
                    "issue": "empty_ocr",
                    "affected_case_count": empty_count,
                    "recommended_action": (
                        "Treat empty OCR as review-only and require source photo or manual note-line evidence."
                    ),
                }
            )
        if garbled_count:
            findings.append(
                {
                    "coverage_tag": tag,
                    "issue": "garbled_ocr",
                    "affected_case_count": garbled_count,
                    "recommended_action": (
                        "Route this card type to review and tune image preprocessing before trusting raw OCR text."
                    ),
                }
            )
    return findings


def summarize_ocr_quality(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return empty_ocr_quality_report()
    lengths = [int(result["text_length"]) for result in results]
    grade_counts: dict[str, int] = {}
    by_coverage_tag: dict[str, dict[str, int]] = {}
    for result in results:
        grade = str(result["quality_grade"])
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
        for tag in result["coverage_tags"]:
            tag_summary = by_coverage_tag.setdefault(
                str(tag),
                {
                    "case_count": 0,
                    "empty_ocr_case_count": 0,
                    "garbled_case_count": 0,
                    "partial_note_match_case_count": 0,
                    "usable_note_match_case_count": 0,
                },
            )
            tag_summary["case_count"] += 1
            if grade == "empty":
                tag_summary["empty_ocr_case_count"] += 1
            elif grade == "garbled":
                tag_summary["garbled_case_count"] += 1
            elif grade == "partial_note_match":
                tag_summary["partial_note_match_case_count"] += 1
            elif grade == "usable_note_match":
                tag_summary["usable_note_match_case_count"] += 1
    return {
        "case_count": len(results),
        "empty_ocr_case_count": len([result for result in results if result["empty_ocr"]]),
        "hint_matched_case_count": len([result for result in results if result["matched_note_hints"]]),
        "text_length_min": min(lengths),
        "text_length_max": max(lengths),
        "quality_grade_counts": grade_counts,
        "by_coverage_tag": by_coverage_tag,
        "quality_findings": ocr_quality_findings(by_coverage_tag),
    }


def probe_local_ocr(generated: dict[str, Any], ocr_provider: dict[str, object]) -> dict[str, Any]:
    if not ocr_provider["available"]:
        return {
            "provider": "tesseract_cli",
            "status": "skipped",
            "case_count": 0,
            "external_inference_used": False,
            "skip_reason": str(ocr_provider["skip_reason"]),
            "quality_report": summarize_ocr_quality([]),
        }

    manifest_path = Path(generated["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_dir = manifest_path.parent
    results = []
    for case in manifest.get("cases", []):
        photo_filename = str(case.get("photo_filename") or "")
        ocr_result = extract_text_with_tesseract(image_dir / photo_filename)
        ocr_text = str(ocr_result.get("text") or "")
        expected_note_hints = [
            str(item.get("raw_line_text") or "")
            for item in case.get("expected_note_items", [])
            if item.get("raw_line_text")
        ]
        matched_note_hints = [hint for hint in expected_note_hints if note_hint_matched(ocr_text, hint)]
        text_length = len(ocr_text)
        quality_grade = ocr_quality_grade(text_length, len(expected_note_hints), len(matched_note_hints))
        case_action = ocr_case_action(quality_grade)
        results.append(
            {
                "case_id": str(case.get("case_id") or ""),
                "coverage_tags": [str(tag) for tag in case.get("coverage_tags", [])],
                "photo_filename": photo_filename,
                "status": ocr_result["status"],
                "text_length": text_length,
                "empty_ocr": not bool(ocr_text.strip()),
                "quality_grade": quality_grade,
                "text_preview": ocr_text[:240],
                "expected_note_hints": expected_note_hints,
                "matched_note_hints": matched_note_hints,
                "external_inference_used": bool(ocr_result["external_inference_used"]),
                "canonical_write": False,
                **case_action,
            }
        )
    failed = len([result for result in results if result["status"] == "failed"])
    return {
        "provider": "tesseract_cli",
        "status": "failed" if failed else "ok",
        "case_count": len(results),
        "failed": failed,
        "external_inference_used": False,
        "quality_report": summarize_ocr_quality(results),
        "results": results,
    }


def verify(output_dir: Path) -> dict[str, Any]:
    generated = generate(output_dir)
    verification = verify_generated_drafts(generated)
    ocr_provider = tesseract_provider_status()
    return {
        "boundary": "review item / test fixture",
        "canonical": False,
        "source_policy": SOURCE_POLICY,
        "ocr_provider": ocr_provider,
        "local_ocr_probe": probe_local_ocr(generated, ocr_provider),
        "extraction_mode": "local_ocr" if ocr_provider["available"] else "fixture_payload_surrogate",
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
            quality = summary["local_ocr_probe"]["quality_report"]
            print(
                "Synthetic draft extraction: "
                f"{verification['passed']}/{verification['case_count']} passed, "
                f"{verification['failed']} failed"
            )
            print(
                "Local OCR quality: "
                f"{quality['empty_ocr_case_count']} empty OCR / "
                f"{quality['case_count']} case(s), "
                f"{quality['hint_matched_case_count']} note-line hints matched, "
                f"text length range {quality['text_length_min']}-{quality['text_length_max']}"
            )
            if quality["by_coverage_tag"]:
                print("By card type:")
                for tag, tag_quality in sorted(quality["by_coverage_tag"].items()):
                    print(
                        f"  {tag}: "
                        f"{tag_quality['case_count']} case(s), "
                        f"{tag_quality['empty_ocr_case_count']} empty, "
                        f"{tag_quality['garbled_case_count']} garbled, "
                        f"{tag_quality['partial_note_match_case_count']} partial, "
                        f"{tag_quality['usable_note_match_case_count']} usable"
                    )
            if quality["quality_findings"]:
                print("OCR weak spots:")
                for finding in quality["quality_findings"]:
                    print(
                        f"  {finding['coverage_tag']} -> {finding['issue']} "
                        f"({finding['affected_case_count']} case)"
                    )
        return int(summary["exit_code"])
    finally:
        if temp_dir is not None and temp_dir.exists():
            remove_tree_with_retries(temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
