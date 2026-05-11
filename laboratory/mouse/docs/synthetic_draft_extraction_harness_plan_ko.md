# Synthetic Draft Extraction Harness Plan

Layer classification: implementation planning / review item. Canonical: false.

## Goal

Add a local-only harness that takes the synthetic cage-card JPEG fixture set and
verifies the next extraction boundary: source image evidence can produce a
reviewable draft payload, the draft can be normalized, and uncertain or risky
fields stay reviewable instead of becoming canonical state.

## Current Local Constraint

This workstation does not currently expose a local OCR engine:

- `tesseract` is not on PATH;
- `pytesseract` is not installed;
- `cv2` is not installed.

Because of that, the first implementation uses the synthetic fixture's local
raw payload as an OCR surrogate. This is still useful because it exercises the
draft extraction, normalization, reviewability, confidence, and payload boundary
contracts without sending images or records to external services. A later
adapter can replace the surrogate with a real local OCR provider behind the same
script contract.

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
- The harness can run with a disposable temp directory and clean it up.
- Existing real-photo E2E and synthetic photo E2E gates still pass.
