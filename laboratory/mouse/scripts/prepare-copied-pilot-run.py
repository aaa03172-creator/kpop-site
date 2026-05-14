from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts" / "verify-real-photo-pilot.py"


def load_real_photo_verifier() -> Any:
    spec = importlib.util.spec_from_file_location("verify_real_photo_pilot", VERIFIER_PATH)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load verifier: {VERIFIER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sanitize_failures(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for failure in failures:
        messages = []
        for message in failure.get("failures", []):
            text = str(message)
            if text.startswith("source_photo_path does not exist:"):
                text = "source_photo_path does not exist: <private source photo path>"
            messages.append(text)
        sanitized.append({"case_id": str(failure.get("case_id") or ""), "failures": messages})
    return sanitized


def case_rows(cases: list[dict[str, Any]]) -> str:
    rows = []
    for case in cases:
        rows.append(
            "| {case_id} | {card_type} | {review_level} | {blocking} | private source photo path omitted |".format(
                case_id=case.get("case_id") or "",
                card_type=case.get("card_type") or "",
                review_level=case.get("expected_review_level") or "",
                blocking=str(bool(case.get("expected_export_blocking"))).lower(),
            )
        )
    return "\n".join(rows)


def readiness_rows(readiness: dict[str, Any]) -> str:
    rows = [f"| Go/no-go | {readiness.get('status', 'skipped')} | |"]
    checks = readiness.get("checks")
    if not isinstance(checks, dict):
        return "\n".join(rows)
    for name, check in checks.items():
        if not isinstance(check, dict):
            continue
        details = {
            key: value
            for key, value in check.items()
            if key != "status"
        }
        rows.append(
            "| {name} | {status} | {details} |".format(
                name=name,
                status=check.get("status", ""),
                details=json.dumps(details, ensure_ascii=False, sort_keys=True),
            )
        )
    return "\n".join(rows)


def build_sanitized_log(*, run_label: str, summary: dict[str, Any]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    coverage = summary.get("coverage", {})
    card_type_counts = coverage.get("card_type_counts", {})
    review_level_counts = coverage.get("review_level_counts", {})
    export_blocking_counts = coverage.get("export_blocking_counts", {})
    cases = summary.get("cases", [])
    status = summary.get("status", "failed")
    readiness = summary.get("readiness", {})

    return f"""# Copied Pilot Run Log - {run_label}

Layer classification: review item / pilot run log.

Canonical: false.

Generated at: {generated_at}

This sanitized log was prepared from a private copied-photo manifest. It intentionally omits private photo paths, raw OCR/AI payloads, generated workbook paths, local database paths, and backup folder paths.

## Preflight

| Check | Result |
| --- | --- |
| Manifest validation | {status} |
| Manifest used | private manifest verified; path intentionally omitted |
| Case count | {summary.get("case_count", 0)} |
| Data boundary | review item / test fixture |
| Source photos | raw source copied outside Git |

## Manifest Coverage

| Coverage | Counts |
| --- | --- |
| Card types | {json.dumps(card_type_counts, ensure_ascii=False, sort_keys=True)} |
| Review levels | {json.dumps(review_level_counts, ensure_ascii=False, sort_keys=True)} |
| Export blocking | {json.dumps(export_blocking_counts, ensure_ascii=False, sort_keys=True)} |

## Sanitized Metrics To Publish

Publish only aggregate counts and rates from the copied-photo run. Do not publish private photo paths, raw card text, raw OCR/AI payloads, local database paths, generated workbook paths, or case-level animal-room details.

| Metric | Sanitized value |
| --- | ---: |
| Manifest cases verified | {summary.get("case_count", 0)} |
| Photos uploaded |  |
| Photos with extraction draft |  |
| Photos requiring manual transcription |  |
| Review items opened |  |
| Review items corrected |  |
| Review items accepted without correction |  |
| Export-blocking items found |  |
| Export-blocking items resolved |  |
| XLSX exports generated |  |

## Failure Taxonomy

Use these labels in the public summary. Keep examples generic and omit raw source text.

| Failure label | Public definition |
| --- | --- |
| `source_trace_missing` | A candidate, review item, or export row could not be traced to a copied photo or note-line evidence label. |
| `low_confidence_unreviewed` | Low-confidence extraction output could proceed without review. |
| `raw_normalized_mixed` | Raw visible text and normalized values were not clearly separated. |
| `mouse_id_or_note_line_error` | A mouse ID, ear label, struck note, or continuity note was missing, merged, split, or assigned to the wrong field. |
| `date_or_count_error` | DOB, mating date, litter date, sex count, or pup count was wrong or normalized without adequate review. |
| `mating_litter_context_error` | Sire, dam, mating, litter, or pup note context was lost or attached to the wrong event. |
| `export_safety_error` | Export included unresolved blockers, stale values, or rows without evidence trace. |
| `privacy_leak` | A public artifact exposed private photo paths, raw OCR/AI text, generated workbook paths, local database paths, or animal-room details. |
| `operator_workload_excessive` | Review time, correction count, or unresolved ambiguity exceeded the go/no-go workload criteria. |

## Reviewer Workload Criteria

Record workload as aggregate numbers only.

| Criterion | Go threshold | Run value |
| --- | --- | ---: |
| Median review time per photo | At or below 4 minutes |  |
| 90th percentile review time per photo | At or below 8 minutes |  |
| Manual transcription required | At or below 40% of photos unless deliberately testing unclear cards |  |
| Reviewer can explain evidence for exported rows | 100% of exported rows |  |
| Unresolved `must_review` items at export time | 0 |  |

## Accuracy Evaluation Criteria

Use the same private manifest expected fields for local scoring, then publish only sanitized aggregates.

| Field family | Go threshold |
| --- | --- |
| Mouse IDs and note-line continuity | 95% exact or reviewer-corrected before apply; 0 unreviewed high-risk misses. |
| Card type and review routing | 100% of `unclear` and blocker cases route to review; no unsupported card is forced into canonical state. |
| Sex/count and DOB/date handling | 90% correct after review, with all ambiguous dates kept raw until reviewer confirmation. |
| Mating/litter context | 90% correct after review, with sire/dam/litter notes traceable to source evidence. |
| Export provenance | 100% of exported rows trace to copied photo, note item, or accepted review correction. |

## Go / No-Go Criteria

Go only if every hard gate passes. A soft gate miss means revise workflow or runbook before expanding the pilot.

| Gate | Type | Pass condition | Run value |
| --- | --- | --- | --- |
| Private data containment | Hard | No committed private photos, raw text, local paths, OCR/AI payloads, generated workbooks, or backup paths. |  |
| Manifest coverage | Hard | 20-30 copied photos with separated, mating, unclear, and other/unknown coverage represented. |  |
| Source preservation | Hard | Original photos unchanged; copied pilot photos preserved even when unreadable. |  |
| Review safety | Hard | No silent overwrite; before/after values preserved for corrections and inferred changes. |  |
| Export safety | Hard | No export while unresolved `must_review` blockers remain. |  |
| Accuracy thresholds | Hard | All field-family thresholds above are met using sanitized aggregate scoring. |  |
| Reviewer workload | Soft | Workload criteria above are met or documented with a narrowed follow-up run. |  |
| Failure taxonomy | Soft | Every failure is assigned one of the public labels above or a new sanitized label. |  |

## Go/No-Go Readiness

| Check | Status | Sanitized details |
| --- | --- | --- |
{readiness_rows(readiness)}

## Per-Photo Private Manifest Summary

| Case/photo label | Card type | Expected review level | Export blocking? | Private path status |
| --- | --- | --- | --- | --- |
{case_rows(cases)}

Operator wording note: manifest card type `other` maps to the UI label `Other / Unknown`. Treat it as trace-only unless the source photo clearly supports a supported cage-card workflow.

## Repeatable Operator Flow

1. Run manifest preflight: `python scripts/verify-real-photo-pilot.py --manifest <private manifest>`.
2. Run this sanitized runbook harness: `python scripts/prepare-copied-pilot-run.py --manifest <private manifest> --run-label <label> --output-log docs/pilot_runs/YYYY-MM-DD-<label>.md`.
3. Run a pre-session backup: `powershell -ExecutionPolicy Bypass -File scripts/backup-local-pilot.ps1 -Label before-<label>`.
4. Start the app with `start.bat` and use a normal browser or standalone Playwright for upload/download verification. The in-app Browser control surface does not provide file upload support for the private copied-photo pilot.
5. Upload copied source photos and confirm they remain raw source evidence.
6. Choose the AI / local OCR / manual extraction decision per photo. Use AI only after explicit approval for that run and keep payloads minimized.
7. Resolve review items, apply source-backed canonical candidates, and confirm export readiness before XLSX download.
8. Run a post-session backup: `powershell -ExecutionPolicy Bypass -File scripts/backup-local-pilot.ps1 -Label after-<label>`.
9. Restore into a separate probe folder before go/no-go: `powershell -ExecutionPolicy Bypass -File scripts/restore-local-pilot.ps1 -BackupPath <private backup> -TargetRoot <private restore probe>`.

## Workflow Counts

| Metric | Count |
| --- | ---: |
| Photos uploaded |  |
| Manual transcriptions |  |
| AI extraction attempts |  |
| Review items resolved |  |
| Canonical candidates applied |  |
| XLSX downloads |  |
| Backup/restore drill result |  |

## Friction And Data Gaps

- Browser/upload surface:
- Other / Unknown card-type cases:
- AI / local OCR / manual extraction decision:
- Review or candidate apply blockers:
- Export readiness or XLSX download blockers:
- Backup/restore findings:

## Sanitization Checklist

- [ ] No private source photo paths.
- [ ] No raw copied-photo OCR/AI payloads.
- [ ] No raw expected field text copied from the private manifest.
- [ ] No generated workbook paths.
- [ ] No local database or backup folder paths.
- [ ] No animal-room details beyond sanitized case labels.
"""


def sanitized_summary(summary: dict[str, Any], output_log: Path | None) -> dict[str, Any]:
    return {
        "status": summary.get("status", "failed"),
        "boundary": "review item / pilot run log",
        "canonical": False,
        "manifest_case_count": summary.get("case_count", 0),
        "coverage": summary.get("coverage", {}),
        "readiness": summary.get("readiness", {}),
        "failures": sanitize_failures(summary.get("failures", [])),
        "sanitized_log_path": str(output_log) if output_log else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a repeatable sanitized run log for a copied-photo pilot.")
    parser.add_argument("--manifest", default="config/real_photo_validation_cases.example.json")
    parser.add_argument("--run-label", default="copied-pilot")
    parser.add_argument("--output-log", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()

    verifier = load_real_photo_verifier()
    manifest = verifier.load_manifest(manifest_path)
    validation = verifier.validate_manifest(manifest, manifest_path)

    output_log = Path(args.output_log) if args.output_log else None
    if output_log and validation.get("status") == "passed":
        output_log.parent.mkdir(parents=True, exist_ok=True)
        output_log.write_text(
            build_sanitized_log(run_label=args.run_label, summary=validation),
            encoding="utf-8",
        )

    result = sanitized_summary(validation, output_log)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"status: {result['status']}")
        print(f"manifest_case_count: {result['manifest_case_count']}")
        if output_log:
            print(f"sanitized_log_path: {output_log}")
    return 0 if validation.get("status") == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
