# Mouse Colony Reference Adoption Notes

## Document Status

Layer classification: design guidance / non-canonical reference adoption note.

This document summarizes external and Notion-based references that can inform the mouse colony management system. It does not define canonical database tables, final response shapes, or final product behavior. Canonical behavior should continue to follow `final_mouse_colony_prd.md`, `design.md`, `AGENTS.md`, and any later adopted project documents.

## Review Scope

References reviewed:

- Notion: `RA portfolio`
- Notion: `Research Tagging Agent`
- Notion: `Research Tagging Agent project archive`
- Notion: `External reference master note (2026-04-08)`
- Notion: `AI Development Resources & Cases`
- Notion: `AI Farm Assistant`
- Local: `final_mouse_colony_prd.md`
- Local: `design.md`
- Local: `AGENTS.md`
- Local: `mousedb_cli_first_review_ko.md`
- Local: `ui_reference_comparison_plan_ko.md`

## Overall Adoption Direction

The useful references are mostly structural, not visual.

The mouse colony product should adopt the pattern:

1. Preserve raw evidence.
2. Parse into intermediate results.
3. Route uncertain or risky values to review.
4. Promote values into canonical state only after review or explicit auto-fill policy permits it.
5. Generate Excel outputs as exports or views.

This maps well to the existing PRD direction:

- handwritten cage card photos are raw source evidence;
- OCR and note parsing are intermediate results;
- low-confidence, conflicting, or biologically unlikely values become review items;
- mouse, mating, litter, genotype, and event records are canonical only after accepted by policy or review;
- Excel files remain import/export views, not the source of truth.

The CLI-first MouseDB direction should adopt the same pattern. MouseDB should remain an independent tool that can later be called by PaperPipe, a personal Research Assistant, an API, or an MCP server. PaperPipe should not be hard-coded into MouseDB; instead, future integration should call stable MouseDB services or CLI JSON outputs.

## Development References To Adopt

### 1. Evidence-First Pipeline

Source reference:

- Research Tagging Agent

Adopt:

- Separate raw source, parsed result, canonical state, review item, export/view, and cache layers.
- Keep source links on every important parsed or canonical value.
- Store confidence and evidence with parsed fields.

Mouse colony mapping:

| Reference concept | Mouse colony equivalent |
| --- | --- |
| source paper/PDF | cage card photo, Excel row, genotyping sheet |
| extracted metadata | OCR field, ROI extraction, note-line parse |
| confidence/evidence | parsed field confidence, source photo region, note-line evidence |
| accepted paper record | verified mouse/card/event/genotype record |
| generated note/export | separation workbook, animalsheet, dashboard view |

Implementation note:

- Do not let parsed OCR values directly overwrite canonical records unless auto-fill policy permits it.
- Preserve before and after values for corrections and inferred state changes.

### 2. QC Gate And Review Routing

Source reference:

- Research Tagging Agent
- Project archiving page for Research Tagging Agent

Adopt:

- Confidence-based gates.
- Explicit review states.
- Quarantine-like handling for unreliable or conflicting values.

Recommended mouse colony states:

| State | Meaning |
| --- | --- |
| Uploaded | Raw source photo or file has been stored. |
| Processing | OCR, ROI extraction, or import parsing is running. |
| Parsed | Intermediate fields or rows have been extracted. |
| Auto-filled | High-confidence values were applied according to policy. |
| Needs Review | Low-confidence, conflicting, missing, or biologically unlikely values need user action. |
| User Corrected | User changed raw-derived or normalized values. |
| Verified | User confirmed the reviewed value or action. |
| Export Ready | Required reviews blocking an export are resolved. |

Review item triggers:

- Low OCR confidence.
- Unknown strain or genotype category.
- Date conflict.
- Mouse active in two incompatible states.
- Count mismatch between note lines, sex/count fields, and Excel outputs.
- Mating or litter event with missing parent IDs.
- Genotype result outside configured categories.

### 3. Fail-Open Processing

Source reference:

- Research Tagging Agent
- AI Farm Assistant

Adopt:

- A single failed photo, OCR pass, row import, or export should not halt the whole pipeline.
- Failures should create review items, logs, or blocked export warnings.
- Partial writes must be guarded against.

