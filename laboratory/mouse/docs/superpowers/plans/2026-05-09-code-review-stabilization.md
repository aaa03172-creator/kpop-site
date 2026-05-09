# Code Review Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

Layer classification: review item / implementation planning.
Canonical: false.

## Goal

Close the remaining whole-repository review risks before merge:

- Keep the Mouse Timeline read model stable as an `export or view` UI surface.
- Fix SQLite schema compatibility for users who already have local rows in legacy tables.
- Preserve traceability and avoid silent data loss during migration.

## Findings

### Mouse Timeline UI

Current risk is low. Static verification passes, and the current file has one `loadMouseTimelineReadModel` and one `renderMouseTimelineReadModel`. The implementation should remain covered by the static MVP verifier and focused UI contract tests.

### Non-Empty Legacy SQLite Migration

Current risk is high. A legacy `mouse_master` table with existing rows fails when `ensure_columns()` tries to add timestamp columns with `DEFAULT CURRENT_TIMESTAMP`. SQLite rejects non-constant defaults in `ALTER TABLE ... ADD COLUMN` for non-empty tables.

## Implementation Tasks

- [x] Confirm current MVP static verification passes with `npm test`.
- [x] Confirm Mouse Timeline has a single loader and renderer in `static/index.html`.
- [x] Add a non-empty legacy `mouse_master` row to `scripts/verify-local-app.py` so the verifier covers existing-user data.
- [x] Make `app/db.py` rewrite incompatible `DEFAULT CURRENT_TIMESTAMP` add-column definitions to a constant default during compatibility migrations.
- [x] Backfill timestamp compatibility columns to `CURRENT_TIMESTAMP` after adding them.
- [x] Run focused Mouse Timeline pytest coverage.
- [x] Run full repository verification with `npm run verify`.

## Verification

Required commands:

```powershell
npm test
python -m pytest tests/test_low_fatigue_ui_contracts.py::test_mouse_timeline_empty_state_does_not_fabricate_events tests/test_low_fatigue_ui_contracts.py::test_mouse_timeline_shows_accepted_events_without_review_details -q
npm run verify
```

Expected result:

- MVP verification passes.
- Mouse Timeline focused tests pass.
- Local app scaffold verification passes with an existing legacy mouse row.
- Full Python suite passes.

## Change Classification

- `app/db.py`: canonical structured state schema compatibility code.
- `scripts/verify-local-app.py`: review item / verification fixture.
- This plan: review item / implementation planning, non-canonical.
