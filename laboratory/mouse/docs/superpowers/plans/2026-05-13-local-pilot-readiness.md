# Local Pilot Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the current local MouseDB MVP from verified prototype to a safe, reviewable, small-lab pilot.

**Architecture:** Keep the current local-first FastAPI + static UI + SQLite shape. Strengthen the source photo -> parsed/intermediate evidence -> review item -> canonical candidate -> explicit apply -> export/view path without turning OCR, Excel, or generated artifacts into canonical truth.

**Tech Stack:** Python, FastAPI, SQLite, pytest, Playwright, vanilla HTML/CSS/JS, openpyxl, local Tesseract OCR where available, optional approval-gated OpenAI extraction.

---

## Document Boundary

Layer classification: implementation planning / non-canonical project note.

Canonical: false.

This plan does not define product behavior by itself. `AGENTS.md`, `final_mouse_colony_prd.md`, committed tests, and runtime code remain the executable and product references.

## File Map

- `app/main.py`: current local API surface for photos, review, canonical candidates, exports, cages, matings, litters, genotyping, and read models.
- `app/db.py`: local SQLite schema, compatibility migrations, seed vocabularies, and indexes.
- `static/index.html`: main local browser UI.
- `scripts/verify-*.py` and `scripts/verify-*.js`: executable smoke, E2E, safety, and acceptance gates.
- `tests/`: current executable contract for data boundaries, review gating, export provenance, OCR draft handling, and CLI behavior.
- `docs/DOCUMENTATION_MAP.md`: documentation precedence and known mismatch map.
- `README.md`: user/developer setup, runtime, and verification entry point.
- `mousedb/`: CLI-first colony service layer, separate from the FastAPI prototype.

## Current Readiness Baseline

- Python test suite passes: 221 tests.
- Local scaffold verification passes.
- MVP browser verification passes.
- Synthetic photo E2E passes.
- Browser photo-to-export E2E passes.
- Synthetic draft extraction passes with local OCR marked as review aid, not canonical truth.
- Cage-card safety probes pass: 10/10.
- Acceptance matrix verifier passes.

The MVP is ready for controlled local pilot with copied/non-production data. It is not yet ready to be the lab's only operational system of record.

## Task 1: Freeze A Pilot Baseline

**Files:**
- Modify: `README.md`
- Modify: `docs/DOCUMENTATION_MAP.md`
- Create: `docs/pilot_readiness_baseline_2026-05-13.md`

- [ ] Record the exact branch, commit hash, Python version, Node version, and verification commands used for the pilot baseline.
- [ ] Add a short README section named `Pilot Baseline` that points users to the baseline document.
- [ ] State that the pilot must use copied or synthetic data first.
- [ ] Re-run:

```powershell
python -m pytest tests
npm test
npm run test:local
npm run test:photo-e2e
npm run test:browser-photo-export-e2e
npm run test:synthetic-draft-extraction
npm run test:cage-card-skill-gym
python scripts/verify-acceptance-matrix.py
git status --short --ignored
```

- [ ] In the baseline document, classify any generated folders as ignored runtime artifacts: `.venv/`, `node_modules/`, `data/`, `mousedb_artifacts/`, `__pycache__/`, `.pytest_cache/`.
- [ ] Commit only documentation files for this task.

## Task 2: Real Photo Pilot Dataset Protocol

**Files:**
- Create: `docs/real_photo_pilot_protocol_2026-05-13.md`
- Modify: `README.md`
- Optional test: `tests/test_real_photo_protocol_docs.py`

- [ ] Define the first pilot dataset size: 20-30 cage-card photos copied from non-destructive source storage.
- [ ] Require each pilot photo to be labeled by card type: separated, mating, unclear, or other.
- [ ] Require manual expected values for only the fields needed to evaluate the workflow: raw strain text, mouse IDs/note lines, sex/count, DOB, mating/litter note, and expected review blockers.
- [ ] State that real photos remain `raw source` and pilot labels remain `review item / test fixture` until explicitly adopted.
- [ ] Add a README link under the cage-card safety or local workbook section.
- [ ] Verify docs can be found from `docs/DOCUMENTATION_MAP.md`.

## Task 3: Real Photo Accuracy Harness

**Files:**
- Create: `config/real_photo_validation_cases.example.json`
- Create: `scripts/verify-real-photo-pilot.py`
- Create: `tests/test_real_photo_pilot_verifier.py`
- Modify: `package.json`

