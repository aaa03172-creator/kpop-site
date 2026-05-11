# Synthetic Cage Card Fixture Validation

Layer classification: review item / test fixture. Canonical: false.

## Purpose

This workflow creates local-only synthetic cage-card images, a matching
validation manifest, and a SQLite fixture database so the photo E2E verifier can
exercise parser and review-routing safety contracts without touching real lab
photos or the operational database.

## Run

```powershell
$out = Join-Path $env:TEMP 'synthetic-cage-cards'
python scripts/generate_synthetic_cage_card_fixtures.py $out
python scripts/verify-photo-e2e-cases.py `
  --manifest (Join-Path $out 'synthetic_photo_e2e_validation_cases.json') `
  --db-path (Join-Path $out 'synthetic_photo_e2e.sqlite') `
  --require-fixtures
```

Expected result: five synthetic cases pass. The generated set covers clear,
low-confidence, dense-note, cropped/blurry, ear-label ambiguity, and numeric-note
contracts.

## Boundaries

- The generated images are synthetic local validation fixtures, not raw colony
  evidence.
- The generated SQLite database is disposable test data.
- The manifest is a review/test contract and must not be treated as canonical
  colony state.
- Do not send the generated payloads or images to external OCR, LLM, or
  inference services unless the user explicitly approves that payload.
