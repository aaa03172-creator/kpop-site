# Synthetic Draft Extraction Harness Plan

Layer classification: implementation planning / review item. Canonical: false.

## Goal

Add a local-only harness that takes the synthetic cage-card JPEG fixture set and
verifies the next extraction boundary: source image evidence can produce a
reviewable draft payload, the draft can be normalized, and uncertain or risky
fields stay reviewable instead of becoming canonical state.

## Current Local OCR Status

This workstation currently exposes local Tesseract OCR on PATH, so the harness
can probe generated synthetic JPEGs without sending photos, draft payloads, or
source records to an external OCR/LLM/inference service.

The fixture raw payload is still used as the deterministic draft surrogate for
normalization and reviewability checks. The Tesseract probe is a local-only raw
text quality report beside that surrogate: it measures whether OCR produced any
text, whether expected note-line hints were seen, text length range, a simple
quality grade, case-level review actions, coverage-tag summaries, and weak-spot
findings that make empty or garbled card types visible. If Tesseract is
unavailable on another workstation, the same script reports a skipped local OCR
probe and keeps the run local.

## Data Boundaries

| Artifact | Layer | Canonical |
| --- | --- | --- |
| Synthetic JPEG | raw source / test fixture | false |
| Extracted draft payload | parsed or intermediate result | false |
| Normalized draft payload | parsed or intermediate result | false |
| Harness report | review item / test fixture | false |
| Generated output directory | cache / disposable test artifact | false |

## First Slice

1. Generate the existing synthetic JPEG fixture set into a disposable directory.
2. Read each generated fixture row from the synthetic SQLite database.
3. Build a local draft extraction result from the fixture raw payload.
4. Normalize the draft with the existing draft normalizer.
5. Verify:
   - no external inference is used;
   - local OCR provider availability is reported explicitly;
   - local OCR probe status is reported explicitly;
   - local OCR raw text quality reports empty OCR cases, note-line hint
     matches, text length range, quality grades, case-level review actions,
     coverage-tag summaries, and weak-spot findings;
   - source photo IDs and filenames are preserved;
   - every draft remains non-canonical;
   - low-confidence and ambiguous cases remain reviewable;
   - clear cases can be trace-only but still keep source evidence.
6. Expose the harness as `npm run test:synthetic-draft-extraction`.

## Run

```powershell
npm run test:synthetic-draft-extraction
```

For debugging, keep generated fixtures in a chosen folder:

```powershell
python scripts/verify-synthetic-draft-extraction.py `
  --output-dir $env:TEMP\synthetic-draft-extraction `
  --json
```

## Success Criteria

- The script reports five generated synthetic cases.
- All five draft extraction cases pass.
- The report has `source_policy` stating local-only, no external inference.
- The report has `ocr_provider`, `local_ocr_probe`, and
  `local_ocr_probe.quality_report` status. If Tesseract is unavailable, the
  harness reports `extraction_mode: fixture_payload_surrogate`, reports
  `local_ocr_probe.status: skipped`, emits a zero-count `quality_report`, and
  keeps the run local.
- The local OCR quality report classifies cases as `empty`, `garbled`,
  `partial_note_match`, or `usable_note_match`, and groups those outcomes by
  synthetic coverage tag such as `cropped_or_blurry`, `ear_label_ambiguity`,
  `numeric_notes`, and `dense_notes`.
- The local OCR quality report emits `quality_findings` for coverage tags with
  empty or garbled OCR so those card types stay review-first and can guide
  future local preprocessing work.
- Each local OCR case includes `review_required`, `canonical_write: false`, and
  `recommended_action` so OCR output remains a review aid rather than an
  acceptance path.
- The harness can run with a disposable temp directory and clean it up.
- Existing real-photo E2E and synthetic photo E2E gates still pass.
