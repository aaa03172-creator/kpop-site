# MouseDB Data Utilization Implementation Review

Layer classification: implementation/product review / review item.
Canonical status: non-canonical. This review compares the current product idea of using extracted cage-card data beyond transcription reduction against `AGENTS.md`, `final_mouse_colony_prd.md`, `README.md`, current implementation, and focused tests. If this document conflicts with adopted project documents or committed tests, call out the mismatch before implementation.

Date: 2026-05-12

## Review Question

The project started as a way to reduce the user's burden of extracting and organizing handwritten cage-card and Excel records. As extraction, review, and canonical state structures accumulate, the question is whether the data should also support higher-value workflows such as:

- mouse timeline;
- operational checks and next actions;
- future Assistant/API/MCP integration.

## Review Outcome

Disposition: accept the direction, but treat it as a staged extension of the existing evidence-first workflow.

The current implementation already contains meaningful foundations for all three ideas. The next product step should not be a standalone RAG or assistant layer. It should first organize existing read models into a practical operations flow:

```text
source evidence -> parsed/review evidence -> accepted state/events -> operations read models -> future assistant/API/MCP wrapper
```

In this project, extracted data is most valuable when it reduces the user's next operational decision, not when it becomes an independent AI memory.

## Baseline Boundary

The data utilization layer should keep the same project boundaries:

- source photos, imported Excel files, and original note text remain raw evidence;
- OCR, AI extraction, workbook parsing, and normalization suggestions remain parsed/intermediate or review evidence until accepted;
- accepted mouse, cage, mating, litter, genotype, and event state remain MouseDB-owned canonical structured state;
- timeline views, operations lists, search results, assistant summaries, exports, validation reports, and dashboards are export/view or cache unless an adopted PRD section says otherwise;
- high-risk changes still require review, evidence, and preview-before-commit.

## Current Implementation Fit

### Mouse Timeline

Status: implemented foundation, needs product polish.

The CLI MouseDB package has a `mouse timeline` command backed by `mouse_event`. Events are written for mouse creation, cage movement, genotyping, mating/litter activity, corrections, and weaning in the CLI/service layer.

The web prototype also has `/api/ui/mouse-timeline`, which returns an export/view timeline with lineage context, event rows, source records, source photos, note items, photo evidence refs, and focus-review attention links.

Implementation implication:

- the timeline idea is not speculative;
- the project already treats events as durable history and card/photo records as evidence-backed observations;
- the next improvement should make the timeline a primary user workflow for "How did this mouse get here?" rather than a secondary inspection endpoint.

Residual gaps:

- some accepted events are still generic, such as canonical candidate application, instead of domain-specific movement, separation, death, litter, or genotype events;
- timeline completeness depends on whether upstream accepted actions consistently write source refs into event details;
- CLI and web event models are related in concept but not yet a single polished product contract.

### Operational Checks And Next Actions

Status: partially implemented across several flows.

The current implementation already generates next-action style signals in several places:

- photo/upload worklists can point to transcription, comparison review, review resolution, canonical candidate mapping, canonical apply, or ready-to-close;
- review queue logic separates attention levels such as `must_review`, `quick_check`, `trace_only`, and `hidden_default`;
- genotyping flows suggest outcomes such as awaiting result, review result, consider for mating, available for experiment, keep for maintenance, or cleanup/confirm;
- export readiness uses open focus-review blockers, genotype blockers, validation reports, and export logs;
- CLI MouseDB exposes `colony summary` and `experiment-ready` query commands.

Implementation implication:

- the project already has the pieces for a practical "Operations Home" or "Today" surface;
- the main missing layer is aggregation and prioritization, not new domain theory;
- next actions should remain derived read models, not canonical state by themselves unless a future PRD explicitly adopts a schedule/task table.

Recommended grouping:

1. Focus Review: high-risk review items that block canonical apply or export.
2. Photo Worklist: uploaded photos needing transcription, comparison review, or candidate mapping.
3. Canonical Apply: resolved candidates waiting for preview/apply.
4. Genotyping: sample needed, awaiting result, review result, available for experiment, consider for mating.
5. Breeding/Weaning: due, blocked, or review-required litter and mating actions.
6. Export Readiness: blockers, stale exports, and ready downloads.

Residual gaps:

