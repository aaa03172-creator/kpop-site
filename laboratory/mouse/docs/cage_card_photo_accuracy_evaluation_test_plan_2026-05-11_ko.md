# Cage Card Photo Accuracy Evaluation And Test Plan

Layer classification: implementation verification plan / review item.
Canonical status: non-canonical. This plan defines tests for the cage-card
photo parsing, review, canonical apply, and Excel export pipeline.

Date: 2026-05-11

## Scope

Accuracy is evaluated as a data-boundary and traceability problem, not just OCR
string matching. The test surface covers:

1. photo upload and raw source preservation;
2. OCR, AI, and manual transcription draft storage;
3. field and note-line parsing;
4. raw extracted value versus normalized value separation;
5. review item creation and trigger metadata;
6. user correction before/after history;
7. guarded canonical candidate apply;
8. event creation with source evidence;
9. Excel preview/export provenance;
10. failure-path transaction safety.

## Boundary Criteria

| Object | Required boundary | Pass condition |
| --- | --- | --- |
| Uploaded original photo | raw source | Original photo remains stored and traceable even when parsing fails. |
| OCR, AI, or manual transcription | parsed or intermediate result | Output does not write canonical mouse state directly. |
| Field or note-line evidence | parsed or intermediate result | Raw, OCR, parsed, confidence, and interpretation fields remain distinguishable. |
| Low-confidence or conflicting value | review item | Review row includes reason, source evidence, and proposed value context. |
| Correction | review item / correction history | Before and after values plus source/review refs are preserved. |
| Canonical candidate | review item / non-canonical draft | Apply is blocked until validation and review gates pass. |
| Mouse, mating, litter, genotype, event state | canonical structured state | Accepted state has source refs or explicit blockers. |
| Excel preview/export | export or view | Export is generated from accepted state and never promoted as source truth. |

## Test Slices

### Slice 1: Parse Payload Boundary Tagging

Required tests:

- upload/manual-review placeholder payload has review-item boundary metadata;
- manual transcription payload has parsed/intermediate boundary metadata;
- AI extraction remains reviewable and does not create canonical state by itself;
- legacy workbook import payload is distinguishable from photo parse payloads.

### Slice 2: Photo Evidence Raw/OCR/Parsed Separation

Required tests:

- raw `sex_raw = "F"` remains raw evidence while normalized `female` is stored separately;
- raw note lines remain unchanged while parsed mouse IDs and ear labels are stored separately;
- correction changes parsed/interpreted state or correction history, not raw source text.

### Slice 3: Evidence Ref Propagation

Required tests:

- movement and weaning events preserve source photo, note item, and photo evidence refs when provided;
- invalid evidence refs fail before any partial assignment or event write;
- manual source-record fallback remains accepted for existing flows.

### Slice 4: Mating, Litter, And Offspring Evidence

Required tests:

- mating, litter, and offspring events inherit the most specific available evidence refs;
- invalid refs fail transactionally before registry, mouse, or event writes.

### Slice 5: Canonical Apply Validation

Required tests:

- missing note-line evidence blocks apply;
- unresolved note review blocks apply;
- duplicate active mouse IDs block apply;
- validation report remains an export/view and does not write canonical state.

### Slice 6: Correction To Evidence

Required tests:

- correction log stores before/after values, reason, source refs, and review refs;
- raw note line and observed raw evidence remain unchanged;
- audit view exposes correction context without hiding original evidence.

### Slice 7: Canonical Structured State Semantics

Required tests:

- card snapshot and canonical candidate remain non-canonical until guarded apply succeeds;
- successful apply writes accepted mouse/event state with evidence refs;
- action logs preserve before/after and source context.

### Slice 8: Excel Export Trace Completeness

Required tests:

- export rows come from accepted canonical state only;
- preview, separation, and animal-sheet rows have row-level trace fields;
- manifest/export log identifies blockers and stale export risk.

## Recommended Regression Command

```powershell
python -m pytest tests/test_photo_transcription_transactions.py tests/test_photo_evidence_ledger_schema.py tests/test_mouse_event_evidence_enforcement.py tests/test_genotyping_evidence_enforcement.py tests/test_artifact_workflow.py tests/test_legacy_workbook_import_api.py tests/test_cage_card_skill_gym.py -q
```

## Manual Validation Still Needed

- real-photo ground truth for clear, blurry, cropped, and dense note-line cards;
- handwritten mouse ID confidence calibration;
- configurable biological/date thresholds by strain and lab practice;
- genotype and mating/litter conflict semantics from lab-specific masters;
- Excel workbook visual QA and lab-sharing format review;
- correction UX review so raw evidence and corrected normalized values are not confused;
- external OCR/LLM payload minimization and approval review.
