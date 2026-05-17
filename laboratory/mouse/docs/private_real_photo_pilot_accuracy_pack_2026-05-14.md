# Private Real-Photo Pilot And Accuracy Evaluation Pack - 2026-05-14

Layer classification: review item / non-canonical pilot and evaluation runbook.

Canonical: false.

This pack defines the private 20-30 copied-photo pilot, the reusable private manifest shape, the sanitized public reporting shape, and the go/no-go gates for deciding whether real cage-card photo workflow accuracy is ready to expand. It does not make copied photos, OCR/AI output, manual labels, Excel rows, or exports canonical colony state. The committed example manifest is `config/copied_photo_pilot_readiness_manifest.example.json`; the committed sanitized example log is `docs/pilot_runs/2026-05-14-copied-photo-pilot-readiness-example.md`.

## Objective

Run a private pilot with 20-30 copied cage-card photos while keeping private photos, raw card text, local paths, OCR/AI payloads, generated workbooks, local databases, and backup paths out of Git. Reuse the same private manifest for accuracy evaluation, then commit only sanitized coverage, metrics, failure taxonomy, reviewer workload, and go/no-go results.

## Artifact Boundaries

| Artifact | Boundary | Git rule |
| --- | --- | --- |
| Original lab photo location | raw source | Never modify from this workflow. Do not commit. |
| Copied pilot photo | raw source | Store outside Git. Preserve even when blurry or unreadable. |
| Private manifest | review item / test fixture | Store outside Git because it contains local paths and raw expected values. |
| Raw OCR, local OCR, or AI draft | parsed or intermediate result | Store outside Git unless scrubbed and explicitly adopted. |
| Review correction record | review item | Preserve before/after values and traceability; publish only sanitized aggregates. |
| Applied candidate state | canonical structured state | Only after explicit reviewed apply with evidence trace. |
| XLSX or CSV export | export or view | Generated output; do not commit private pilot exports. |
| Sanitized run log | review item / pilot run log | May be committed after the checklist confirms no private data. |

## Private Manifest Design

The private manifest is the single local index for both pilot execution and accuracy scoring. It should be created outside Git and verified with `python scripts/verify-real-photo-pilot.py --manifest <private manifest>`.

Required manifest properties:

| Field | Requirement |
| --- | --- |
| `layer` | Exactly `review item / test fixture`. |
| `canonical` | Exactly `false`. |
| `source_policy` | States that private photos, source paths, raw text, OCR/AI payloads, and pilot exports stay local-only. |
| `readiness_criteria` | Defines 20-30 photo count, card-type coverage, review-level coverage, export-blocking expectations, and backup/restore evidence using labels and booleans only. |
| `cases` | 20-30 copied-photo cases for the full pilot. |

Required case properties:

| Field | Requirement |
| --- | --- |
| `case_id` | Stable sanitized label such as `pilot_photo_001`; do not encode animal-room details. |
| `source_photo_path` | Private path to the copied photo outside Git. The real value must not appear in committed docs. |
| `source_photo_filename` | Safe copied filename. |
| `card_type` | One of `separated`, `mating`, `unclear`, or `other`. |
| `traceability_label` | Sanitized label that links the case to the copied source without exposing local paths. |
| `expected_review_level` | One of `must_review`, `quick_check`, or `trace_only`. |
| `expected_export_blocking` | Boolean. Use `true` for any case that must block export until reviewed. |
| `expected_fields` | Raw visible expectations needed for accuracy scoring. Keep raw text private. |
| `accuracy_eval` | Local scoring instructions for the same expected fields. Publish only aggregate results. |

Private-only case template:

```json
{
  "case_id": "pilot_photo_001",
  "source_photo_path": "<private copied photo path outside Git>",
  "source_photo_filename": "pilot_photo_001.jpg",
  "card_type": "separated",
  "traceability_label": "20-30 copied-photo pilot / photo 001",
  "expected_review_level": "must_review",
  "expected_export_blocking": true,
  "expected_fields": {
    "raw_strain_text": "<raw visible text or unclear>",
    "mouse_ids_or_note_lines": ["<raw visible note line>"],
    "sex_count": "<raw visible sex/count or unclear>",
    "dob": "<raw visible date text or unclear>",
    "mating_or_litter_note": "<raw visible mating/litter note or not visible>",
    "expected_review_blockers": ["ambiguous_date"]
  },
  "accuracy_eval": {
    "score_fields": [
      "mouse_ids_or_note_lines",
      "card_type",
      "review_routing",
      "sex_count",
      "dob",
      "mating_or_litter_note",
      "export_traceability"
    ],
    "high_risk_fields": [
      "mouse_ids_or_note_lines",
      "dob",
      "mating_or_litter_note",
      "export_traceability"
    ],
    "publish_case_level_details": false
  }
}
```

