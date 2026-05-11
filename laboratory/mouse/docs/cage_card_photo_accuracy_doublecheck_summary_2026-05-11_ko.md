# Cage Card Photo Accuracy Doublecheck Summary

Layer classification: implementation verification summary / review item.
Canonical status: non-canonical. If this document conflicts with `AGENTS.md`,
`final_mouse_colony_prd.md`, committed tests, or the full evaluation plan, use
those sources first and call out the mismatch.

Date: 2026-05-11

## Result

The current implementation direction is valid only if it stays additive and
evidence-backed. The useful next slice is not a new OCR engine or a schema
rewrite. It is a set of boundary and provenance checks around the existing photo
pipeline:

- preserve uploaded cage-card photos as raw source;
- keep OCR, AI, and manual transcription output as parsed/intermediate state;
- keep raw extracted values separate from normalized or corrected values;
- require review for low-confidence, conflicting, or biologically unlikely data;
- block canonical apply when source note-line evidence is missing or unresolved;
- keep Excel preview/export as an export/view with row-level trace.

## Verified Coverage

Focused tests now cover:

- source-layer columns for raw photos, parse results, review items, corrections,
  and photo evidence;
- raw extracted value versus normalized value storage in `photo_evidence_item`;
- confidence source and machine-readable evidence references for evidence rows;
- review trigger metadata for transcription review items;
- correction before/after context and review/source evidence references;
- canonical apply blockers for unresolved note review and missing note-line
  evidence;
- canonical apply event details that carry `photo_evidence_id`;
- export preview consistency checks that assert export rows remain traceable
  views;
- domain-specific movement, weaning, mating, litter, and offspring event flows
  preserving specific photo, note-line, and photo-evidence refs;
- timeline read models exposing event evidence traces without exposing review
  item details;
- action-log read models exposing before/after values as an export/view;
- external AI draft responses recording explicit approval and payload-review
  metadata;
- real-photo E2E calibration output with required fixture mode, confidence
  bands, low-confidence guard cases, and coverage tags for clear,
  low-confidence, cropped/blurry, and dense-note examples;
- export manifests that explicitly mark workbook visual QA as a manual
  lab-format review boundary.

## Verification Run

Focused commands run successfully:

```powershell
python -m pytest tests/test_photo_transcription_transactions.py tests/test_photo_evidence_ledger_schema.py tests/test_mouse_event_evidence_enforcement.py tests/test_genotyping_evidence_enforcement.py tests/test_artifact_workflow.py tests/test_legacy_workbook_import_api.py tests/test_cage_card_skill_gym.py -q
python -m pytest tests/test_review_attention.py -q
git diff --check
```

Observed result:

- focused photo/evidence/export set: 37 passed;
- review attention set: 31 passed;
- `git diff --check`: passed, with only existing Windows CRLF warnings.

Additional current gate:

```powershell
python scripts/verify-photo-e2e-cases.py --require-fixtures --json
npm run verify
```

Observed current result:

- real-photo E2E fixture set: 5 passed, 0 failed, 0 skipped;
- confidence calibration bands: one `0_20_must_review` case and four
  `60_100_clearer` cases;
- recommended real-photo coverage tags: no missing tags for the current
  clear, low-confidence, cropped/blurry, and dense-note categories;
- full repository verification: 186 Python tests passed after MVP,
  acceptance, local app, photo E2E, and skill-gym gates.

## Remaining Risks

- Real-photo OCR confidence has an initial local five-case calibration gate;
  more photos should still be added as the lab collects new card patterns.
- Domain-specific movement, weaning, mating, litter, and offspring flows now
  preserve specific evidence refs in focused tests; future domain event flows
  should follow the same helper instead of adding one-off trace fields.
- Biological/date thresholds must remain configurable rather than hard-coded.
- Excel workbook visual QA is now explicit in export manifests, but the
  actual lab-format review remains a manual handoff step.
- External OCR/LLM payload minimization now records approval and payload-review
  metadata for the current draft flow; any new provider or payload shape still
  needs operator approval review before use.
