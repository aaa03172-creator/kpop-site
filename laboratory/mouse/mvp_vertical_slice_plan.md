# Mouse Colony MVP Vertical Slice Plan

## Document Status

Layer classification: implementation planning / non-canonical project note.

This document turns the current PRD, design notes, Korean extension design, reference adoption notes, and CLI-first MouseDB review into an implementation sequence. It does not define canonical schema or final product behavior. Canonical product behavior should continue to follow `final_mouse_colony_prd.md`, with `design.md`, `mouse_strain_colony_system_design_ko.md`, `reference_adoption_notes.md`, `mousedb_cli_first_review_ko.md`, and `AGENTS.md` used as supporting guidance.

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
| My Assigned Strains | canonical structured state | User-approved scope for OCR strain matching and export grouping. |
| Imported distribution workbook | raw source | Occasional assignment reference; must not overwrite photo-backed colony state. |
| Parsed distribution row | parsed or intermediate result | Can help update My Assigned Strains after user review. |
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
| `assignment_scope` | Store and edit My Assigned Strains for OCR matching scope. |
| `assignment_importer` | Optional helper to parse distribution workbooks into assigned people, mating types, and expected cage counts. |
| `parse_pipeline` | OCR, ROI extraction, raw field parsing, confidence. |
| `normalization` | Date normalization, strain alias matching, genotype matching. |
| `validation` | Required fields, count consistency, date logic, active conflict checks. |
| `review_queue` | Create review items and preserve issue context. |
| `action_log` | Record user corrections, before/after values, and inferred changes. |
| `canonical_writer` | Apply reviewed or policy-approved changes to structured state. |
| `exporter` | Produce Excel previews and exports. |

These names are planning labels, not required final file names.

If the implementation moves toward a standalone MouseDB package, keep the core service layer independent from any UI:

```text
CLI or UI -> schemas/input validation -> services -> repositories -> models/db
```

The CLI should remain stable enough for a future Research Assistant, API, or MCP wrapper to call. Major commands should support `--json`, and JSON shapes used by tests should be treated as integration contracts.

## Implementation Sequence

### Step 1: Source Photo Intake

Goal:

- Accept a local photo file and register it as raw source evidence.

Minimum behavior:

- Accept multiple photos in one upload action and assign a batch identifier.
- Generate a `photo_id`.
- Store original filename, upload time, capture time if available, and file path.
- Set status to `Uploaded`.
- Display the photo in Photo Inbox.
- Show batch progress so processing/review failures remain local to each source photo.

Acceptance checks:

- Poor-quality image is still stored.
- Upload failure does not create partial parsed or canonical records.
- Re-uploading the same source does not silently duplicate downstream state.
- One failed or review-blocked photo does not block unrelated photos from the same batch.

### Step 1A: My Assigned Strains

Goal:

- Keep an explicit list of the user's assigned strains for OCR matching and review routing.

Minimum behavior:

- Let the user add, edit, deactivate, and review `My Assigned Strains`.
- Use `My Assigned Strains` as the first matching scope for cage card OCR.
- If a parsed cage card strain is outside this scope, route it to review instead of auto-accepting it.
- Optionally accept a `.xlsx` distribution workbook such as `20260407 의대 수의대 분배현황표.xlsx` when the user's assignment list changes.
- Convert the workbook with `npm run parse:distribution -- "path/to/분배현황표.xlsx" --out fixtures/parsed_distribution.json`, then import the JSON through `Import Distribution JSON` as a helper.
- Preserve distribution filename, sheet name, row number, and parsed row values when used.

Acceptance checks:

- My Assigned Strains can be updated without changing current cage/card state.
- Distribution imports remain optional and non-canonical until the user chooses assigned strains from them.
- Merged responsible-person cells are carried down as row evidence without losing the original row trace when distribution import is used.
- A newer distribution workbook can help update assigned scope while preserving import history.

### Step 2: Stub OCR And Field Extraction

Goal:

- Convert the source photo into parsed fields.

Minimum behavior:

- For MVP, allow fixture-based OCR text before real OCR is integrated.
- Keep LLM parsing optional; the vertical slice should run without any LLM service.
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
- Preserve raw ear label notation exactly when present.
- Normalize ear labels into codes such as `R_PRIME`, `L_PRIME`, `R_CIRCLE`, `L_CIRCLE`, and `NONE`.
- Keep prime/circle ambiguity reviewable instead of silently merging identity marks.
- Preserve strike-through status when available.
- Attach confidence and source photo link.

Acceptance checks:

- Struck-through lines are not deleted.
- Raw ear label text and normalized ear label code are visible separately for parsed mouse lines.
- Unknown note lines become review items.
- Mouse IDs from note lines are visible in review and records views.

### Step 4: Review Queue

Goal:

- Resolve uncertain, conflicting, or high-risk values before canonical updates.

Minimum behavior:

- Create review items for low-confidence strain, unknown genotype, count mismatch, duplicate active mouse, and date conflict.
- Show source photo and parsed field beside the review item.
- Capture before and after values when the user applies a correction.
- Resolve duplicate active mouse conflicts through a dedicated movement decision, not the generic correction action.

Acceptance checks:

- No silent destructive overwrite.
- Dismissal requires a reason in production flow.
- Reviewed correction creates an action log entry.
- Duplicate active mouse resolution records the selected movement outcome, evidence reason, and before value before unblocking export.

### Step 5: Canonical Candidate Writer

Goal:

- Apply only reviewed or policy-approved values to structured state.

Minimum behavior:

- Create or update candidate mouse records from reviewed note lines.
- Create a card snapshot as a source-backed observation.
- Link canonical candidate records to source photo and note item.
- For newly separated mice, initialize genotyping workflow fields as not sampled with next action sample needed when genotyping is required.
- Store line-level note evidence in `card_note_item_log` before writing mouse-level state.
- Store current individual state in `mouse_master`, while preserving movement/death/genotype changes as action/event history.
- Apply state changes and related event/action log writes in a single transaction.

Acceptance checks:

- Card snapshot is not treated as durable history by itself.
- Note line raw text, strike status, parsed mouse ID, parsed ear label, confidence, and review flag are preserved.
- Mouse display ID is not globally unique by itself; duplicate display IDs remain candidate matches until strain/DOB/ear-label/source context resolves them.
- Movement, death, mating, litter, and genotype updates are represented as events.
- Internal IDs stay hidden from ordinary user-facing UI.
- Partial writes cannot leave current mouse state updated without the corresponding event/action log, or vice versa.
- Event/action log entries preserve source evidence and before/after values when correcting or inferring high-risk state changes.

### Step 5A: Genotyping Worklist Planning

Goal:

- Keep mouse ID, ear label, sample ID, and genotype result connected after separation.

Minimum behavior:

- Show separated mice that need tail sampling.
- Support manual sample/result entry before real OCR.
- Match sample IDs to mouse IDs by exact ID, ID without prefix, and strain/DOB/ear-label context.
- Route unmatched, duplicate, conflicting, or ambiguous sample/result rows to review.
- Suggest target match, use category, and next action from configurable strain target genotype settings.

Acceptance checks:

- Newly separated mice can be found in a not-sampled worklist.
- Sample/result changes create action log entries.
- Suggested use category does not automatically overwrite user judgment.
- Existing export templates are not broken by genotyping fields.

### Step 6: Export Preview

Goal:

- Produce familiar workbook-shaped previews from accepted structured state using the current lab templates as references.

Minimum behavior:

- Show a `분리 현황표` preview with `Strain`, `Genotype`, `total`, `DOB`, `WT`, `Tg`, spacer, and `Sampling point` columns.
- Show an `animal sheet` preview with mating cage blocks: parent rows, litter rows, mating date, and pup note evidence.
- Let the user select the export strain when multiple accepted strains exist; filenames and rows are generated from that selected strain.
- Refresh export preview/readiness after accepted uploads and reviewed corrections.
- Show blocked export count.
- Show stale or failed export state.
- Record export attempt in export log.
- Generate final Excel-style outputs only when the user explicitly requests an export.
- Download `.xlsx` files from the current workbook preview using the lab filename pattern.
- Show expected filenames before download so the user can verify date, strain, and workbook type.
- Treat senior-provided multi-strain Excel files as source/template references: animalsheet examples may be strain tabs, while separation examples may be person tabs containing multiple strain blocks.

Acceptance checks:

- Export preview is labeled as export/view.
- Blocking review items prevent final export.
- Export does not become the only source of truth.
- Export behavior is upload-driven and on-demand, not tied to a monthly schedule or automated email handoff.
- Preview rows preserve traceability in the web UI even when traceability columns are not part of the lab workbook template.

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
- The prototype also includes a `Load Sample Fixture` button that loads the same embedded parsed/intermediate cases without using the file picker.
- The fixture includes a count mismatch case where the sex/count field indicates more animals than active mouse note lines. The prototype should route this to review and must not create canonical candidate rows from that fixture until reviewed.

Current verification command:

- `npm test` runs the Playwright-backed MVP smoke test in `scripts/verify-mvp.js`.
- The smoke test clears local prototype session state, imports the parsed fixture, verifies review routing, blocks duplicate active mouse approval until movement review, applies one reviewed correction, verifies dismissed items do not become canonical candidates, uploads a local source photo, checks reload persistence, and generates a separation CSV preview with blocked rows preserved in the export log.
- The duplicate active mouse fixture also verifies that resolving movement removes the conflict from the review queue and marks the previous active source as closed by movement review.
- The animalsheet fixture verifies parent ID row splitting, litter row rendering, pup count mapping, source evidence, and traceability columns.

## UI Acceptance Checklist

- Photo Inbox is the first operational screen.
- Raw source, parsed result, review item, canonical state, and export/view are visually labeled.
- Raw and normalized values are shown side by side.
- Per-field confidence is visible.
- Source photo remains visible during review.
- Review actions show before and after values.
- Export Center shows blocked review item count.
- Settings shows My Assigned Strains plus configurable strain, genotype, date/rule, and export template masters.
- External OCR or LLM use is presented as approval-gated or local-only by default.

## Technical Guardrails

- Do not hard-code strain names, genotype categories, protocols, or date rules.
- Do not silently overwrite high-risk data.
- Do not send full records to external OCR, LLM, or inference services without approval.
- Do not delete raw source photos because parsing quality is poor.
- Do not treat Excel as the canonical database.
- Do not create canonical records from OCR-only values unless explicit auto-fill policy allows it.
- Treat any future LLM output as parsed/intermediate data, not canonical truth.
- Keep Mouse genotype summaries as display/cache values; structured genotype records are the source of truth.
- Treat CLI JSON output, where implemented, as a stable integration contract for future tools.
- Write current-state changes and related event/action log entries transactionally.

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