## Coverage Targets

Use the manifest to balance the first full copied-photo pilot:

| Card type | Target count | Accuracy reason |
| --- | ---: | --- |
| `separated` | 8-12 | Mouse IDs, note-line continuity, sex/count, DOB, ear-label handling, and export grouping. |
| `mating` | 6-10 | Sire/dam context, mating/litter notes, pup counts, and event traceability. |
| `unclear` | 3-5 | Low-confidence routing, manual transcription, blurry/cropped evidence, and export blocking. |
| `other` | 1-3 | Unsupported or unexpected formats should remain trace-only unless reviewed. |

The pilot should contain 20-30 cases total. If the available private photo set cannot meet the mix, run a smaller private rehearsal first and do not mark the 20-30 pilot go.

## Runbook

1. Copy 20-30 photos from source storage into a private pilot folder outside Git. Do not move or rename original evidence.
2. Rename copied files to sanitized filenames if needed, then open each copied file once to confirm it is readable.
3. Create the private manifest using the shape above. Record raw visible expected values only in the private file.
4. Verify the manifest with `python scripts/verify-real-photo-pilot.py --manifest <private manifest>`. The verifier redacts the manifest path in its JSON summary; do not paste private failure values, raw expected text, or local paths into committed docs.
5. Generate a sanitized run-log shell with `python scripts/prepare-copied-pilot-run.py --manifest <private manifest> --run-label <label> --output-log docs/pilot_runs/YYYY-MM-DD-<label>.md`.
6. Review the generated log before committing. Remove any private source path, raw card text, OCR/AI payload, generated workbook path, local database path, backup path, or animal-room detail.
7. Run a pre-session local backup using the backup script documented in `docs/local_backup_restore_2026-05-13.md`.
8. Start the app and use the normal local browser UI or standalone Playwright for file upload/download checks. The in-app Browser control surface is not the private upload mechanism.
9. Upload copied photos. Confirm uploaded photos remain raw source evidence and that OCR/AI/manual drafts remain parsed or intermediate results.
10. Use external AI only after explicit approval for that run. If approved, send only the selected photo and minimal assigned-strain scope needed for extraction.
11. Resolve review items. Preserve before/after values for corrections and inferred state changes.
12. Apply only reviewed, source-backed canonical candidates. Do not silently overwrite high-risk data.
13. Generate XLSX export only when no unresolved `must_review` blocker remains.
14. Run a post-session backup and restore into a separate probe location before declaring go/no-go confidence.
15. Score accuracy locally from the same private manifest expected fields with `python scripts/report-private-accuracy.py --manifest <private manifest> --results <private scoring results> --output-report docs/pilot_runs/YYYY-MM-DD-<label>-accuracy.md --json`. Commit only aggregate counts, rates, failure taxonomy labels, workload metrics, and go/no-go status.

## Accuracy Evaluation Reuse

Use each manifest case as the local scoring row:

| Private manifest input | Local scoring output | Public reporting |
| --- | --- | --- |
| `expected_fields.mouse_ids_or_note_lines` | Exact/corrected/missed count for mouse IDs, ear labels, struck notes, and continuity notes. | Aggregate accuracy rate and failure labels only. |
| `card_type` and `expected_review_level` | Whether routing matched `must_review`, `quick_check`, or `trace_only`. | Routing rate, blocker catch rate, and false-pass count. |
| `sex_count` and `dob` | Whether raw and normalized values stayed separate and reviewed when ambiguous. | Aggregate correct-after-review rate and ambiguous-date failure count. |
| `mating_or_litter_note` | Whether sire/dam/mating/litter/pup context stayed traceable. | Aggregate correct-after-review rate and context-error count. |
| `expected_export_blocking` | Whether export was blocked until review cleared the case. | Export safety pass/fail and unresolved blocker count. |

Never publish case-level raw text from the manifest. If a public example is needed, write a synthetic example that is clearly not copied from a real photo.

The private scoring results file is a local-only review item. It should use `layer: "review item / private accuracy scoring input"` and `canonical: false`, then record sanitized `case_id` values, field-family scoring statuses, review timing, export blocking, traceability, and failure taxonomy labels. The reporter output is a sanitized aggregate report, not canonical colony state.

