# Copied Pilot Run Log - copied-photo-pilot-readiness-example

Layer classification: review item / pilot run log.

Canonical: false.

Generated at: 2026-05-14 14:36:37

This sanitized log was prepared from a private copied-photo manifest. It intentionally omits private photo paths, raw OCR/AI payloads, generated workbook paths, local database paths, and backup folder paths.

## Preflight

| Check | Result |
| --- | --- |
| Manifest validation | passed |
| Manifest used | private manifest verified; path intentionally omitted |
| Case count | 20 |
| Data boundary | review item / test fixture |
| Source photos | raw source copied outside Git |

## Manifest Coverage

| Coverage | Counts |
| --- | --- |
| Card types | {"mating": 7, "other": 2, "separated": 8, "unclear": 3} |
| Review levels | {"must_review": 10, "quick_check": 8, "trace_only": 2} |
| Export blocking | {"blocking": 10, "non_blocking": 10} |

## Sanitized Metrics To Publish

Publish only aggregate counts and rates from the copied-photo run. Do not publish private photo paths, raw card text, raw OCR/AI payloads, local database paths, generated workbook paths, or case-level animal-room details.

| Metric | Sanitized value |
| --- | ---: |
| Manifest cases verified | 20 |
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
| Go/no-go | go | |
| photo_count | passed | {"actual": 20, "expected": {"max": 30, "min": 20}} |
| card_type_coverage | passed | {"missing": [], "required": ["separated", "mating", "unclear", "other"]} |
| review_level_coverage | passed | {"missing": [], "required": ["must_review", "quick_check", "trace_only"]} |
| export_blocking_expectations | passed | {"actual": {"blocking": 10, "non_blocking": 10}, "minimum_blocking": 1, "minimum_non_blocking": 1} |
| backup_restore_evidence | passed | {"after_backup_label": "after-20-photo-readiness-example", "before_backup_label": "before-20-photo-readiness-example", "overwrite_refusal_verified": true, "restore_probe_label": "restore-probe-20-photo-readiness-example", "restore_verified": true} |

## Per-Photo Private Manifest Summary

| Case/photo label | Card type | Expected review level | Export blocking? | Private path status |
| --- | --- | --- | --- | --- |
| pilot_photo_001 | separated | quick_check | false | private source photo path omitted |
| pilot_photo_002 | separated | must_review | true | private source photo path omitted |
| pilot_photo_003 | separated | quick_check | false | private source photo path omitted |
| pilot_photo_004 | separated | must_review | true | private source photo path omitted |
| pilot_photo_005 | separated | quick_check | false | private source photo path omitted |
| pilot_photo_006 | separated | must_review | true | private source photo path omitted |
| pilot_photo_007 | separated | quick_check | false | private source photo path omitted |
| pilot_photo_008 | separated | must_review | true | private source photo path omitted |
| pilot_photo_009 | mating | must_review | true | private source photo path omitted |
| pilot_photo_010 | mating | quick_check | false | private source photo path omitted |
| pilot_photo_011 | mating | must_review | true | private source photo path omitted |
| pilot_photo_012 | mating | quick_check | false | private source photo path omitted |
| pilot_photo_013 | mating | must_review | true | private source photo path omitted |
| pilot_photo_014 | mating | quick_check | false | private source photo path omitted |
| pilot_photo_015 | mating | must_review | true | private source photo path omitted |
| pilot_photo_016 | unclear | must_review | true | private source photo path omitted |
| pilot_photo_017 | unclear | must_review | true | private source photo path omitted |
| pilot_photo_018 | unclear | quick_check | false | private source photo path omitted |
| pilot_photo_019 | other | trace_only | false | private source photo path omitted |
| pilot_photo_020 | other | trace_only | false | private source photo path omitted |

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