- next-action values exist in multiple subsystems but are not yet normalized into one operator-facing contract;
- not every next action has a stable target URI, target type, evidence refs, and risk class;
- some next-action labels are implementation-shaped rather than lab-workflow-shaped.

### Assistant/API/MCP Readiness

Status: foundation exists; adapter should remain deferred.

The implementation already supports assistant-readiness habits:

- CLI commands expose JSON output;
- stable service boundaries exist in the CLI-first MouseDB package;
- web APIs expose focus review, timeline, search, audit trace, export preview, genotyping dashboard, and review audit data;
- SQLite FTS search indexes review items, note evidence, source records, and mouse-related data;
- assistant integration documentation already says summaries must be non-canonical views and must not hide unresolved review blockers.

Implementation implication:

- a future assistant, API, or MCP wrapper should be thin orchestration over MouseDB-owned state;
- the next useful step is not MCP itself, but named assistant-safe read models.

Recommended read models before any adapter:

- `MouseTimelineSummary`: mouse identity, accepted events, lineage, evidence refs, unresolved attention links.
- `FocusReviewSummary`: must-review and quick-check items with source evidence and operator action.
- `NextActionSummary`: grouped operational tasks with target refs, risk class, blocker reason, and source evidence.
- `ExportReadinessSummary`: export type, blocker count, stale/export status, validation report refs, and intended file.
- `ExperimentCandidateSummary`: candidate mice with genotype, age, sex, status, warnings, and evidence refs.

Residual gaps:

- existing APIs are useful but not yet named or versioned as assistant-safe contracts;
- URI planning such as `mousedb://mouse/{id}` is documented but not runtime-stable;
- MCP/API implementation should remain deferred until read models and review/export gates are stable.

## RAG Assessment

This direction is still not RAG-centered.

Search is useful for finding mouse IDs, strains, review items, note text, and source evidence. A future assistant may use search as one input. However, colony truth should come from MouseDB structured records and event history, not from a vector memory or assistant-owned copy of extracted records.

Safe framing:

```text
structured evidence-backed operations system with optional assistant/search interface
```

Risky framing:

```text
RAG knowledge base of colony records
```

## Product Recommendation

The next product slice should be:

```text
Operations Home + Mouse Timeline Polish
```

Scope:

- surface mouse timeline as a first-class way to inspect accepted history;
- aggregate existing next-action signals into one operations read model;
- keep all operations entries traceable to source photo, note item, review item, accepted event, or export manifest;
- preserve review blockers and uncertainty instead of summarizing them away;
- keep assistant/API/MCP integration as a later wrapper over these read models.

Suggested order:

1. Define `NextActionSummary` as export/view.
2. Normalize task fields: `task_id`, `family`, `label`, `status`, `risk_class`, `target_type`, `target_id`, `target_label`, `blocker_reason`, `evidence_refs`, `source_layer`.
3. Populate it from existing photo worklist, focus review, canonical candidates, genotyping dashboard, export readiness, and breeding/weaning checks.
4. Add focused tests proving unresolved review/export blockers remain visible.
5. Polish `/api/ui/mouse-timeline` so event labels, evidence refs, and attention links are consistent.
6. Only after that, define assistant-facing summaries or MCP/API wrappers.

## Implementation Review Notes

No runtime behavior changes are made by this document.

Observed alignment:

- `mouse_event` exists and supports event history.
- `review_queue`, `action_log`, `correction_log`, and evidence tables preserve review and correction traceability.
- `export_log`, validation report artifacts, and export blockers support readiness-based exports.
- search and audit APIs already provide non-canonical read surfaces.

Observed mismatch or risk:

- product language says "next action", but implementation has several local next-action vocabularies that are not yet one contract;
- assistant-readiness is present as a habit, but the runtime does not yet expose stable assistant-safe summary families;
- timeline and operations views should avoid becoming hidden canonical state or assistant memory.

## Verification Status

This review was prepared by inspecting current documentation, source files, existing focused tests, and the focused verification run below.

Focused verification command:

```powershell
python -m pytest tests/test_mousedb_cli.py tests/test_review_attention.py tests/test_search_index.py tests/test_artifact_workflow.py tests/test_mouse_event_evidence_enforcement.py
```

Result:

- 72 passed;
- 90 FastAPI deprecation warnings from dependencies;
- no test failures.
