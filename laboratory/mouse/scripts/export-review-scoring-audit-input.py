from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = "review item / private accuracy scoring input"
ALLOWED_AUDIT_STATUSES = {
    "exact",
    "partial_match",
    "near_miss",
    "unscorable_due_to_occlusion",
}


def sanitized_run_label(value: str) -> str:
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return label or "review-scoring-audit"


def json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        decoded = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def safe_audit_status(value: Any) -> str:
    status = str(value or "").strip()
    return status if status in ALLOWED_AUDIT_STATUSES else ""


def load_manifest(path: Path | str) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = manifest.get("cases")
    if manifest.get("layer") != "review item / test fixture" or manifest.get("canonical") is not False:
        raise ValueError("manifest must be a local-only review item test fixture")
    if not isinstance(cases, list):
        raise ValueError("manifest.cases must be a list")
    return manifest


def manifest_cases_by_filename(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for case in manifest.get("cases", []):
        if not isinstance(case, dict):
            continue
        filename = str(case.get("source_photo_filename") or "").strip().lower()
        case_id = str(case.get("case_id") or "").strip()
        if filename and case_id:
            index[filename] = case
    return index


def default_field_scores(status: str) -> dict[str, dict[str, Any]]:
    note_status = "exact" if status == "exact" else "corrected"
    reviewed = status != "exact"
    return {
        "mouse_ids_or_note_lines": {
            "status": note_status,
            "reviewed_before_apply": True,
            "traceable": True,
        },
        "card_type_review_routing": {
            "status": "not_applicable",
            "reviewed_before_apply": reviewed,
            "traceable": True,
        },
        "sex_count_dob": {
            "status": "not_applicable",
            "reviewed_before_apply": reviewed,
            "traceable": True,
        },
        "mating_litter_context": {
            "status": "not_applicable",
            "reviewed_before_apply": reviewed,
            "traceable": True,
        },
        "export_provenance": {
            "status": "not_applicable",
            "reviewed_before_apply": reviewed,
            "traceable": True,
        },
    }


def scored_note_case(status: str) -> dict[str, Any]:
    exact = status == "exact"
    labels = [] if exact else [status]
    return {
        "hybrid_pre_review_status": status,
        "local_ocr_pre_review_status": "",
        "ai_pre_review_status": "",
        "expected_candidate_present": True,
        "auto_candidate_usable_without_edit": exact,
        "review_correction_required": not exact,
        "reviewer_override": not exact,
        "reviewed_before_apply": True,
        "source_image_quality_bucket": "unknown",
        "roi_alignment_bucket": "unknown",
        "line_segmentation_bucket": "unknown",
        "rule_snapshot_hash": "unknown_rule_hash",
        "failure_labels": labels,
    }


def result_case(case_id: str, status: str, *, created_at: str = "") -> dict[str, Any]:
    exact = status == "exact"
    return {
        "case_id": case_id,
        "scoring_status": "review_resolution_audit_exported",
        "actual_review_level": "quick_check" if exact else "must_review",
        "export_blocked_until_resolved": False,
        "unresolved_must_review_at_export": False,
        "source_preserved": True,
        "silent_overwrite": False,
        "review_seconds": 0,
        "manual_transcription_required": False,
        "failure_labels": [] if exact else [status],
        "field_scores": default_field_scores(status),
        "hybrid_note_line_evaluator": {
            "boundary": BOUNDARY,
            "scored_cases": [scored_note_case(status)],
        },
        "review_resolution_scoring_audit": {
            "boundary": "review item / scoring audit metadata",
            "provenance": "operator_selected_review_resolution",
            "status": status,
            "created_at": created_at,
        },
    }


def collect_action_audits(conn: sqlite3.Connection) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT action_id, target_id, after_value, created_at
        FROM action_log
        WHERE action_type = 'review_resolved'
        ORDER BY created_at, action_id
        """
    ).fetchall()
    audits = []
    for row in rows:
        after = json_object(row["after_value"])
        scoring = json_object(after.get("scoring_audit"))
        status = safe_audit_status(scoring.get("status"))
        filename = str(after.get("source_photo_filename") or "").strip()
        if status and filename:
            audits.append(
                {
                    "review_id": str(row["target_id"] or ""),
                    "source_photo_filename": filename,
                    "status": status,
                    "created_at": str(row["created_at"] or ""),
                    "source": "action_log",
                }
            )
    return audits


def collect_correction_audits(conn: sqlite3.Connection, seen_reviews: set[str]) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT correction.review_id, correction.correction_context_json, correction.corrected_at,
               photo.original_filename
        FROM correction_log correction
        LEFT JOIN review_queue review ON review.review_id = correction.review_id
        LEFT JOIN parse_result parse ON parse.parse_id = review.parse_id
        LEFT JOIN photo_log photo ON photo.photo_id = parse.photo_id
        ORDER BY correction.corrected_at, correction.correction_id
        """
    ).fetchall()
    audits = []
    for row in rows:
        review_id = str(row["review_id"] or "")
        if review_id in seen_reviews:
            continue
        context = json_object(row["correction_context_json"])
        status = safe_audit_status(context.get("scoring_audit_status"))
        filename = str(row["original_filename"] or "").strip()
        if status and filename:
            audits.append(
                {
                    "review_id": review_id,
                    "source_photo_filename": filename,
                    "status": status,
                    "created_at": str(row["corrected_at"] or ""),
                    "source": "correction_log",
                }
            )
    return audits


