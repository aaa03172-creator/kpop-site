# Low-Fatigue Colony UI Implementation Plan

## Document Status

Layer classification: implementation planning / non-canonical project documentation.

Canonical status: non-canonical. This plan does not define database truth, final API contracts, export schemas, or lab workflow policy. It proposes small, additive implementation slices that must still be proven by tests, reviewed diffs, and the existing `AGENTS.md`, `final_mouse_colony_prd.md`, and `docs/superpowers/specs/2026-05-09-low-fatigue-colony-ui-design.md`.

Data boundary: this document is a planning artifact. Any endpoint, response shape, UI behavior, or test fixture below remains proposed until implemented and merged in code.

## Goal

Implement the low-fatigue UI direction in small slices without fabricating colony state.

The first implementation target is a read-only Focus Review view model that groups existing review items by source photo/card evidence and exposes review urgency without changing canonical state. Broader pages such as Colony State, Schedule, Mouse Timeline, Evidence Ledger, and Excel Export should follow only when their data can be derived from accepted records, configured rules, or existing export/evidence views.

## Guardrails

- Do not add canonical tables in this plan slice.
- Do not rewrite existing runtime, DB, or API contracts.
- Do not hard-code strains, genotype categories, dates, mouse relationships, schedule rules, or colony counts as real product state.
- Do not render synthetic fallback mouse IDs, dates, strains, review counts, or schedule tasks when an API request fails.
- Do not add Google Calendar OAuth, live calendar sync, barcode, or QR scope.
- Keep Excel preview/export as `export or view`, never as a canonical editing grid.
- Keep source photos and note-line evidence visible and traceable from review work.
- Treat ambiguous data as non-canonical until a reviewer accepts it through existing gates.

## Source Documents

- `AGENTS.md`
- `final_mouse_colony_prd.md`
- `docs/superpowers/specs/2026-05-09-low-fatigue-colony-ui-design.md`
- `docs/ctx2skill_lite_adoption_review.md`
- Existing tests:
  - `tests/test_review_attention.py`
  - `tests/test_artifact_workflow.py`
  - `tests/test_legacy_workbook_import_api.py`
  - `tests/test_cage_card_skill_gym.py`
- Existing frontend verification:
  - `scripts/verify-mvp.js`

## Recommended Slice 1: Focus Review Read Model

Purpose: make review work easier to scan while preserving evidence-first boundaries.

Data layer:

- Input: existing `review_queue`, `parse_result`, `photo_log`, `card_snapshot`, note item, and photo evidence records.
- Output boundary: `export or view`.
- Canonical writes: none.

Expected behavior:

- Group open review items by source photo/card where evidence exists.
- Include only actual DB-backed rows and review items.
- Count `must_review` and `quick_check` as workload.
- Keep `trace_only` available as a filter or secondary detail, not primary workload.
- Mark source photo as primary evidence when a photo is present.
- Include evidence links or evidence summaries only from existing source records, note items, photo evidence, or review links.
- Preserve existing review actions; this read model should not create a new apply path.

Tests first:

- Add focused tests in `tests/test_low_fatigue_ui_contracts.py`.
- Seed the test database with real rows through existing helper functions or explicit DB inserts.
- Assert the read endpoint returns only seeded values.
- Assert the payload declares `source_layer == "export or view"`.
- Assert no fabricated fallback records appear when the database is empty.
- Assert review cards include evidence references and attention levels.

Candidate endpoint:

- `GET /api/ui/focus-review`

Acceptance criteria:

- Focused pytest for the new read model passes.
- `npm run test:local` passes.
- `npm test` passes if the static UI is touched.
- `npm run verify` passes before PR.
- Codex review finds no boundary or evidence regressions.

## Recommended Slice 2: Render Focus Review Cues

Purpose: use the already adopted visual cue rules in the UI without changing data semantics.

Scope:

- Render the Focus Review read model in `static/index.html`.
- Reuse the existing low-fatigue attention classes:
  - `attention-must-review`
  - `attention-quick-check`
  - `attention-trace-only`
- Preserve visible text labels such as `Focus review`, `Needs quick confirmation`, and `Trace only`.
- Keep source photo and evidence controls visible.

Fallback rule:

- If the read endpoint fails, show a clear loading/error/empty state.
- Do not show fabricated mice, strains, dates, calendar sync, export rows, or review counts.

Verification:

- Extend `scripts/verify-mvp.js` with DOM assertions that rendered cards expose attention text, `data-attention-level`, and accessible actions.
- Confirm evidence actions remain visible.

## Later Slices

Implement these only after the required source data exists or the read model can derive it from accepted records:

- Colony State: accepted current state only, with links to Focus Review for unresolved blockers.
- Colony Schedule: derived from accepted events and configurable rules; external calendar remains a mirror.
- Mouse Timeline: accepted events only by default; proposed events remain in Focus Review.
- Related Mice/Pedigree: derived from accepted mating, litter, and parent-child events.
- Evidence Ledger: evidence search and trace status from existing source/evidence tables.
- Excel Export: workbook preview from accepted structured state and existing export preview helpers.

## Explicit Non-Goals

- No fabricated sample state in runtime code.
- No full UI rewrite.
- No canonical schedule schema in this plan.
- No direct canonical editing in an Excel-like grid.
- No automatic acceptance of OCR, workbook rows, or inferred biological state.
- No calendar OAuth or barcode/QR implementation.

## Review Checklist

Before any implementation PR based on this plan:

- Every new response shape is classified by data boundary.
- Every displayed mouse, date, strain, task, event, or evidence item comes from a real source table, accepted state, or test fixture.
- Empty states are honest and do not impersonate lab data.
- Review blockers remain actionable in Focus Review.
- Trace-only items do not inflate primary workload counts.
- Source photo evidence remains primary in photo/card review contexts.
- Excel and calendar surfaces are labeled as views or mirrors.
- `npm run verify` passes.
