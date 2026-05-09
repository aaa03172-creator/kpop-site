# PVM Photo Evidence Ledger Adoption Review For MouseDB

## Document Status

Layer classification: implementation planning / non-canonical project note.

Canonical: false. This document does not define final product schema, API contracts, database migrations, or committed runtime behavior. It translates the Persistent Visual Memory paper into a MouseDB workflow-level evidence design and identifies the minimum documentation, schema, code, and test work that should follow.

Reviewed external references:

- Hugging Face paper page: https://huggingface.co/papers/2605.00814
- arXiv abstract page: https://arxiv.org/abs/2605.00814
- Official GitHub repository: https://github.com/huaixuheqing/PVM

## Executive Summary

Decision: **partial adoption**.

MouseDB should not adopt PVM as a model architecture, training recipe, fine-tuning plan, or VLM internal memory module. The useful part is the problem framing: visual evidence can fade or become detached from later generated conclusions. In MouseDB, this is a data-integrity problem, not a deep-learning architecture problem.

The MouseDB adoption target is a workflow-level **Photo Evidence Ledger**:

1. Raw source photos remain immutable evidence.
2. OCR and AI extraction remain draft evidence.
3. Parsed note lines remain reviewable evidence anchors.
4. Human corrections preserve before and after values.
5. Canonical mouse, cage, genotype, mating, separation, death, and litter events must point back to source evidence.

The immediate recommendation is to document and then implement a narrow ledger around existing tables before adding any new AI capability.

## PVM Insight Translated To MouseDB

PVM addresses a visual grounding failure in autoregressive LVLMs. The paper describes visual signal dilution during long sequence generation, where the model's attention to original visual tokens decays as textual context grows. The GitHub repository confirms that the proposed solution is a parallel visual retrieval branch for Qwen3-VL-style models, plus training entry points.

MouseDB has a similar shape of failure but at a different layer:

| PVM concept | MouseDB translation |
| --- | --- |
| Visual signal dilution | Raw cage-card evidence gets buried behind OCR text, AI interpretation, review summaries, exports, and later edits. |
| Persistent visual memory | Durable source photo, ROI, field, and note-line evidence that remains available at commit and audit time. |
| Fixed visual token bank | Immutable raw photo plus derived local card crop, field crop, note-line anchor, and gel band crop references. |
| Distance-agnostic retrieval path | Canonical state and events can always link back to source photo or evidence item regardless of how many workflow steps happened later. |
| Visual retrieval branch | Product workflow branch: raw evidence, draft parse, review item, correction, canonical commit, and export trace stay separated. |

MouseDB should phrase this as:

> Do not let later AI summaries, normalized values, or Excel exports become detached from the photo or note line that justified them.

## What To Bring In

Bring in these concepts:

- Persistent evidence access: every important state change should preserve a route back to raw photo or note-line evidence.
- Draft-versus-commit separation: AI extracted values are draft observations until reviewed or explicitly accepted.
- Evidence locality: use local photos, local ROI crops, and minimized payloads. Treat external inference as opt-in and payload-minimized.
- Reviewable uncertainty: low confidence, biological conflicts, ambiguous handwriting, and OCR symbol confusion must create review items.
- Later re-check: review and canonical apply views should show the original source evidence, not only the extracted text.
- Audit-first corrections: corrected values must not overwrite raw OCR or observed text.

Bring in as design vocabulary only:

- "persistent visual memory" becomes "Photo Evidence Ledger".
- "visual signal dilution" becomes "evidence dilution".
- "visual retrieval" becomes "audit retrieval to source photo, ROI, note line, or gel band".

## What Not To Bring In

Do not bring in:

- PVM model training or fine-tuning.
- Qwen3-VL custom model files.
- SFT or GRPO training flows.
- VLM internal attention modification.
- Trainable memory adapters.
- Sending real lab photos to external tools as a default architecture.
- Treating PDF visual grounding benchmarks as equivalent to MouseDB evidence traceability.
- Any path that lets raw OCR, raw image-derived text, or AI interpretation overwrite human-approved canonical values.

## Current Repo State

Current implementation already has several pieces of the ledger:

| Concern | Current artifact | Review |
| --- | --- | --- |
| Raw source photo | `app/db.py` `photo_log` | Present. Uploaded photo is retained and linked to review flow. |
| Parse attempt and AI/manual draft | `parse_result` | Present. It acts like a parse log, but not a full append-only photo parse ledger. |
| Review queue | `review_queue`, `review_evidence_link` | Present. Review items can reach the source photo through `parse_id`, and photo transcription reviews can directly link to field/note evidence items. |
| Card snapshot | `card_snapshot` | Present as parsed/intermediate observation, not durable history by itself. |
| Note-line evidence | `card_note_item_log` | Present. This is a strong fit for cage card note line continuity. |
| Correction history | `correction_log` | Present, but should be extended or consistently used for evidence item corrections. |
| Canonical mouse state | `mouse_master` | Present. Several fields carry `source_photo_id`, `source_note_item_id`, and `source_record_id`. |
| Event history | `mouse_event` | Present. Some event paths include `source_record_id`; photo/note evidence requirements are not consistently enforced. |
| Genotyping evidence | `genotyping_record` | Present, with `source_photo_id`, `source_record_id`, and `photo_evidence_id`. Genotype result confirmation is evidence-gated. |
| ROI/crop evidence | ROI preview and cache paths | Present as local derived review aid, but not yet durable field-level evidence. |

Important current findings:

- `photo_parse_log` does not exist by that exact name. `parse_result` covers part of the need, but a future ledger should record parse attempt metadata more explicitly: extraction method, ROI template, field crop labels, source image minimization mode, OCR engine/model, parse version, confidence, and failure/supersession state.
- `card_note_item_log` exists and is the correct starting point for cage card note line tracking.
- Review Queue is connected to raw photo evidence through `review_queue.parse_id -> parse_result.photo_id -> photo_log.photo_id`; photo transcription reviews also use `review_evidence_link` to point directly at `photo_evidence_item` rows.
- ROI/bbox is currently enough as a local review aid. For v1, `source_photo_id + roi_label + observed_raw_text + note_item_id` is sufficient. Durable `bbox_json` should be added first for ear label ambiguity and gel band evidence, not for every field on day one.
- AI parsing results generally enter `parse_result`, `card_snapshot`, `card_note_item_log`, `photo_evidence_item`, and `review_queue` before canonical apply.
- The risky gap is no longer initial AI transcription or genotype result confirmation. Remaining risk is later manual or workflow endpoints that create mating, death, movement, separation, or litter events with weak evidence requirements.

## Proposed Photo Evidence Ledger

The minimum schema should be a small field-level evidence table, not a new AI subsystem.

Proposed table name:

```text
photo_evidence_item
```

Minimum fields:

| Field | Required | Boundary | Purpose |
| --- | --- | --- | --- |
| `photo_evidence_id` | yes | parsed or intermediate result | Stable evidence item ID for review and canonical links. |
| `source_photo_id` | yes | raw source link | Links to immutable uploaded photo. |
| `parse_id` | optional | parsed result link | Links to OCR/AI/manual parse attempt. |
| `card_snapshot_id` | optional | parsed observation link | Links to the card snapshot observed from the photo. |
| `note_item_id` | optional | note evidence link | Links to a note line when the evidence came from NOTE. |
| `card_type` | optional | parsed result | Candidate card type visible or inferred from the photo. |
| `evidence_kind` | yes | parsed result | Examples: `card_field`, `note_line`, `ear_label`, `gel_band`, `protocol_text`, `genotyping_sheet_cell`. |
| `roi_label` | optional | parsed result | Local crop label such as `raw_strain`, `notes`, `ear_label`, `gel_lane_3`. |
| `bbox_json` | optional | parsed result/cache pointer | Coordinates in source or normalized card image. Nullable in v1. |
| `observed_raw_text` | optional | photo observation | What a human or extractor says is directly visible. |
| `ocr_text` | optional | OCR draft | OCR output, preserved even after correction. |
| `parsed_value` | optional | AI/parser draft | Structured candidate value. |
| `confidence` | yes | parsed result | Numeric confidence for the extraction or interpretation. |
| `interpretation` | optional | AI/parser draft | Human-readable interpretation, such as `R0 may be R_CIRCLE`. |
| `needs_review` | yes | review routing | Whether it must be checked before canonical use. |
| `review_reason` | optional | review routing | Why review is needed. |
| `linked_mouse_id` | optional | canonical link | Filled when accepted into mouse state. |
| `linked_cage_id` | optional | canonical link | Filled when accepted into cage/movement state. |
| `linked_event_id` | optional | canonical link | Filled when accepted into event history. |
| `status` | yes | workflow state | `draft`, `review_open`, `accepted`, `rejected`, `superseded`, `linked`. |
| `created_at` | yes | audit | Creation time. |
| `updated_at` | yes | audit | Last workflow update time. |

