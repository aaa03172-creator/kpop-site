# Cage Card Photo Pipeline Implementation Baseline

Layer classification: implementation baseline / non-canonical project documentation.
Canonical status: non-canonical. This document summarizes implementation rules from `AGENTS.md`, `final_mouse_colony_prd.md`, adopted supporting documents, current artifact contracts, and executable tests. If this document conflicts with `AGENTS.md`, `final_mouse_colony_prd.md`, committed runtime behavior, or tests, call out the mismatch before implementation.

Date: 2026-05-11

## Purpose

This document defines the recommended implementation baseline for the cage-card photo processing pipeline.

The baseline is not a new schema by itself. It is a guardrail for future audits and implementation work so that photo parsing, review, canonical apply, and Excel export remain aligned with the product direction.

## Recommended Baseline

### 1. Preserve the handwritten workflow

The system must assist the lab's handwritten cage-card workflow, not replace it.

Implementation should prioritize:

- photo upload;
- transcription or OCR draft;
- review and correction;
- canonical candidate preview;
- validation;
- accepted state update;
- Excel preview/export.

It should not require animal-room app usage, QR codes, barcodes, or a new cage-card writing workflow for MVP.

### 2. Treat original photos as raw source

Uploaded cage-card photos are `raw source`.

Rules:

- Store the original photo even when it is blurry, occluded, rotated, or partially unreadable.
- Do not replace the original with a crop, ROI image, normalized image, OCR text, or AI summary.
- Derived images such as upright normalized cards and ROI crops are parsed/intermediate artifacts or cache, not the raw source.
- Every downstream parsed field, review item, canonical candidate, event, and export row should retain a path back to the source photo when applicable.

### 3. Keep OCR, AI, and manual transcription non-canonical until accepted

OCR text, AI extraction, ROI parsing, and manual transcription drafts are `parsed or intermediate result`.

They may create:

- parsed fields;
- note-line candidates;
- `photo_evidence_item` rows;
- review items;
- canonical write candidates.

They must not directly overwrite canonical mouse, cage, mating, litter, genotype, or event state.

Future LLM output should be treated as parsed/intermediate data, not canonical truth.

### 4. Separate raw extracted values from normalized values

The implementation must store raw evidence separately from normalized or selected meaning.

Examples:

- `sex_raw` remains as written or extracted, while `sex_normalized` may be `male`, `female`, `mixed`, `unknown`, or `not_visible`.
- Raw note-line text remains unchanged, while parsed mouse ID, parsed ear-label code, strike status, and interpreted status are stored separately.
- Raw ear-label tokens such as `R0`, `R'`, or `R°` remain visible, while normalized codes such as `R_PRIME`, `R_CIRCLE`, `NONE`, or `UNREADABLE` remain separate.
- Raw strain text remains visible, while matched assigned strain or strain master candidate remains separate.

Correction flows must preserve before and after values. Corrected or selected values must not erase OCR text, raw note text, raw workbook cells, or observed photo evidence.

### 5. Use note lines and mouse IDs as continuity anchors

The cage-card `I.D` field is not a stable physical cage ID. It can contain a prefix, parent IDs, individual mouse IDs, a loose group identifier, or nothing useful.

Continuity should be based on:

- mouse display IDs;
- note-line evidence;
- source photo;
- strain and assigned strain scope;
- DOB or DOB range;
- sex/count evidence;
- ear-label evidence;
- mating date or litter-note context;
- previous accepted state and event history.

Internal IDs such as `record_id`, `card_snapshot_id`, or hidden UUIDs may be used by the implementation, but they should not become user-facing lab concepts unless needed for debugging.

### 6. Treat card records as snapshots and durable history as events

A cage/card record is a source-backed observation at a point in time. It is useful for current state display, review, reconciliation, and export. It is not durable history by itself.

Durable history should be represented as events and logs, such as:

- mouse created or born;
- separated;
- moved;
- assigned to mating;
- litter recorded;
- genotyped;
- dead;
- used;
- closed;
- corrected or updated.

Movement, death, mating, litter, genotype, and identity-changing corrections should write event/action/correction history with evidence refs and before/after values.

### 7. Route uncertainty and risk to review

The pipeline must create review items or blockers for high-risk or uncertain records.

Must review or block before canonical apply:

- low-confidence identity fields;
- missing or outside-scope strain;
- ambiguous ear label, especially prime versus circle ambiguity;
- unclear strike-through status when it affects movement, death, or litter events;
- duplicate active mouse ID;
- count mismatch between sex/count and active note lines;
- biologically unlikely or impossible dates;
- genotype conflict;
- cage/card mismatch without movement evidence;
- missing source trace;
- conflicting Excel or predecessor state.

Review burden reduction is allowed only as presentation policy. It may move low-risk items into quick check, trace-only, or hidden-by-default views, but it must not let high-risk canonical writes bypass review and validation.

### 8. Preserve user correction evidence

User correction is a review/action boundary, not a silent overwrite.

For each correction or inferred high-risk state change, preserve:

- target entity and field;
- before value;
- after value;
- source photo, note item, imported row, source record, or manual source;
- review reason or resolution note;
- timestamp and action log/correction log entry.

For identity-sensitive corrections, raw evidence remains unchanged and the accepted interpretation is stored separately.

### 9. Use configurable masters and policies

Do not hard-code:

- strain names;
- genotype categories;
- target genotypes;
- PCR protocols;
- date rules;
- breeding operation thresholds;
- labeling session behavior;
- export templates.

These values should come from configurable masters, seed data, policy files, or user-approved assigned strain scope. Seed examples are acceptable in MVP, but they should not be scattered as generic domain logic.

### 10. Treat Excel as import/export view

Excel files are not the source of truth.

Rules:

- Existing workbooks may be raw sources, predecessor snapshots, assignment references, or template references.
- Imported workbook rows must preserve filename, sheet, row, and cell evidence where available.
- Distribution workbooks should update `My Assigned Strains` only after review or explicit user action.
- Excel exports must be generated from accepted structured state, not from OCR drafts alone.
- Export preview and final export should preserve provenance through export logs or export manifests.
- Blocked exports should log intended filename, blocker count, and blocker preview without creating a misleading final workbook artifact.

### 11. Standardize preview-before-commit

High-risk state changes must use preview-before-commit.

Recommended flow:

1. Raw source photo or workbook row is stored.
2. Parsed/intermediate draft is created.
3. Review items are created for uncertainty or conflict.
4. A canonical write candidate is created only from reviewed or policy-approved evidence.
5. Apply preview or proposed changeset shows target writes, before/after values, evidence refs, and blockers.
6. Deterministic validation report runs before apply.
7. User-approved apply writes canonical state and related event/action logs in one transaction.
8. Export preview and export readiness use accepted state only.

Important wording: `canonical_candidate` and proposed changeset artifacts are not canonical state. They are reviewable canonical-write candidates. Canonical state exists only after successful guarded apply to canonical tables and event/action logs.

### 12. Keep artifacts non-canonical unless explicitly promoted

Artifact contracts currently define proposed changesets, validation reports, and export manifests as `export or view`.

Rules:

- Proposed changeset artifact: durable preview of proposed canonical writes; not canonical by itself.
- Validation report artifact: deterministic self-check evidence; does not write canonical state by itself.
- Export manifest: provenance for generated or blocked export; not canonical state.
- File-backed artifacts should be used selectively for reviewable generated outputs, not as a parallel database.
- Real lab photos, real workbook exports, and generated reports from real data should not be committed by default.

### 13. Gate external OCR, LLM, and inference services

The MVP should work without an external LLM.

Before any external OCR, LLM, or inference service is used:

- minimize payloads;
- avoid sending unnecessary full records;
- prefer local photos/ROI crops when possible;
- treat uncertain payload safety as local-only until the user approves;
- keep external output parsed/intermediate and reviewable.

External tooling must not bypass review queue, canonical candidate preview, validation report, and transactional apply.

## Data Boundary Standard

Use these boundaries in audits, implementation plans, API payloads, tables, files, and response shapes.