def collect_review_scoring_audits(db_path: Path | str) -> list[dict[str, str]]:
    conn = sqlite3.connect(Path(db_path))
    conn.row_factory = sqlite3.Row
    try:
        action_audits = collect_action_audits(conn)
        seen_reviews = {audit["review_id"] for audit in action_audits if audit.get("review_id")}
        return action_audits + collect_correction_audits(conn, seen_reviews)
    finally:
        conn.close()


def build_results_payload(
    *,
    manifest: dict[str, Any],
    audits: list[dict[str, str]],
    run_label: str,
) -> tuple[dict[str, Any], int]:
    cases_by_filename = manifest_cases_by_filename(manifest)
    exported_cases = []
    unmatched = 0
    matched_case_ids: set[str] = set()
    for audit in audits:
        case = cases_by_filename.get(audit["source_photo_filename"].lower())
        if not case:
            unmatched += 1
            continue
        case_id = str(case["case_id"])
        if case_id in matched_case_ids:
            continue
        matched_case_ids.add(case_id)
        exported_cases.append(result_case(case_id, audit["status"], created_at=audit.get("created_at", "")))
    corrected_count = sum(
        1
        for case in exported_cases
        for scored in case["hybrid_note_line_evaluator"]["scored_cases"]
        if scored["review_correction_required"]
    )
    return (
        {
            "layer": BOUNDARY,
            "canonical": False,
            "source_policy": (
                "Local-only scoring input generated from review resolution audit metadata. "
                "Raw photos, private paths, raw OCR/AI text, and raw reviewer notes are omitted."
            ),
            "run_label": sanitized_run_label(run_label),
            "reviewer_scoring_provenance": {
                "method": "manual_operator_review",
                "approved_by_operator": True,
                "approval_scope": "review resolution scoring audit metadata",
                "raw_payload_policy": "omitted_from_sanitized_report",
            },
            "workflow_metrics": {
                "photos_uploaded": len(manifest.get("cases", [])),
                "photos_with_extraction_draft": len(exported_cases),
                "manual_transcriptions": 0,
                "review_items_opened": len(exported_cases),
                "review_items_corrected": corrected_count,
                "review_items_accepted_without_correction": len(exported_cases) - corrected_count,
                "xlsx_exports_generated": 0,
            },
            "cases": exported_cases,
        },
        unmatched,
    )


def export_review_scoring_audit_input(
    *,
    db_path: Path | str,
    manifest_path: Path | str,
    output_path: Path | str,
    run_label: str,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    audits = collect_review_scoring_audits(db_path)
    payload, unmatched = build_results_payload(
        manifest=manifest,
        audits=audits,
        run_label=run_label,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "status": "created",
        "boundary": BOUNDARY,
        "canonical": False,
        "run_label": sanitized_run_label(run_label),
        "matched_case_count": len(payload["cases"]),
        "unmatched_audit_count": unmatched,
        "output_path": "private output path omitted",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export review resolution scoring audit metadata as sanitized private accuracy input."
    )
    parser.add_argument("--db-path", required=True, help="Local SQLite database path.")
    parser.add_argument("--manifest", required=True, help="Private real-photo manifest path.")
    parser.add_argument("--output", required=True, help="Private output JSON path.")
    parser.add_argument("--run-label", default="review-scoring-audit", help="Sanitized run label.")
    parser.add_argument("--json", action="store_true", help="Print sanitized JSON summary.")
    args = parser.parse_args()

    try:
        summary = export_review_scoring_audit_input(
            db_path=Path(args.db_path),
            manifest_path=Path(args.manifest),
            output_path=Path(args.output),
            run_label=args.run_label,
        )
    except Exception as exc:
        private_markers = [args.db_path, args.manifest, args.output]
        error = str(exc)
        for marker in private_markers:
            if marker:
                error = error.replace(marker, "<private path>")
        summary = {
            "status": "failed",
            "boundary": BOUNDARY,
            "canonical": False,
            "error": error,
            "output_path": "private output path omitted",
        }
        if args.json:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            print(f"status: {summary['status']}")
            print(f"error: {summary['error']}")
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"status: {summary['status']}")
        print(f"matched_case_count: {summary['matched_case_count']}")
        print(f"unmatched_audit_count: {summary['unmatched_audit_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