This table should not replace `photo_log`, `parse_result`, `card_note_item_log`, or `correction_log`. It should connect them.

## Source, Draft, Review, Canonical Separation

MouseDB should maintain four different meanings:

| Layer | Meaning | Existing examples | Rule |
| --- | --- | --- | --- |
| Photo observation | What is visible in the raw photo or crop. | `photo_log`, ROI crop, `observed_raw_text`, note line image. | Never overwrite. |
| OCR extraction | Text extracted from the image. | `parse_result.raw_payload`, future `ocr_text`. | Preserve as draft, even if wrong. |
| AI/parser interpretation | Meaning assigned to visible or OCR text. | `parsed_value`, `parsed_ear_label_code`, card type candidate. | Reviewable; not canonical by itself. |
| Human-approved canonical value | Value accepted into operational mouse state. | `mouse_master`, `mouse_event`, `genotyping_record` accepted result. | Must link to source evidence for high-risk events. |

Correction flow:

1. User reviews a field, note line, gel band, or event candidate.
2. The raw observed text and OCR text remain unchanged.
3. The selected/corrected value is recorded as a correction or accepted evidence value.
4. The canonical record or event stores a link back to the evidence item, source note line, source photo, or source record.

## Review Queue Connection

Review items should be able to show:

- source photo image;
- optional normalized card crop;
- optional field crop or ROI label;
- note line raw text;
- OCR text;
- AI parsed value;
- current canonical value if any;
- proposed corrected value;
- confidence;
- review reason;
- downstream event or mouse record that would be affected.

For v1, a review item may link indirectly through `parse_id` and `note_item_id`. Photo transcription reviews now also link through `review_evidence_link`; future high-risk review items should use the same linking pattern instead of adding a single `photo_evidence_id` column to `review_queue`.

## Event Commit Rule

The following canonical writes must not commit from AI/OCR draft alone:

| Event or state change | Minimum evidence before commit |
| --- | --- |
| New mouse from cage card note line | Reviewed `card_note_item_log.note_item_id` or accepted `photo_evidence_item`. |
| Genotype result accepted | Genotyping sheet row, gel image band evidence, imported result source record, or explicit manual review source. |
| Death or sacrificed status | Source note line, photo evidence, or explicit manual source record with correction/action log. |
| Separation or weaning | Source card/photo note, reviewed litter record, or manual source record. |
| Cage movement | Source note/card evidence or explicit manual source record. |
| Mating start/end | Mating cage card, parent note lines, or explicit manual source record. |
| Litter birth/pup count | Mating card note line, litter note evidence, or explicit manual source record. |
| Identity-changing correction | Correction log with before/after values and review/source link. |

Implementation rule:

- If the event is high-risk and has no `photo_evidence_id`, `source_note_item_id`, `source_photo_id`, or `source_record_id`, the write should fail or route to Review Queue.
- `manual_entry` source records are acceptable only when the UI makes clear that the user is asserting the evidence manually.
- AI parsed values can create candidates and review items, not direct canonical updates.

## Genotyping Gel Image Evidence

MouseDB should support gel image evidence, but not as a v1 model-training problem.

Minimum useful shape:

| Field | Purpose |
| --- | --- |
| `source_photo_id` | Raw gel image or genotyping sheet photo. |
| `evidence_kind` | `gel_band` or `genotyping_sheet_cell`. |
| `roi_label` | Lane or band crop label, such as `lane_03_target_band`. |
| `bbox_json` | Band/lane crop coordinate when available. |
| `observed_raw_text` | Visible sample label or lane annotation. |
| `parsed_value` | Candidate band call, such as `band_present`, `band_absent`, `ambiguous`. |
| `confidence` | Band call confidence. |
| `linked_mouse_id` | Mouse matched from sample ID. |
| `linked_event_id` | Genotyped event after approval. |

Gel band calls should start as reviewable evidence. A genotype result should become canonical only after user confirmation or an explicit imported result source.

