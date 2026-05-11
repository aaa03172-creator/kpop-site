# Cage Card Photo Pipeline Implementation Audit

Layer classification: implementation audit / review item.
Canonical status: non-canonical. This audit checks the current implementation against `AGENTS.md`, `final_mouse_colony_prd.md`, `docs/cage_card_photo_pipeline_implementation_baseline_ko.md`, current artifact contracts, and focused tests. If this audit conflicts with adopted project documents or committed tests, call out the mismatch before implementation.

Date: 2026-05-11

## Scope

This audit checks the current cage-card photo pipeline implementation against the recommended baseline:

- raw photo and evidence preservation;
- parsed/intermediate versus canonical boundaries;
- canonical candidate apply evidence refs;
- high-risk mouse event evidence enforcement;
- genotype evidence enforcement;
- validation report and export manifest provenance;
- domain-specific apply flows for cage movement, mating, litter, offspring generation, and weaning.

It does not change runtime behavior.

## Verification Run

Focused verification command:

```powershell
python -m pytest tests/test_photo_evidence_ledger_schema.py tests/test_mouse_event_evidence_enforcement.py tests/test_genotyping_evidence_enforcement.py tests/test_artifact_workflow.py
```

Result:

- 19 passed;
- 89 FastAPI deprecation warnings from dependencies;
- no test failures.

## Current Implementation Fit

### Raw photo and field-level evidence

Status: aligned.

The implementation has `photo_log`, `parse_result`, `card_snapshot`, `card_note_item_log`, `photo_evidence_item`, and `review_evidence_link` tables. Manual/photo transcription creates photo evidence items and links review items to evidence rows.

Audit implication:

- source photos remain the raw source anchor;
- parsed fields and note lines remain draft/review evidence;
- review audit can display linked photo evidence rows.

### Canonical candidate apply path

Status: mostly aligned.

`apply_canonical_candidate`:

- requires preview without blockers;
- requires candidate status `draft`;
- requires linked review status `resolved`;
- reads parsed mouse note lines;
- writes `mouse_master`;
- writes a `canonical_candidate_applied` mouse event;
- prefers a linked `photo_evidence_item` for the note line;
- stores `photo_evidence_id` and `source_photo_id` in event details when available;
- updates the evidence row with `linked_mouse_id`, `linked_event_id`, and `status = linked`;
- records an action log before/after status transition.

Focused test coverage confirms this behavior in `test_canonical_candidate_apply_links_note_evidence_to_created_event`.

Residual gap:

- The event type is generic (`canonical_candidate_applied`) rather than domain-specific movement/death/separation/litter event semantics. It preserves evidence, but the next slice should ensure inferred domain events created from accepted note-line status also carry the same specific evidence refs.

### Canonical apply validation artifact

Status: partially aligned.

`build_canonical_apply_validation_report` and `persist_validation_report_artifact` produce a non-canonical validation report artifact. Current checks include:

- duplicate active mouse ID;
- missing source trace.

Focused test coverage confirms missing source trace blocks the report.

Residual gap:

- The baseline expects deterministic checks for impossible dates, genotype conflict, cage mismatch, ambiguous ear label, uncertain strike status, and count mismatch. Some of these are checked elsewhere in review/parse flows, but the canonical apply validation artifact does not yet represent the full baseline blocker set.

### Generic high-risk mouse event evidence gate

Status: aligned.

`create_mouse_event` uses evidence validation for high-risk event types. High-risk event strings include death/dead, movement/moved, separation/separated, wean/weaned, mating/paired, litter, genotype/genotyped, and related variants.

High-risk events require at least one of:

- `source_record_id`;
- `details.source_photo_id`;
- `details.photo_evidence_id`;
- `details.source_note_item_id`.

Focused tests confirm:

- evidence-free death event is rejected;
- source-record-backed death event is accepted;
- photo-evidence-backed death event is accepted.

Residual gap:

- This gate applies to the generic event API. Several domain-specific service flows write directly to `mouse_event` with manual `source_record_id`, bypassing the generic `create_mouse_event` helper. They still include a source record, but not always the most specific photo/note/evidence refs.

### Genotype result evidence enforcement

Status: aligned.

Genotype confirmation requires evidence:

- `source_photo_id`;
- `photo_evidence_id`;
- or `source_record_id`.

When accepted, it updates genotype state and creates a `genotyped` mouse event with evidence details.

Focused tests confirm evidence-free genotype confirmation is rejected and source-photo-backed confirmation records evidence and event state.

Residual gap:

- Genotyping sheet cell or gel-band `photo_evidence_item` capture remains a later expansion. The current gate is suitable for MVP safety.

### Export validation and manifest provenance

Status: aligned for current export flows.

Current export support includes:

- export validation report artifact creation;
- export manifest artifact creation;
- source refs from preview rows;
- state watermark from latest data change;
- export log notes preserving manifest path, validation report ID, and state watermark;
- blocked export paths that persist provenance before returning a 409.

Focused tests confirm:

- export validation report uses current preview trace;
- export manifest links validation report and sources;
- export log preserves manifest provenance;
- export log can resolve validation report path from manifest.

Residual gap:

- Source refs are only as complete as preview rows. Any preview row missing source refs can still weaken manifest value, so export preview generation should remain part of future audit.

## Domain-Specific Flow Gaps

### Cage movement flow

Status: acceptable MVP source trace, but not full evidence specificity.

The cage movement flow creates a manual source record, updates assignment state, writes a `moved` mouse event with `source_record_id`, and records the prior/current cage labels in details.

Gap:

- It does not accept or propagate `source_photo_id`, `source_note_item_id`, or `photo_evidence_id`.
- It is evidence-backed through a manual source record, but not linked to the most specific cage-card note-line evidence when movement is inferred from photo review.

Recommendation:

- Add optional photo/note/evidence refs to the movement payload or service layer.
- Include those refs in `mouse_event.details`.
- Add tests for movement created from accepted note-line evidence.

### Mating creation flow

Status: acceptable MVP source trace, but manual-entry centered.

The mating flow creates a manual source record, writes `mating_registry`, links parent mice, and writes `paired` events with `source_record_id`.

Gap:

- It does not preserve source photo, parent note-line, or photo evidence refs in the mating events when the mating is derived from a cage-card photo.

Recommendation:

- Allow mating creation from a reviewed mating-card evidence bundle.
- Preserve parent note-line refs and source photo refs in `paired` event details.

### Litter creation flow

Status: acceptable MVP source trace, but manual-entry centered.

The litter flow creates a manual source record, writes `litter_registry`, and writes `litter_produced` events for parents with `source_record_id`.

Gap:

- It does not preserve source photo, litter note-line, or `photo_evidence_id` when the litter is derived from a mating-card note line.

Recommendation:

- Add a reviewed litter-note evidence path.
- Include note item and photo evidence refs in parent `litter_produced` event details.

### Offspring generation flow

Status: acceptable MVP source trace, but derived from reviewed litter record rather than direct photo evidence.

The offspring generation flow creates a manual source record, writes offspring `mouse_master` rows, optional cage assignments, and `born` events with source record and litter details.

Gap:

- It does not link born events to the original litter note-line/photo evidence unless that evidence is represented through the broad source record.

Recommendation:

- Propagate original litter source refs from `litter_registry` or an accepted evidence bundle into offspring `born` event details.

### Litter weaning flow

Status: good before/after action logging, but not full evidence specificity.

The weaning flow creates a manual source record, updates `litter_registry`, updates selected offspring state, writes one `weaned` event per affected offspring, and writes a `litter_weaned` action log with before/after values.

Gap:

- It does not link `weaned` events to a source photo, note item, or photo evidence item when weaning is inferred from a struck litter note line.

Recommendation:

- Add optional source refs to weaning payload/service.
- Include original litter source refs plus weaning-specific evidence refs in each `weaned` event.

## Recommended Next Implementation Slice

Recommended next slice: **domain-specific event evidence propagation**.

Why this slice:

- generic high-risk event gates are already in place;
- canonical candidate apply already links note evidence to generic applied events;
- genotype evidence enforcement is already in place;
- export provenance is already in place;
- the remaining safety gap is that domain-specific service flows often preserve only a broad manual source record.

Proposed implementation order:

1. Add a small internal evidence-ref helper that normalizes optional refs:
   - `source_record_id`;
   - `source_photo_id`;
   - `source_note_item_id`;
   - `photo_evidence_id`.
2. Use the helper when writing domain-specific `mouse_event` rows.
3. Start with movement and weaning because they directly correspond to crossed-out note evidence.
4. Then extend mating/litter/offspring generation to preserve reviewed mating-card and litter-note evidence.
5. Add tests that prove event details include the most specific available evidence refs, not only a manual source record.

## Audit Verdict

The current implementation satisfies the core baseline at the infrastructure level:

- raw/photo evidence ledger exists;
- review/evidence links exist;
- canonical candidate apply is guarded and evidence-linked;
- high-risk generic events require evidence;
- genotype confirmation requires evidence;
- export validation and manifests preserve provenance.

The main implementation gap is not missing infrastructure. It is incomplete propagation of the most specific evidence refs through domain-specific apply flows.

For the next code slice, do not add a new large abstraction or UI first. Tighten event evidence propagation in movement, weaning, mating, litter, and offspring flows, with focused regression tests.