## Sanitized Public Summary

A committed pilot log may include:

| Public section | Allowed content |
| --- | --- |
| Coverage summary | Case count, card-type counts, review-level counts, export-blocking counts. |
| Sanitized metrics | Upload counts, extraction counts, review counts, correction counts, export counts, backup/restore status. |
| Failure taxonomy | Labels and aggregate counts, with generic definitions. |
| Reviewer workload | Median/90th percentile review time, manual transcription rate, unresolved blocker count. |
| Accuracy criteria | Aggregate field-family rates and hard-gate pass/fail. |
| Go/no-go decision | Go, no-go, or narrow rerun, with sanitized reasons. |

A committed pilot log must not include:

- Private photos.
- Raw card text or raw expected field values.
- Local absolute or relative private paths.
- Raw OCR/AI payloads.
- Generated private workbooks.
- Local database, backup, or restore paths.
- Animal-room details beyond sanitized case labels.

## Failure Taxonomy

Use the same labels in the generated sanitized run log and any public summary:

| Failure label | Meaning |
| --- | --- |
| `source_trace_missing` | Candidate, review item, or export row lost traceability to copied photo or note evidence. |
| `low_confidence_unreviewed` | Low-confidence extraction output could proceed without review. |
| `raw_normalized_mixed` | Raw visible text and normalized values were mixed or unclear. |
| `mouse_id_or_note_line_error` | Mouse ID, ear label, struck note, or continuity note was missing, merged, split, or attached to the wrong field. |
| `date_or_count_error` | DOB, mating date, litter date, sex count, or pup count was wrong or normalized without adequate review. |
| `mating_litter_context_error` | Sire, dam, mating, litter, or pup note context was lost or attached to the wrong event. |
| `export_safety_error` | Export included unresolved blockers, stale values, or rows without evidence trace. |
| `privacy_leak` | Public artifact exposed private photos, raw text, local paths, OCR/AI payloads, generated workbook paths, local database paths, or animal-room details. |
| `operator_workload_excessive` | Review time, correction count, or unresolved ambiguity exceeded the workload criteria. |

## Go / No-Go Criteria

Hard gates:

| Gate | Go threshold |
| --- | --- |
| Manifest coverage | 20-30 verified copied-photo cases with separated, mating, unclear, and other/unknown represented. |
| Private data containment | 0 private photos, raw text, local paths, OCR/AI payloads, generated workbooks, local database paths, or backup paths in committed artifacts. |
| Source preservation | 100% of copied source photos retained; originals unchanged. |
| Traceability | 100% of applied candidates and exported rows trace to a source photo, note item, or accepted review correction. |
| Review blocking | 0 unresolved `must_review` items at export time. |
| Silent overwrite prevention | 0 high-risk corrections or inferred state changes without before/after preservation. |
| Mouse IDs and note-line continuity | At least 95% exact or reviewer-corrected before apply; 0 unreviewed high-risk misses. |
| Card type and review routing | 100% of unclear/blocker cases route to review; unsupported cards are not forced into canonical state. |
| Sex/count and date handling | At least 90% correct after review; ambiguous dates remain raw until reviewer confirmation. |
| Mating/litter context | At least 90% correct after review; sire/dam/litter notes remain evidence-traceable. |

Soft gates:

| Gate | Go threshold |
| --- | --- |
| Median review time | At or below 4 minutes per photo. |
| 90th percentile review time | At or below 8 minutes per photo. |
| Manual transcription rate | At or below 40% unless the run intentionally over-samples unclear cards. |
| Failure classification | 100% of observed failures assigned to a public taxonomy label or a new sanitized label. |

Decision rules:

- Go: all hard gates pass, soft gates pass or have a narrow documented mitigation.
- Narrow rerun: all safety hard gates pass, but one or more accuracy/workload gates need a targeted 5-10 photo rerun.
- No-go: any privacy, source preservation, traceability, review blocking, silent overwrite, or export safety hard gate fails.

## Completion Checklist

- [ ] Private manifest is outside Git.
- [ ] Manifest verifies with 20-30 copied-photo cases.
- [ ] Sanitized run log includes coverage summary, sanitized metrics, failure taxonomy, reviewer workload, accuracy criteria, and go/no-go criteria.
- [ ] Accuracy scoring reused the same manifest expected fields locally.
- [ ] Public artifacts contain no private photos, raw text, local paths, OCR/AI payloads, generated workbook paths, local database paths, backup paths, or animal-room details.
