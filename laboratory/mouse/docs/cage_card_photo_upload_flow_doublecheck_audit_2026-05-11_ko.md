# Cage Card Photo Upload Flow Doublecheck Audit

Layer classification: implementation audit / review item.
Canonical status: non-canonical. If this audit conflicts with `AGENTS.md`,
`final_mouse_colony_prd.md`, accepted tests, or later adopted documents, call
out the mismatch before implementation.

Date: 2026-05-11

## Scope

This audit doublechecks the current flow after cage-card photo upload:

- raw photo preservation;
- OCR, AI, and manual extraction boundaries;
- parsed result storage;
- raw extracted value versus normalized value separation;
- confidence and source evidence storage;
- review item creation;
- user correction storage;
- canonical apply safety;
- Excel preview/export relationship;
- partial write, orphan record, duplicate record, and stale export risks.

## Current Flow

### Photo Upload

Uploaded images are stored locally and registered in `photo_log`. The file and
photo row are raw source. Upload also creates a reviewable parse placeholder so
the photo cannot silently become canonical state.

### AI And Manual Transcription

AI extraction requires explicit external inference approval. AI and manual
transcriptions are parsed/intermediate results, not canonical records. Stored
transcriptions create snapshots, note rows, photo evidence rows, and review
items.

### Evidence Ledger

The strongest trace path is:

`photo_log -> parse_result -> card_snapshot -> card_note_item_log -> photo_evidence_item -> review_queue -> canonical_candidate -> mouse_master/mouse_event`

The current improvement adds stronger source-layer columns, raw/normalized
evidence fields, confidence source metadata, and JSON evidence references.

### Review And Correction

Review items remain review-layer records. Corrections store before/after values
plus source and review refs. Raw note lines and source photos must not be
overwritten by correction flows.

### Canonical Apply

Canonical apply should only write accepted state after validation. The tightened
checks block apply when note-line review remains unresolved or when a proposed
mouse row lacks note-line photo evidence.

### Excel Export

Excel preview/export remains an export/view. The export consistency checks verify
that preview, separation, and animal-sheet rows contain source refs where
available and never become the source of truth.

## Doublecheck Findings

Strengths:

- raw photo preservation is aligned with the product principles;
- transcription output remains reviewable;
- focused tests now exercise evidence metadata and apply blockers;
- export consistency checks make stale or untraceable views easier to detect.

Remaining gaps:

- real-photo OCR confidence needs calibration;
- domain-specific breeding and movement endpoints still need broader evidence
  propagation;
- biological rules must remain configurable;
- Excel visual QA still needs manual review;
- external inference payload shape must remain minimized and approval-gated.

## Verification Command

```powershell
python -m pytest tests/test_photo_transcription_transactions.py tests/test_photo_evidence_ledger_schema.py tests/test_mouse_event_evidence_enforcement.py tests/test_genotyping_evidence_enforcement.py tests/test_artifact_workflow.py tests/test_legacy_workbook_import_api.py tests/test_cage_card_skill_gym.py -q
```