Implementation checks:

- No orphan `parse_result` without a `photo_log` or import source.
- No canonical state change without source evidence.
- No stale export presented as current.
- No duplicate mouse/event records created by retrying the same import.

### 4. Environment Reproducibility

Source reference:

- AI Development Resources & Cases
- `VS Code Dev Container reproducibility`

Adopt:

- Pin OCR, image processing, and Excel export dependencies.
- Prefer reproducible local development setup.
- Keep sample fixtures for photos, Excel rows, OCR text, and expected parsed output.

Useful test fixture types:

- clear separated cage card photo;
- blurry or cropped cage card photo;
- mating cage card with litter note lines;
- struck-through note lines;
- Excel separation workbook sample;
- animalsheet sample;
- genotyping sheet sample;
- unknown strain and unknown genotype examples.

### 5. Module Separation

Source reference:

- `Skills/Hooks/Subagents separation`
- AI Development Resources & Cases

Adopt the role separation, not the exact agent terminology:

- Photo storage and source logging.
- Image quality check.
- OCR and ROI extraction.
- Field parsing and normalization.
- Strain/genotype/rule matching.
- Validation and review routing.
- Canonical event/state writer.
- Excel import/export.
- Audit and export logs.
- Stable CLI commands and JSON output contracts for future tool integration.

Guidance:

- Add abstractions only when they clarify the domain model or reduce meaningful duplication.
- Keep strain, genotype, protocol, and date rules configurable.
- Keep business logic in services that can be reused by CLI, web UI, API, and MCP wrappers.
- State-changing operations that update current mouse state and write events should be transactional.

## Design References To Adopt

### 0. UI Reference Redesign Direction

Source reference:

- Local `ui_reference_comparison_plan_ko.md`

Adopt:

- Use the reference screens for product shell, hierarchy, density, and navigation quality, not as literal screens to copy.
- Make Photo Review Workbench the first polished operational screen.
- Add a persistent sidebar and top utility bar before expanding dashboard-style summaries.
- Keep Evidence Comparison, Review Queue, and Export Readiness as secondary operational views.
- Defer Mouse Detail, Strain Detail, and full Colony Dashboard until reviewed canonical data is strong enough to support them.

Required adaptation:

- Every dashboard, detail, chart, and summary should disclose whether it is based on raw source, parsed/intermediate data, review items, canonical structured state, or export/view data.
- Raw photo review, manual transcription, evidence comparison, and candidate drafts must not create canonical state unless the user explicitly applies a reviewed candidate.
- Uncertain values must remain visible and actionable rather than disappearing into clean KPI totals.

### 1. Workflow-First Information Architecture

Source reference:

- Local `design.md`
- Research Tagging Agent
- AI Farm Assistant

Adopt:

1. Photo Inbox
2. Review Queue
3. Colony Records
4. Mating & Litters
5. Genotyping
6. Exports
7. Settings

Design principle:

- The dashboard should support work, not drive the product structure.
- Prioritize upload, review, correction, and Excel export flows over broad dashboard decoration.

### 2. Photo Inbox

Adopt:

- Dense source list on the left.
- Source photo preview and parsed field comparison on the right.
- Batch upload summary for common sessions where many cage card/name tag photos are uploaded together.
- Raw values and normalized suggestions shown side by side.
- Per-field confidence, not only per-photo confidence.
- Quality issues visible: blurry, cropped, glare, missing note area, low confidence.

Avoid:

- Presenting inferred values as final.
- Hiding uncertain OCR values in logs.
- Collapsing raw text and normalized value into one field.

### 3. Review Queue

Adopt:

- Review items grouped by risk and workflow impact.
- Source evidence always visible.
- Before/after preview before applying corrections.
- Clear action language such as `Apply Reviewed Changes`.

Avoid:

- Buttons or copy that pressure the user to accept inferred biological or colony-state data.
- Silent destructive overwrites.

### 4. Export Center

Source reference:

- AI Farm Assistant operational metrics
- Local PRD and design notes

Adopt:

- Export type cards for separation workbook, animalsheet, and handoff outputs.
- Last export timestamp.
- Blocked review item count.
- Stale export warning.
- Export preview.
- Failed export log.
- On-demand generation using the lab filename pattern, rather than a scheduled monthly automation.
- Multi-strain operation: choose a strain before preview/download, and later support batch generation of one workbook per strain when needed.
- Senior workbook examples should be treated as raw source/template references because animalsheet tabs can be strain-based while separation tabs can be person-based with many strain blocks.

Design principle:

- Excel exports must look like generated views, not the canonical database.
- Email sending should remain outside MVP; the product can support a manual handoff checklist without sending mail automatically.

### 5. Settings And Masters

Adopt:

- Strain Master.
- My Assigned Strains as the user's active matching scope.
- Strain Alias Master.
- Distribution Import as an occasional helper for assignment changes.
- Genotype Category Master.
- Management Rule Master.
- Card Type Rules.
- Export Templates.

UX guidance:

- Unknown parsed values should create review items.
- Adding a new strain/genotype/rule should feel deliberate, not automatic.
- Periodic distribution workbooks should help update My Assigned Strains when assignments change, not overwrite accepted cage/card state.

## External References Worth Evaluating

From `External reference master note (2026-04-08)`:

| Reference | Potential use | Adoption status |
| --- | --- | --- |
| PaddleOCR | Local OCR candidate for cage card photos | Evaluate |
| OpenDataLoader PDF | PDF or document parsing reference for genotyping sheets | Evaluate |
| semantic-router | Routing parsed outputs into review categories | Optional |
| Transformers.js | Local or browser-side inference experiments | Optional |
| OpenAI Codex AGENTS guide | Agent/project instruction structure | Informational |
| OpenAI Codex Skills guide | Repeatable workflow packaging | Informational |
| OpenAI MCP guide | Tool integration design | Informational |
| Harness Design for Long-Running Apps | Long-running workflow and harness thinking | Informational |
| Engineering Discipline | Development discipline and process reference | Informational |

Safety note:

- Before using any external OCR, LLM, or inference service, minimize payloads and avoid sending unnecessary full records.
- If payload safety is unclear, treat it as local-only until the user approves otherwise.
- The base workflow should remain LLM-optional: local/manual parsing, OCR, rules, validation, review, and export must still work without an LLM.

## References To Avoid Or Treat Carefully

### Portfolio Visual Style

Source:

- RA portfolio page

Do not adopt the decorative portfolio style directly. The mouse colony product should feel like a careful lab workflow tool, not a portfolio, landing page, or broad analytics dashboard.

### AI Farm Assistant Hardware Details

Source:

- AI Farm Assistant
- Prototype hardware pages

Do not adopt sensor, hardware, or farm-specific details. The useful part is MVP discipline, operational metrics, and field-workflow thinking.

### PaperPipe Slot/Top3 Logic

Source:

- Research Tagging Agent

Do not directly adopt paper triage slots, Top3 selection, or literature-specific scoring. Only the confidence, evidence, QC, and provenance concepts transfer cleanly.

### Hard-Coded Domain Rules

Do not hard-code:

- strain names;
- genotype categories;
- date rules;
- protocols;
- biologically specific thresholds.

These belong in configurable master data or adopted project documents.

## Open Decisions

- Which OCR engine should be used first for MVP: local OCR only, external OCR with approval, or hybrid?
- Should `Quarantined` be a visible user-facing state, or should it be represented as a high-priority `Needs Review` item?
- What confidence thresholds should separate auto-fill, review, and blocked states?
- Which Excel formats are required for the first export implementation?
- Should photo ROI overlays be implemented in MVP, or deferred until after basic review flow works?

## Recommended Next Implementation Slice

Build the first vertical slice around one cage card photo:

1. Store source photo in `photo_log`.
2. Store OCR/raw parsed fields in `parse_result`.
3. Create `card_snapshot` as a source-backed observation.
4. Parse note lines into `card_note_item_log`.
5. Route uncertain fields into `review_queue`.
6. Allow user correction with before/after values.
7. Generate a minimal export preview.

This slice exercises the key product philosophy without requiring full colony history, pedigree resolution, or broad dashboard features.