| Artifact or object | Boundary | Implementation rule |
| --- | --- | --- |
| Uploaded cage-card photo | raw source | Preserve even if parsing fails. |
| Imported workbook file | raw source | Assignment/reference/import evidence; does not overwrite accepted photo-backed state. |
| Raw OCR text | parsed or intermediate result | Visible and preserved; not canonical by itself. |
| ROI crop and field extraction | parsed or intermediate result / cache | Link to source photo and ROI label where available. |
| Note-line parse | parsed or intermediate result | Preserve raw line, line order, strike status, parsed candidates, confidence, review flag. |
| Photo evidence item | parsed or intermediate result | Connect photo, parse, ROI, note line, review, and later canonical/event links. |
| Low-confidence or conflicting value | review item | Route to review with source evidence and reason. |
| User correction | review item plus action/correction log | Preserve before/after and evidence link. |
| Canonical write candidate | non-canonical draft candidate | Reviewable proposed write; must not be treated as accepted state. |
| Proposed changeset artifact | export or view | Durable preview of proposed writes and blockers. |
| Validation report artifact | export or view | Deterministic gate result for apply/export readiness. |
| Accepted mouse/card/genotype/event state | canonical structured state | Written only after review/policy approval and guarded apply. |
| Card snapshot | parsed observation / current-state support | Source-backed snapshot; durable history comes from events. |
| Mouse event and action log | canonical structured state / event history | Append-oriented history with evidence and before/after where applicable. |
| Excel preview/export | export or view | Generated from accepted state; not source of truth. |
| Export manifest/log | export or view | Links export to accepted state, validation report, query/filter, and source evidence. |
| OCR retry or derived preview file | cache or parsed result | Must not create duplicate canonical records. |

If a layer is ambiguous, default to non-canonical until `AGENTS.md`, `final_mouse_colony_prd.md`, or another adopted project document explicitly defines it as canonical.

## Conflicts And Ambiguities To Watch

### Canonical candidate wording

`canonical_candidate` can sound canonical, but it is only a proposed write. Treat it as a non-canonical draft until applied.

### Review burden versus safety gates

Review burden reduction documents support quick check and trace-only UX. They do not authorize high-risk writes without review, evidence, and deterministic validation.

### Supporting documents versus adopted anchors

Most planning and review documents are non-canonical. Use this precedence:

1. `AGENTS.md`
2. `final_mouse_colony_prd.md`
3. committed implementation and tests
4. supporting documents in `docs/DOCUMENTATION_MAP.md`

### Mojibake-corrupted Korean notes

Some Korean planning documents contain encoding damage in this checkout. Use them for broad direction only when their meaning is clear and cross-check against PRD, tests, and uncorrupted documents.

### Artifact files versus database truth

Artifacts improve reviewability and audit. They should not become a second database or a path around canonical apply.

### Assistant summaries

Assistant/API/MCP summaries should be views or cache unless explicitly promoted by an adopted project document. MouseDB remains the colony truth owner.

## Decisions Needed Before Further Implementation

- First OCR path: fixture/manual-first, local OCR, or external OCR with approval.
- Confidence thresholds for auto-fill, quick check, must review, and block.
- Raw photo storage location and retention policy for the first local implementation.
- Minimum durable ROI/bbox storage for v1, especially ear-label and gel-band evidence.
- First supported Excel export priority: separation workbook, animalsheet, or both as previews.
- Deterministic validation report blocker set and severity mapping.
- Initial seed/config scope for assigned strains, ear labels, genotype categories, date rules, breeding rules, labeling rules, and export templates.
- How assistant/API read models should expose evidence warnings without becoming canonical state.

## Audit Checklist

Before implementing or approving a cage-card photo pipeline change, check:

- Does it preserve the original photo as raw source?
- Does it keep raw extracted values separate from normalized or corrected values?
- Does it route low-confidence, conflicting, or biologically unlikely data to review?
- Does it preserve source trace to a photo, note item, workbook row, source record, or manual assertion?
- Does it preserve before/after values for corrections and inferred state changes?
- Does it treat card records as snapshots and durable history as events?
- Does it avoid using Excel as source of truth?
- Does it avoid hard-coded strain, genotype, protocol, and date rules?
- Does it prevent OCR, AI, artifact, or assistant output from bypassing review and canonical apply?
- Does it write current state and related event/action history transactionally?
- Does final export use accepted state and include provenance or a blocked-export record?

## Recommended Next Implementation Slice

The safest next implementation work should strengthen correctness and audit before UI polish:

1. Ensure every canonical candidate apply event links to the most specific available `photo_evidence_item`, note item, source photo, or source record.
2. Extend domain-specific apply flows so movement, death, separation/weaning, mating, litter, and genotype events preserve specific evidence refs.
3. Keep validation reports deterministic and attached to apply/export readiness.
4. Keep export manifests linked to validation report, state watermark, source refs, query/filter, and expected filename.
5. Add UI audit panels that show source photo, ROI or note-line evidence, raw value, parsed value, correction, and linked canonical event.
