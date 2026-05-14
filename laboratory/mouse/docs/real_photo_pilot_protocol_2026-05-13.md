# Real Photo Pilot Protocol - 2026-05-13

Layer classification: review item / non-canonical pilot protocol.

Canonical: false.

This protocol defines how to prepare the first real cage-card photo pilot dataset without turning real photos, manual labels, OCR output, AI drafts, or Excel rows into canonical colony truth. Canonical behavior remains defined by `AGENTS.md`, `final_mouse_colony_prd.md`, committed tests, and runtime code.

## Pilot Dataset Size

Prepare 20-30 cage-card photos for the first real-photo pilot.

Use copied files from non-destructive source storage. Keep the original lab source location unchanged. The copied pilot files remain `raw source` evidence and should be stored outside Git.

Recommended first-pass mix:

| Card type | Target count | Purpose |
| --- | ---: | --- |
| separated | 8-12 | Validate separated mouse note lines, sex/count, DOB, ear labels, and export grouping. |
| mating | 6-10 | Validate sire/dam IDs, mating dates, litter notes, pup counts, and animal sheet export rows. |
| unclear | 3-5 | Validate low-confidence routing, blurry/cropped cards, ambiguous note lines, and manual transcription. |
| other | 1-3 | Catch unexpected card formats without forcing a canonical interpretation. |

## Required Per-Photo Labels

Each copied pilot photo must have a local label record before running workflow evaluation. Labels are `review item / test fixture`, not canonical structured state.

Required fields:

| Field | Boundary | Requirement |
| --- | --- | --- |
| `case_id` | review item / test fixture | Stable local identifier such as `pilot_photo_001`. Do not include private animal-room details. |
| `source_photo_path` | raw source pointer | Local path to the copied pilot photo. Do not commit private paths if they reveal sensitive storage names. |
| `source_photo_filename` | raw source pointer | Copied filename or safe renamed filename. |
| `card_type` | review item / test fixture | One of `separated`, `mating`, `unclear`, or `other`. |
| `traceability_label` | review item / test fixture | Human-readable pilot label linking the case to the copied source, such as `Pilot batch A / photo 001`. |
| `expected_review_level` | review item / test fixture | One of `must_review`, `quick_check`, or `trace_only`. |
| `expected_export_blocking` | review item / test fixture | `true` when the case should block final export before review. |

## Manual Expected Values

Only record the values needed to evaluate whether the workflow routes evidence safely. Do not over-label full colony records.

Recommended expected fields:

| Expected field | Boundary | Notes |
| --- | --- | --- |
| `raw_strain_text` | parsed/intermediate expectation | Write what is visible on the card, including uncertainty markers if unclear. |
| `mouse_ids_or_note_lines` | review item / test fixture | Preserve raw note-line text where possible; mouse IDs and note lines are primary continuity anchors. |
| `sex_count` | parsed/intermediate expectation | Use visible text such as `M 3`, `F 6`, or `unclear`; do not infer hidden values. |
| `dob` | parsed/intermediate expectation | Preserve ambiguous dates as raw text. Add normalized date only if a human reviewer is confident. |
| `mating_or_litter_note` | review item / test fixture | For mating cards, capture sire/dam notes, pup notes, mating date, litter note, or `not visible`. |
| `expected_review_blockers` | review item / test fixture | List blockers such as `low_confidence`, `duplicate_active_mouse`, `ambiguous_date`, `count_mismatch`, `unclear_ear_label`, `outside_assigned_strain_scope`. |

## Safety Rules

- Do not send pilot photos to external OCR, LLM, or inference services unless the user explicitly approves that run.
- If external inference is approved, send only the selected source photo plus the minimal assigned-strain scope required for extraction.
- Keep source photos even when blurry, cropped, or unreadable.
- Keep raw visible text separate from normalized values.
- Treat OCR, local Tesseract output, and AI drafts as `parsed or intermediate result`.
- Route low-confidence, conflicting, biologically unlikely, or unclear evidence to review.
- Do not import predecessor Excel rows as canonical state. They may create review candidates only.
- Do not commit private photos, private manifests, local paths, generated OCR payloads, or pilot exports to Git unless explicitly adopted and scrubbed.

## Suggested Local Manifest Shape

Task 3 will add a private-photo-safe verifier. Use this shape for pilot labels:

```json
{
  "layer": "review item / test fixture",
  "canonical": false,
  "source_policy": "Local-only real-photo pilot labels. Do not commit private photos or private source paths.",
  "cases": [
    {
      "case_id": "pilot_photo_001",
      "source_photo_path": "C:/local/private/pilot/photos/pilot_photo_001.jpg",
      "source_photo_filename": "pilot_photo_001.jpg",
      "card_type": "separated",
      "traceability_label": "Pilot batch A / photo 001",
      "expected_review_level": "must_review",
      "expected_export_blocking": true,
      "expected_fields": {
        "raw_strain_text": "visible strain text or unclear",
        "mouse_ids_or_note_lines": ["raw note line 1", "raw note line 2"],
        "sex_count": "M 3",
        "dob": "26.04.13",
        "mating_or_litter_note": "",
        "expected_review_blockers": ["ambiguous_date"]
      }
    }
  ]
}
```

The example path is illustrative. Real manifests with private local paths should stay outside Git.

## Pilot Preparation Checklist

- [ ] Copy 20-30 photos into a local pilot folder outside Git.
- [ ] Confirm copied files open correctly before upload.
- [ ] Create one local label row per copied photo.
- [ ] Assign one of `separated`, `mating`, `unclear`, or `other` to each photo.
- [ ] Record only the minimum expected fields needed for workflow evaluation.
- [ ] Mark cases that should block export before review.
- [ ] Confirm the assigned strain scope before running AI extraction or review.
- [ ] Back up the local database and photo folder before a real pilot run.

## Readiness Criteria

For the 20-30 copied-photo pilot, add a `readiness_criteria` object to the private manifest. The verifier treats these values as `review item / test fixture` evidence, not canonical colony state.

Minimum readiness criteria:

- `photo_count.min=20` and `photo_count.max=30`.
- `required_card_types` includes `separated`, `mating`, `unclear`, and `other`.
- `required_review_levels` includes `must_review`, `quick_check`, and `trace_only`.
- `export_blocking` includes at least one blocking and one non-blocking expectation.
- `backup_restore` records only labels and booleans: before-backup label, after-backup label, restore-probe label, restore verified, and overwrite-refusal verified.

Do not put backup paths, restore target paths, local database paths, generated workbook paths, or raw copied-photo text in `readiness_criteria`. Use `docs/copied_photo_pilot_go_no_go_2026-05-14.md` for the full go/no-go decision.

## Completion Criteria

This protocol is ready when:

- The pilot photo set contains 20-30 copied photos.
- Every photo has a local label record with card type, traceability label, expected review level, and expected export-blocking state.
- The labels can be used by the real-photo verifier without requiring private photos to be committed.
- The verifier reports `readiness.status=go` for the private copied-photo pilot manifest.
- The operator can explain why each expected value is `raw source`, `parsed/intermediate`, `review item`, or `export/view`.
