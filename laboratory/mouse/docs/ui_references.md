# UI References

Layer classification: design guidance / non-canonical product documentation.

This document records developer-only UI reference research rules for MouseDB. UI references can inform interaction design, but they do not define canonical database tables, response shapes, parsing behavior, genotype interpretation, or product requirements. Adopted behavior continues to come from `final_mouse_colony_prd.md`, `AGENTS.md`, committed tests, and explicitly accepted project documents.

## Lazyweb Usage Policy

Lazyweb may be used as a developer-only UI reference tool for design research. It must not be installed as a MouseDB runtime dependency, and MouseDB must not call Lazyweb from the CLI, FastAPI app, parsing pipeline, OCR workflow, validation reports, exports, or tests.

Allowed uses:

- finding UI references for review queues, OCR correction, source-evidence inspectors, spreadsheet-like export previews, and lab-style decision workflows;
- generating local-only design research notes from synthetic examples;
- summarizing reference patterns, anti-patterns, and MouseDB-specific recommendations in this document or a dated docs note.

Disallowed uses:

- sending real cage-card photos, mouse IDs, strain assignments, genotype results, workbook rows, lab names, or colony records to Lazyweb;
- using Lazyweb to improve parsing accuracy, genotype decisions, colony rules, or validation logic;
- treating Lazyweb output as a product requirement without human review and PRD alignment;
- committing Lazyweb tokens, generated MCP config, downloaded reference screenshots, or prompt logs that contain sensitive data.

## Config And Token Safety

Lazyweb tokens and MCP configuration belong only in ignored local developer config, such as a user-level Codex/Cursor/Claude config or `~/.lazyweb/`. They must not be committed to the repository.

The repository `.gitignore` blocks local MCP files and Lazyweb scratch output:

- `.mcp.json`
- `.mcp/`
- `.cursor/mcp.json`
- `.cursor/**/mcp*.json`
- `.lazyweb/`
- `lazyweb-output/`
- `ui-reference-screenshots/`
- `docs/ui_references/screenshots/`

If a future workflow repeatedly creates another local Lazyweb artifact, add a narrow ignore rule before committing any related documentation.

## Output Artifact Standard

When Lazyweb is used, keep the durable artifact as Markdown, not raw screenshots or tool config. Each research note should include:

- research date;
- UI topic;
- fake-data prompt used;
- source disclaimer: synthetic examples only, no real lab data;
- patterns worth considering;
- anti-patterns to avoid;
- MouseDB-specific recommendation;
- explicit note that the result is non-canonical design guidance.

Recommended location:

- short, durable summaries in this file;
- larger focused reports as `docs/ui_references/YYYY-MM-DD-<topic>.md`.

## Candidate UI Research Tasks

### Review Queue

Research goals:

- queue density;
- issue severity hierarchy;
- side evidence inspector;
- accept, correct, reject, and dismiss-with-reason actions;
- before/after confirmation and audit trail.

MouseDB fit:

- useful for reducing review fatigue and making uncertainty visible;
- should preserve raw source evidence and never pressure users to accept inferred biological state.

### Photo And OCR Correction

Research goals:

- source photo viewer with ROI or highlighted evidence;
- raw parsed value beside normalized suggestion;
- confidence and uncertainty display;
- keyboard-friendly correction flow.

MouseDB fit:

- useful for manual transcription and AI draft review;
- must use placeholder cage-card images only during research.

### Mouse Detail

Research goals:

- mouse master fields;
- genotype summary;
- accepted event timeline;
- source evidence links;
- cage movement history.

MouseDB fit:

- useful for information architecture and detail-drawer behavior;
- should keep internal IDs hidden unless debugging.

### Cage Detail

Research goals:

- current mice;
- card snapshot photo;
- parsed note lines;
- mating, litter, and weaning status;
- source card history.

MouseDB fit:

- useful for card-snapshot and event-history presentation;
- should not imply a handwritten cage-card ID is a stable physical cage ID.

### Genotyping Review

Research goals:

- sample number;
- protocol or gel image placeholder;
- raw band/result text;
- target gene;
- final reviewed genotype decision.

MouseDB fit:

- useful for review layout and decision auditability;
- must not infer genotype from reference UI patterns.

### Export Preview

Research goals:

- spreadsheet-like preview;
- blocked rows;
- stale export warnings;
- jump-to-review links;
- final download readiness.

MouseDB fit:

- useful for Excel compatibility and preventing unsafe exports;
- preview grids remain export/view layers, not canonical editing surfaces.

## Example Lazyweb Prompts With Synthetic Data

### Review Queue Prompt

```text
Use Lazyweb to find UI references for a data-correction review queue.

Use only synthetic MouseDB data:
- fake source photo: synthetic cage card placeholder, no real image
- fake mouse IDs: MOUSE-001, MOUSE-002
- fake strain: Synthetic-Strain-A
- fake issues: low OCR confidence, duplicate active mouse, DOB conflict
- fake actions: accept, correct, reject with reason

Find references for queue + side evidence inspector layouts.
Focus on error prevention, before/after correction, auditability, and fast keyboard review.
Do not optimize for marketing dashboard aesthetics.
Return a markdown report with patterns, anti-patterns, and MouseDB-specific recommendations.
```

### OCR Correction Prompt

```text
Use Lazyweb to research image annotation and OCR correction interfaces.

Use synthetic data only:
- fake image: placeholder cage card drawing
- fields: raw strain text, DOB raw, mouse count, note line
- confidence: 62%, 81%, 96%
- correction flow: raw value, normalized suggestion, user correction, reason

Look for UI patterns where an image/ROI is shown beside structured extracted fields.
Prioritize correction speed, uncertainty visibility, and traceability.
Return recommendations for MouseDB's Photo/OCR correction page.
```

### Spreadsheet Export Preview Prompt

```text
Use Lazyweb to find spreadsheet-like data grid references for export preview.

Use synthetic MouseDB export rows:
- workbook: separation.xlsx
- columns: source_photo, mouse_id, strain, DOB, sex, genotype, status
- row states: ready, blocked_by_review, stale_after_correction
- actions: preview, jump to review, download final export

Focus on Excel compatibility, blocked row visibility, and non-editable canonical export previews.
Do not suggest direct editing of canonical state inside the grid.
```

### Genotyping Review Prompt

```text
Use Lazyweb to research review interfaces for lab-like sample result decisions.

Use synthetic data only:
- sample IDs: SAMPLE-001, SAMPLE-002
- target gene: GeneA
- raw result: band present, weak band, no band
- final decision: positive, negative, ambiguous, needs rerun
- evidence: placeholder protocol image, fake gel lane label

Find patterns for structured review, evidence links, and final decision audit trails.
Do not infer biology. Treat all results as human-reviewed decisions.
```

## Final Recommendation

Lazyweb is approved only as a developer-side reference tool. It is useful for researching Review Queue, OCR correction, data grid, detail page, and evidence-inspector patterns with fake data. It is not approved for runtime integration, product logic, actual lab data handling, or canonical requirements.