## Minimal Patch Candidates

### Doc-only

1. Adopt this document as the PVM-to-MouseDB interpretation.
2. Add it to `final_mouse_colony_prd.md` document references.
3. Add a short note to `mvp_vertical_slice_plan.md` that the vertical slice should eventually create field-level photo evidence items before canonical apply.

### Schema-only

1. Add `photo_evidence_item`.
2. Add `review_evidence_link` so one review can cover several evidence items.
3. Add optional `photo_evidence_id` to `mouse_event` or standardize event details JSON to include `photo_evidence_ids`.
4. Allow `correction_log.entity_type = 'photo_evidence_item'` and `entity_type = 'note_item'`.

### Code-required

1. On AI/manual photo transcription, create evidence rows for card fields and note lines.
2. On review resolution, write correction rows that preserve raw OCR/observed text separately from corrected values.
3. On canonical candidate apply, link created mouse events to source evidence item IDs when available.
4. Require evidence for `update_genotyping` when accepting a genotype result, unless the user supplies an explicit manual source record.
5. Require evidence/source records for death, separation, mating, movement, and litter event commits.
6. Add UI audit display for source photo, ROI label, raw text, parsed value, correction, and linked canonical event.

## Implementation Plan

### Phase 1: Document and boundary alignment

Goal: make the PVM adoption decision explicit without changing runtime behavior.

Steps:

1. Add this adoption document.
2. Link it from the PRD document reference list.
3. Cross-check that it does not claim canonical schema status.
4. Keep PVM implementation, training, and fine-tuning out of MouseDB scope.

Verification:

- Markdown can be read without encoding damage.
- `git diff --check` passes.
- No runtime files are changed.

### Phase 2: Evidence ledger schema draft

Goal: add a small schema placeholder while preserving existing tables.

Suggested implementation:

1. Add `photo_evidence_item` to `app/db.py`.
2. Add indexes for `source_photo_id`, `parse_id`, `note_item_id`, `linked_mouse_id`, and `linked_event_id`.
3. Do not remove or rename `parse_result` or `card_note_item_log`.
4. Treat all new rows as `parsed or intermediate result` unless linked after review.

Acceptance checks:

- Existing tests still pass.
- Existing photo transcription still works.
- Existing canonical candidate apply still works.
- No canonical write requires the new table until code paths are updated.

### Phase 3: Photo transcription evidence rows

Goal: create durable field-level evidence during AI/manual transcription.

Suggested implementation:

1. For card-level fields, create evidence rows with `evidence_kind = 'card_field'`.
2. For NOTE lines, create evidence rows linked to `card_note_item_log.note_item_id`.
3. Store `roi_label` when available from ROI extraction regions.
4. Store `observed_raw_text`, `ocr_text`, and `parsed_value` separately where the payload provides them.
5. Mark uncertain fields and note-line ambiguity as `needs_review = 1`.

Acceptance checks:

- Raw photo remains in `photo_log`.
- Raw note lines remain in `card_note_item_log`.
- Evidence rows do not overwrite `parse_result.raw_payload`.
- Low-confidence fields create or link to review items.

### Phase 4: Review and correction linkage

Goal: make review resolution preserve raw, parsed, corrected, and canonical layers.

Suggested implementation:

1. Link review items to one or more evidence items.
2. When resolving a review with a correction, write `correction_log` with before and after values.
3. If the correction targets a note line or evidence item, do not overwrite `observed_raw_text` or `ocr_text`.
4. Store the selected value as corrected/accepted interpretation.
5. Keep the source photo and note line visible in audit view.

Acceptance checks:

- Ear label correction preserves raw `R0`, `RWM`, or prime/circle text.
- Correction history shows before and after values.
- Review audit can show the source photo path or image URL.

### Phase 5: Evidence-required canonical events

Goal: prevent high-risk event commits without source evidence.

Suggested implementation:

1. Add a small helper such as `require_event_evidence(event_type, payload)`.
2. Apply it first to genotype result acceptance.
3. Extend it to death, separation/weaning, cage movement, mating, and litter events.
4. Permit explicit manual source records when the user is entering evidence directly.
5. Return actionable error messages that tell the user which evidence is missing.

Acceptance checks:

- Genotype confirmation without evidence is blocked or routed to review.
- Genotype confirmation with source record or gel/photo evidence succeeds.
- Mating, death, separation, and movement commits preserve source linkage.
- Existing reviewed canonical candidate apply remains possible because note-line/photo evidence is present.

### Implemented Progress Snapshot

Implemented in the local FastAPI/SQLite prototype:

- `photo_evidence_item` schema and indexes.
- `review_evidence_link` schema and indexes.
- AI/manual photo transcription writes field-level and note-line `photo_evidence_item` rows.
- Photo transcription review items link to evidence rows.
- Review audit exposes linked `photo_evidence_items`.
- Genotype result confirmation requires `source_photo_id`, `photo_evidence_id`, or `source_record_id`.
- Accepted genotype result records preserve evidence refs and create a `genotyped` mouse event with evidence details.

Still pending:

- Link canonical candidate apply events back to `photo_evidence_item`.
- Extend evidence-required commit checks to death, separation/weaning, cage movement, mating, and litter events.
- Add UI panels that render linked evidence rows with source photo/ROI context.
- Add gel band evidence capture as manual/reviewable rows before any automated band calling.

### Phase 6: Gel and genotyping evidence

Goal: represent gel image and genotyping sheet evidence without overbuilding image analysis.

Suggested implementation:

1. Add `evidence_kind = 'gel_band'` and `evidence_kind = 'genotyping_sheet_cell'`.
2. Allow lane/sample crop references through `roi_label` and `bbox_json`.
3. Start with manual band call and review status.
4. Later add local or explicitly approved AI-assisted band draft, still as reviewable evidence.

Acceptance checks:

- Gel image evidence can be linked to `genotyping_record`.
- Ambiguous band calls remain reviewable.
- Accepted genotype event links to evidence.

## Test Plan

### Cage card photo parsing regression

Purpose: ensure AI/manual photo transcription creates draft evidence, not canonical state.

Expected:

- `photo_log` row exists.
- `parse_result` row exists.
- `card_snapshot` row exists.
- `card_note_item_log` rows exist for note lines.
- future `photo_evidence_item` rows exist for fields and note lines.
- no high-risk canonical event is created without review/apply.

### Ear label ROI ambiguity test

Purpose: ensure ambiguous ear labels stay reviewable.

Inputs:

- `R0`, `RWM`, `R1`, unclear prime/circle marks.

Expected:

- raw note text remains unchanged.
- parsed candidate may exist.
- normalized ear label is withheld or marked reviewable.
- correction writes before/after values and leaves raw evidence intact.

### Genotyping evidence test

Purpose: ensure genotype confirmation requires evidence.

Expected:

- genotype result without evidence is rejected or routed to review.
- genotype result with source record is accepted.
- gel band evidence can link to `genotyping_record` and `mouse_event`.

### Correction history preservation test

Purpose: ensure user correction does not overwrite OCR or observed evidence.

Expected:

- raw OCR/observed text remains unchanged.
- correction log has before/after values.
- canonical value updates only after review or explicit accepted source.
- audit trail shows source photo, evidence item, correction, and canonical record.

### Event evidence enforcement test

Purpose: ensure high-risk events cannot be committed evidence-free.

Expected:

- death, separation, mating, movement, litter, and genotype events reject missing evidence unless an explicit manual source record is supplied.
- returned errors name the missing evidence field.
- successful writes include `source_record_id`, `source_photo_id`, `source_note_item_id`, or `photo_evidence_id`.

## Recommendation

Do now:

1. Adopt PVM only as the Photo Evidence Ledger framing.
2. Add a doc reference so future work does not reinterpret PVM as model training.
3. Plan schema placeholder work for `photo_evidence_item`.
4. Prioritize genotype evidence enforcement because genotype status currently has the highest risk of becoming canonical without photo or result evidence.

Do later:

1. Add durable bbox storage for ear labels and gel bands.
2. Add review UI evidence panels that show source photo, ROI, raw text, parsed value, and correction history.
3. Add gel image evidence as manual/reviewable band calls before any AI band calling.
4. Extend audit traces so every canonical event can show its evidence chain.

Do not do:

1. Do not implement PVM model internals.
2. Do not fine-tune a VLM for MouseDB v1.
3. Do not send real lab photos to external services by default.
4. Do not let AI parsing write genotype, death, separation, mating, or litter events directly.
5. Do not overwrite raw OCR or observed text with corrected values.
