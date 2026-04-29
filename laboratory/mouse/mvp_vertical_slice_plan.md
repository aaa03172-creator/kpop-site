# Mouse Colony MVP Vertical Slice Plan

## Document Status

Layer classification: implementation planning / non-canonical project note.

This document turns the current PRD, design notes, and reference adoption notes into an implementation sequence. It does not define canonical schema or final product behavior. Canonical product behavior should continue to follow `final_mouse_colony_prd.md`, with `design.md`, `reference_adoption_notes.md`, and `AGENTS.md` used as supporting guidance.

## Target Slice

Build one end-to-end workflow around a single cage card photo:

1. Store the source photo as raw evidence.
2. Create parsed OCR and field extraction results.
3. Display raw and normalized values side by side.
4. Route uncertain values into review.
5. Apply a reviewed correction with before/after traceability.
6. Show the resulting canonical candidate state.
7. Generate a minimal Excel export preview.

The slice should prove the core product loop before adding broad dashboard features.

## Data Boundary Map

| Artifact | Boundary | Notes |
| --- | --- | --- |
| Uploaded cage card image | raw source | Must be retained even if parsing fails. |
| OCR text | parsed or intermediate result | Never treated as clean canonical data by itself. |
| ROI field extraction | parsed or intermediate result | Store field confidence and source region when available. |
| Normalized DOB or strain match | parsed or intermediate result | Becomes canonical only through policy or review. |
| Low-confidence strain alias | review item | Do not create new strain automatically. |
| User correction | review item plus action log | Preserve before and after values. |
| Mouse/card/event candidate | canonical structured state candidate | Must remain traceable to source photo and note line. |
| Separation workbook preview | export or view | Generated from structured records, not source of truth. |
| OCR retry result | cache or parsed result | Must not create duplicate canonical records. |

## Recommended File/Module Shape

The current prototype is static HTML. If the project moves into application code, keep modules separated by boundary:

| Module | Responsibility |
| --- | --- |
| `source_store` | Save and retrieve raw photos and import files. |
| `parse_pipeline` | OCR, ROI extraction, raw field parsing, confidence. |
| `normalization` | Date normalization, strain alias matching, genotype matching. |
| `validation` | Required fields, count consistency, date logic, active conflict checks. |
| `review_queue` | Create review items and preserve issue context. |
| `action_log` | Record user corrections, before/after values, and inferred changes. |
| `canonical_writer` | Apply reviewed or policy-approved changes to structured state. |
| `exporter` | Produce Excel previews and exports. |

These names are planning labels, not required final file names.

## Implementation Sequence

### Step 1: Source Photo Intake

Goal:

- Accept a local photo file and register it as raw source evidence.

Minimum behavior:

- Generate a `photo_id`.
- Store original filename, upload time, capture time if available, and file path.
- Set status to `Uploaded`.
- Display the photo in Photo Inbox.

Acceptance checks:

- Poor-quality image is still stored.
- Upload failure does not create partial parsed or canonical records.
- Re-uploading the same source does not silently duplicate downstream state.

### Step 2: Stub OCR And Field Extraction

Goal:

- Convert the source photo into parsed fields.

Minimum behavior:

- For MVP, allow fixture-based OCR text before real OCR is integrated.
- Store raw OCR text.
- Extract candidate fields: strain, DOB, sex/count, ID, note lines.
- Attach per-field confidence.
- Set parsing status to `Parsed` or `Needs Review`.

Acceptance checks:

- Raw OCR text remains visible.
- Normalized values are displayed separately from raw values.
- Low-confidence fields create review items.

### Step 3: Note Line Parsing

Goal:

- Treat note lines as primary continuity evidence.

Minimum behavior:

- Parse note lines into typed candidates: mouse item, litter event, unknown.
- Preserve raw note text.
- Preserve strike-through status when available.
- Attach confidence and source photo link.

Acceptance checks:

- Struck-through lines are not deleted.
- Unknown note lines become review items.
- Mouse IDs from note lines are visible in review and records views.

### Step 4: Review Queue

Goal:

- Resolve uncertain, conflicting, or high-risk values before canonical updates.

Minimum behavior:

- Create review items for low-confidence strain, unknown genotype, count mismatch, duplicate active mouse, and date conflict.
- Show source photo and parsed field beside the review item.
- Capture before and after values when the user applies a correction.

Acceptance checks:

- No silent destructive overwrite.
- Dismissal requires a reason in production flow.
- Reviewed correction creates an action log entry.

### Step 5: Canonical Candidate Writer

Goal:

- Apply only reviewed or policy-approved values to structured state.

Minimum behavior:

- Create or update candidate mouse records from reviewed note lines.
- Create a card snapshot as a source-backed observation.
- Link canonical candidate records to source photo and note item.

Acceptance checks:

- Card snapshot is not treated as durable history by itself.
- Movement, death, mating, litter, and genotype updates are represented as events.
- Internal IDs stay hidden from ordinary user-facing UI.

### Step 6: Export Preview

Goal:

- Produce a familiar Excel-shaped preview from accepted structured state.

Minimum behavior:

- Show a separation workbook preview table.
- Show blocked export count.
- Show stale or failed export state.
- Record export attempt in export log.

Acceptance checks:

- Export preview is labeled as export/view.
- Blocking review items prevent final export.
- Export does not become the only source of truth.

## Initial Test Fixtures

Create small fixtures before integrating real OCR:

- clear separated cage card;
- blurry separated cage card;
- mating card with litter note;
- struck-through note line;
- unknown strain text;
- genotype outside configured category;
- duplicate active mouse ID;
- incomplete OCR result;
- sample separation workbook output row;
- sample animalsheet output row.

Current fixture file:

- `fixtures/sample_parse_results.json`: parsed/intermediate result fixture that can be imported through the prototype's `Import Parse JSON` button.

## UI Acceptance Checklist

- Photo Inbox is the first operational screen.
- Raw source, parsed result, review item, canonical state, and export/view are visually labeled.
- Raw and normalized values are shown side by side.
- Per-field confidence is visible.
- Source photo remains visible during review.
- Review actions show before and after values.
- Export Center shows blocked review item count.
- Settings shows configurable strain, genotype, date/rule, and export template masters.
- External OCR or LLM use is presented as approval-gated or local-only by default.

## Technical Guardrails

- Do not hard-code strain names, genotype categories, protocols, or date rules.
- Do not silently overwrite high-risk data.
- Do not send full records to external OCR, LLM, or inference services without approval.
- Do not delete raw source photos because parsing quality is poor.
- Do not treat Excel as the canonical database.
- Do not create canonical records from OCR-only values unless explicit auto-fill policy allows it.

## Open Decisions Before Real OCR

- Which OCR engine is first: local OCR, external OCR with approval, or fixture-only prototype?
- What confidence thresholds trigger auto-fill, review, and block states?
- What is the first supported Excel output: separation workbook or animalsheet?
- Should ROI overlays be implemented in MVP or after field extraction is stable?
- Where should raw photos be stored for the first local implementation?

## Suggested Next Build Task

Implement fixture-backed photo intake and review behavior before real OCR.

First build target:

1. Load a local fixture photo record.
2. Load fixture OCR/field parse JSON.
3. Render it in Photo Inbox.
4. Create review item for one low-confidence field.
5. Apply correction.
6. Append action log entry.
7. Update export preview blocked count.

This keeps the first implementation small while exercising the full evidence-to-review-to-export loop.
