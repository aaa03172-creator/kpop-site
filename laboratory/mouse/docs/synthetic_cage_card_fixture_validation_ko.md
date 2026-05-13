# Synthetic Cage Card Fixture Validation

Layer classification: review item / test fixture. Canonical: false.

## Purpose

This workflow creates local-only synthetic cage-card JPEG images, a matching
validation manifest, and a SQLite fixture database so the photo E2E verifier can
exercise parser and review-routing safety contracts without touching real lab
photos or the operational database. The JPEG renderer adds deterministic
photo-like perturbations such as blur, slight rotation, crop-like framing, and
pixel noise.

`npm run test:photo-e2e` is the default strict photo E2E gate for CI and local
verification. It must generate disposable synthetic/anonymized fixtures, report
`skipped: 0`, cover every recommended photo E2E tag, and preserve explicit layer
boundaries for raw source fixtures, parsed evidence, review items, and export
views. Real lab-photo fixture validation remains available as an optional
local-only check through `npm run test:real-photo-e2e`; it is not required for
`npm run verify` because raw lab photos and sensitive source records should not
be committed.

## Run

```powershell
$out = Join-Path $env:TEMP 'synthetic-cage-cards'
python scripts/generate_synthetic_cage_card_fixtures.py $out
python scripts/verify-photo-e2e-cases.py `
  --manifest (Join-Path $out 'synthetic_photo_e2e_validation_cases.json') `
  --db-path (Join-Path $out 'synthetic_photo_e2e.sqlite') `
  --require-fixtures
```

Or run the disposable one-command gate:

```powershell
npm run test:photo-e2e
```

Expected result: five synthetic JPEG cases pass. The generated set covers clear,
low-confidence, dense-note, cropped/blurry, ear-label ambiguity, and numeric-note
contracts. Each manifest case includes `synthetic_source.rendering:
local_jpeg_photo_simulation`.

The compatibility alias remains available:

```powershell
npm run test:synthetic-photo-e2e
```

To check a lab-owned local real-photo fixture database without committing those
photos or records:

```powershell
npm run test:real-photo-e2e
```

## Boundaries

- The generated images are synthetic local validation fixtures, not raw colony
  evidence.
- The generated SQLite database is disposable test data.
- The manifest is a review/test contract and must not be treated as canonical
  colony state.
- The generated parse payloads are parsed or intermediate evidence, and the
  generated review rows are review items.
- The strict gate writes no Excel export files; export readiness remains an
  export or view concern outside this fixture database.
- Do not send the generated payloads or images to external OCR, LLM, or
  inference services unless the user explicitly approves that payload.
