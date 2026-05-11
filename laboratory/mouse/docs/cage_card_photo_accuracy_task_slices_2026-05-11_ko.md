# Cage Card Photo Accuracy Task Slices

Layer classification: implementation planning / review item.
Canonical status: non-canonical. This document slices future implementation
work for cage-card photo accuracy and traceability.

Date: 2026-05-11

## Goal

Improve cage-card photo accuracy by tightening the existing data pipeline rather
than replacing it. The priority is boundary clarity, review gates, and evidence
traceability across photo, parse, review, canonical apply, events, and export.

## Current Baseline

Already present:

- uploaded photos are preserved through `photo_log` and source records;
- manual and AI transcription output flows through `parse_result`,
  `card_snapshot`, `card_note_item_log`, and `photo_evidence_item`;
- ambiguous or conflicting values can create `review_queue` rows;
- corrections preserve before/after values in `correction_log`;
- canonical apply is transactional and writes `mouse_master` plus events;
- Excel preview/export is treated as an export/view.

Main gaps:

- `parse_result.raw_payload` still carries several payload shapes in one JSON column;
- some evidence rows do not clearly separate raw, OCR, parsed, and normalized values;
- domain-specific event flows need more specific evidence refs;
- canonical apply validation needs broader blocker coverage;
- export rows need consistent row-level trace checks.

## Recommended Slice Order

1. Parse payload boundary tagging.
2. Photo evidence raw/OCR/parsed separation.
3. Movement and weaning evidence ref propagation.
4. Mating, litter, and offspring evidence propagation.
5. Canonical apply validation coverage.
6. Correction to evidence propagation.
7. Canonical structured state apply semantics.
8. Excel export row trace completeness.

## Slice 1: Parse Payload Boundary Tagging

Purpose: distinguish upload placeholder, manual transcription, AI extraction,
legacy workbook parse, and fixture import payloads without splitting the table.

Completion criteria:

- new payloads include additive boundary tags;
- old readers still tolerate older payload shapes;
- no canonical table consumes raw payload JSON as accepted truth.

## Slice 2: Raw/OCR/Parsed Separation

Purpose: keep raw observed values, OCR/model text, parsed values, normalized
candidates, confidence, and interpretation separate.

Completion criteria:

- raw values are not overwritten by normalized or corrected values;
- evidence ledger responses expose the distinction;
- correction flows preserve raw evidence.

## Slice 3: Movement And Weaning Evidence Refs

Purpose: store source photo, note item, and photo evidence refs in event details
when those refs exist.

Completion criteria:

- optional refs are validated before mutation;
- invalid refs fail transactionally;
- manual source-record fallback remains compatible.

## Slice 4: Mating, Litter, And Offspring Evidence

Purpose: preserve source evidence through breeding history and offspring events.

Completion criteria:

- parent and offspring events carry inherited source refs;
- invalid refs do not leave partial registry or event writes.

## Slice 5: Canonical Apply Validation

Purpose: prevent review-needed or evidence-missing values from becoming
canonical state.

Completion criteria:

- missing note-line evidence blocks apply;
- unresolved note review blocks apply;
- duplicate active mouse IDs block apply;
- validation remains an export/view and does not mutate canonical state.

## Slice 6: Correction Propagation

Purpose: preserve correction provenance without overwriting raw source evidence.

Completion criteria:

- correction log stores before/after and evidence refs;
- audit view can reconstruct what changed and why.

## Slice 7: Apply Semantics

Purpose: keep snapshots and candidates non-canonical until guarded apply
succeeds.

Completion criteria:

- successful apply records accepted state, event details, and action log context;
- failed apply leaves no partial canonical state.

## Slice 8: Export Trace

Purpose: keep Excel previews and files as traceable views over accepted state.

Completion criteria:

- preview/export rows contain source refs or blockers;
- manifests record validation and stale-view context.
