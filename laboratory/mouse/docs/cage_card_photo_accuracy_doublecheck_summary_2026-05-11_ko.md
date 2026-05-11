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
  views.

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

## Remaining Risks

- Real-photo OCR confidence still needs ground-truth calibration.
- Domain-specific mating, litter, offspring, movement, and weaning flows still
  need broader evidence propagation checks.
- Biological/date thresholds must remain configurable rather than hard-coded.
- Excel workbook visual QA still needs manual lab-format review.
- External OCR/LLM payload minimization still needs operator approval review for
  any new provider or payload shape.
