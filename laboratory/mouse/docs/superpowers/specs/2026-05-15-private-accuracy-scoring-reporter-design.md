# Private Accuracy Scoring Reporter Design

Layer classification: review item / non-canonical implementation design.

Canonical: false.

## Objective

Add a local-only reporter that scores the private copied-photo pilot against the same private manifest used for readiness. The reporter must publish only sanitized aggregate accuracy, workload, failure taxonomy, and go/no-go results. It must not publish private photos, source paths, raw cage-card text, OCR/AI payloads, local databases, generated workbooks, backup paths, or animal-room details.

## Data Boundaries

| Artifact | Boundary | Rule |
| --- | --- | --- |
| Private manifest | review item / test fixture | Input only; may contain source paths and raw expected values; never echoed. |
| Private scoring results JSON | review item / private accuracy scoring input | Input only; may contain case-level workflow observations; never committed if it contains private details. |
| Field-family score aggregates | review item / sanitized private accuracy report | Safe to publish when it contains counts, rates, thresholds, and labels only. |
| Markdown report | review item / sanitized private accuracy report | Safe to commit after the checklist confirms no private paths or raw values. |

## Inputs

The script is `scripts/report-private-accuracy.py`.

It accepts:

- `--manifest <private manifest>`: the same manifest verified by `scripts/verify-real-photo-pilot.py`.
- `--results <private results JSON>`: local scoring observations keyed by sanitized `case_id`.
- `--output-report <markdown path>`: optional sanitized Markdown report.
- `--json`: prints the sanitized aggregate summary.

The private results JSON must use:

```json
{
  "layer": "review item / private accuracy scoring input",
  "canonical": false,
  "source_policy": "Local-only scoring input. Publish aggregates only.",
  "workflow_metrics": {
    "photos_uploaded": 20,
    "photos_with_extraction_draft": 20,
    "manual_transcriptions": 3,
    "review_items_opened": 12,
    "review_items_corrected": 5,
    "review_items_accepted_without_correction": 7,
    "xlsx_exports_generated": 1
  },
  "cases": [
    {
      "case_id": "pilot_photo_001",
      "actual_review_level": "quick_check",
      "export_blocked_until_resolved": false,
      "unresolved_must_review_at_export": false,
      "source_preserved": true,
      "silent_overwrite": false,
      "review_seconds": 180,
      "manual_transcription_required": false,
      "failure_labels": [],
      "field_scores": {
        "mouse_ids_or_note_lines": {
          "status": "exact",
          "reviewed_before_apply": true,
          "traceable": true
        }
      }
    }
  ]
}
```

Field score `status` values are `exact`, `corrected`, `missed`, and `not_applicable`. `corrected` only counts as passing when `reviewed_before_apply` is true.

## Scoring Model

The reporter aggregates five field families:

| Field family | Go threshold |
| --- | ---: |
| Mouse IDs and note-line continuity | 95% |
| Card type and review routing | 100% |
| Sex/count and DOB/date handling | 90% |
| Mating/litter context | 90% |
| Export provenance | 100% |

Missing scoring cases fail the accuracy gate. Observed missed high-risk field scores also fail when they were not reviewed before apply.

## Gates

The output decision is:

- `go`: all hard gates pass and workload passes.
- `narrow_rerun`: all hard gates pass but workload exceeds the soft thresholds.
- `no_go`: any hard gate fails.

Hard gates cover manifest validation, source preservation, traceability, review blocking, silent overwrite prevention, and accuracy thresholds. Workload is soft and uses median review seconds, 90th percentile review seconds, and manual transcription rate.

## Privacy Controls

The reporter does not include manifest path, results path, source photo paths, raw expected fields, or case-level raw text in `build_report()` output. The optional Markdown report contains only counts, rates, labels, thresholds, and the sanitization checklist.

## Verification

The focused test suite is:

```powershell
python -m pytest tests/test_private_accuracy_reporter.py -q
```

The tests cover:

- passing aggregate scoring with raw manifest values omitted;
- no-go scoring for missing cases, traceability failure, and silent overwrite;
- CLI Markdown generation without manifest or results path leakage;
- package command exposure through `npm run pilot:private-accuracy -- ...`.