- [ ] Add an example manifest schema with local-only file paths, expected fields, expected review level, and expected export-blocking state.
- [ ] Implement a verifier that reads the manifest, checks each referenced photo exists, and reports coverage by card type and expected risk.
- [ ] Make the verifier fail if a case has no source photo path, no expected review policy, or no traceability label.
- [ ] Add `npm run test:real-photo-pilot` as a wrapper around `python scripts/verify-real-photo-pilot.py --manifest config/real_photo_validation_cases.example.json`.
- [ ] Test that the example manifest passes structure validation without requiring private photos.
- [ ] Keep all real photo paths local-only and out of Git.

## Task 4: Real Photo Manual Walkthrough

**Files:**
- Create: `docs/manual_pilot_walkthrough_2026-05-13.md`
- Modify: `README.md`

- [ ] Write a step-by-step pilot flow from `start.bat` to final Excel download.
- [ ] Include the exact expected user decisions: upload photos, choose whether AI extraction is allowed, manually correct uncertain fields, inspect Focus Review, apply canonical candidate, export XLSX.
- [ ] Include failure handling: upload error, OCR unavailable, OpenAI key missing, review blocker still open, export blocked, duplicate active mouse conflict.
- [ ] Include a final instruction to inspect `data/`, `mousedb_artifacts/`, and export log after a pilot run.

## Task 5: OCR Quality Triage

**Files:**
- Modify: `scripts/verify-synthetic-draft-extraction.py`
- Create: `docs/ocr_quality_triage_2026-05-13.md`
- Create or modify: `tests/test_local_ocr_provider.py`

- [ ] Convert current OCR quality categories into explicit pilot triage labels: usable hint, partial hint, garbled, empty.
- [ ] Ensure garbled or empty OCR never creates canonical candidates directly.
- [ ] Document which image problems should route to manual transcription: blur, crop, shadow, handwritten prime/circle ambiguity, dense mating notes.
- [ ] Add tests that garbled and empty OCR are review-only signals.

## Task 6: Review Queue Pilot Ergonomics

**Files:**
- Modify: `static/index.html`
- Modify: `app/main.py`
- Modify: `tests/test_review_attention.py`
- Modify: `scripts/verify-mvp.js`

- [ ] Add a pilot-friendly grouping summary for open Focus Review items by source photo.
- [ ] Keep `must_review`, `quick_check`, `trace_only`, and `hidden_default` semantics unchanged.
- [ ] Add a visible count of reviews that block export versus reviews retained only for traceability.
- [ ] Verify that quick/trace items do not become invisible in audit views.
- [ ] Extend MVP Playwright checks to assert source-photo grouping appears after fixture import.

## Task 7: Canonical Apply Audit Tightening

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_artifact_workflow.py`
- Modify: `tests/test_photo_transcription_transactions.py`
- Modify: `tests/test_mouse_event_evidence_enforcement.py`

- [ ] Add or strengthen tests that canonical apply writes mouse state, mouse event, action log, source evidence, and candidate status in one transaction.
- [ ] Add a rollback test for a forced failure during canonical apply.
- [ ] Ensure before/after values are present for movement, death/status, genotype, and review-applied corrections.
- [ ] Ensure internal IDs remain hidden from ordinary UI labels unless shown in audit/debug views.

## Task 8: Export Provenance Pilot Pack

**Files:**
- Modify: `app/main.py`
- Modify: `static/index.html`
- Modify: `tests/test_artifact_workflow.py`
- Modify: `tests/test_browser_photo_export_e2e.py`
- Modify: `scripts/verify-browser-photo-export-e2e.js`

- [ ] Ensure each XLSX download creates or links an export manifest.
- [ ] Ensure the manifest links accepted state, source photo IDs, note item IDs, validation report path, query/filter, expected filename, and generated filename.
- [ ] Add UI access to preview the manifest and validation report from export log.
- [ ] Test that blocked exports create blocked export log entries without writing risky final workbooks.

## Task 9: Legacy Excel Import Safety Pass

**Files:**
- Modify: `scripts/parse_legacy_workbooks.py`
- Modify: `app/main.py`
- Modify: `tests/test_legacy_workbook_parser.py`
- Modify: `tests/test_legacy_workbook_import_api.py`
- Create: `docs/legacy_excel_pilot_rules_2026-05-13.md`

- [ ] Confirm every imported workbook row remains `export or view` or `parsed/intermediate`, not canonical.
- [ ] Add pilot rules for how predecessor Excel rows can create review candidates.
- [ ] Add tests for source-cell traceability on ambiguous or merged workbook rows.
- [ ] Add tests that newer photo-backed evidence outranks older Excel rows during evidence reconciliation.

## Task 10: Backup And Restore Drill

**Files:**
- Create: `scripts/backup-local-pilot.ps1`
- Create: `scripts/restore-local-pilot.ps1`
- Create: `docs/local_backup_restore_2026-05-13.md`
- Optional test: `tests/test_backup_restore_docs.py`

- [ ] Back up `data/mouse_lims.sqlite`, `data/photos/`, `data/exports/`, and `mousedb_artifacts/`.
- [ ] Include timestamped backup folder names.
- [ ] Refuse to overwrite an existing restore target unless the user passes an explicit force flag.
- [ ] Document that backups are local operational copies, not canonical external archive policy.
- [ ] Run one restore drill on copied pilot data before any real pilot.

## Task 11: Documentation Encoding Repair

**Files:**
- Modify: `docs/DOCUMENTATION_MAP.md`
- Repair or rewrite affected Korean docs listed in the documentation map.

- [ ] Identify mojibake-corrupted Korean files with headings or body text that cannot be reviewed reliably.
- [ ] For each file, either restore from a known-good UTF-8 source or rewrite the lost section with an explicit note that it was reconstructed.
- [ ] Do not silently summarize away damaged content.
- [ ] Add a short repair log with date, source, and reviewer.
- [ ] Keep repaired docs classified as non-canonical unless the PRD adopts them.

## Task 12: Pilot Operator Checklist

**Files:**
- Create: `docs/pilot_operator_checklist_2026-05-13.md`
- Modify: `README.md`

- [ ] Write a one-page checklist for the lab user before, during, and after a pilot session.
- [ ] Include: use copied photos, confirm assigned strains, upload batch, review blockers, inspect source photo, apply only reviewed candidates, export only when ready, save backup after session.
- [ ] Include a stop condition list: unclear duplicate identity, unexpected genotype, missing source photo, failed export validation, or any external inference safety concern.

## Task 13: Small Pilot Run

**Files:**
- Create: `docs/pilot_run_log_template_2026-05-13.md`
- Create after run: `docs/pilot_runs/YYYY-MM-DD-<label>.md`

- [ ] Run a 5-photo dry run with synthetic or copied non-production photos.
- [ ] Record number of photos, parse attempts, manual corrections, must-review items, quick-check items, canonical candidates applied, exports generated, and blockers found.
- [ ] Record time spent per photo and top three friction points.
- [ ] Do not add private source photos to Git.
- [ ] After the run, re-run the standard verification commands and record results.

## Task 14: Decide Pilot Go/No-Go Criteria

**Files:**
- Create: `docs/pilot_go_no_go_criteria_2026-05-13.md`

- [ ] Define minimum acceptable review traceability: every exported row links to source photo or note item.
- [ ] Define maximum allowed unresolved `must_review` blockers before export: zero.
- [ ] Define manual review requirement for low-confidence or garbled OCR: always review.
- [ ] Define rollback requirement: backup exists before pilot and restore is tested.
- [ ] Define success criteria for the first real pilot: no lost source photos, no silent canonical overwrite, no final export while blockers are open, and pilot user can explain source evidence for exported rows.

## Suggested Execution Order

1. Task 1: Freeze A Pilot Baseline.
2. Task 2: Real Photo Pilot Dataset Protocol.
3. Task 3: Real Photo Accuracy Harness.
4. Task 10: Backup And Restore Drill.
5. Task 12: Pilot Operator Checklist.
6. Task 4: Real Photo Manual Walkthrough.
7. Task 13: Small Pilot Run.
8. Task 5: OCR Quality Triage.
9. Task 6: Review Queue Pilot Ergonomics.
10. Task 7: Canonical Apply Audit Tightening.
11. Task 8: Export Provenance Pilot Pack.
12. Task 9: Legacy Excel Import Safety Pass.
13. Task 11: Documentation Encoding Repair.
14. Task 14: Decide Pilot Go/No-Go Criteria.

## Verification Gate Before Saying Pilot-Ready

Run all of:

```powershell
python -m pytest tests
npm test
npm run test:local
npm run test:photo-e2e
npm run test:browser-photo-export-e2e
npm run test:synthetic-draft-extraction
npm run test:cage-card-skill-gym
python scripts/verify-acceptance-matrix.py
git status --short --ignored
```

Expected:

- All tests pass.
- No task source files are unstaged.
- Only ignored runtime artifacts remain untracked, such as `.venv/`, `node_modules/`, `data/`, `mousedb_artifacts/`, `__pycache__/`, and `.pytest_cache/`.

