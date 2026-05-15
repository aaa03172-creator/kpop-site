# Real Photo Hybrid Evaluator Validation Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-only validation loop for real cage-card photos that compares reviewer corrections against OCR, AI, and hybrid note-line evaluator candidates.

**Architecture:** Reuse the existing private manifest and private accuracy reporter rather than adding canonical tables. Generate local-only private manifest/results templates from a source photo directory, then aggregate sanitized metrics from reviewer-filled scoring results.

**Tech Stack:** Python scripts, pytest, existing private real-photo verifier, existing sanitized private accuracy reporter.

---

### Task 1: Reporter Metrics

**Files:**
- Modify: `scripts/report-private-accuracy.py`
- Test: `tests/test_private_accuracy_reporter.py`

- [x] Add a failing pytest that feeds `hybrid_note_line_evaluator.scored_cases` with OCR, AI, and hybrid statuses, `reviewer_override`, false-positive/false-negative cases, and rule snapshot hashes.
- [x] Run `python -m pytest tests/test_private_accuracy_reporter.py -q` and confirm the new assertions fail because the summary does not expose those metrics yet.
- [x] Extend `hybrid_note_line_evaluator_metrics()` to emit sanitized `candidate_source_metrics` and `rule_snapshot_breakdown`.
- [x] Extend Markdown output with candidate-source and rule-hash breakdown tables.
- [x] Re-run the focused pytest and confirm it passes.

### Task 2: Real Photo Run Pack

**Files:**
- Create: `scripts/prepare-real-photo-hybrid-evaluator-run.py`
- Create: `tests/test_real_photo_hybrid_evaluator_run.py`
- Modify: `package.json`

- [x] Add a failing pytest that creates temporary image files, invokes the pack builder, and checks that it writes a private manifest, scoring template, and operator README.
- [x] Confirm CLI JSON output redacts the private source directory path.
- [x] Implement source directory scanning for `.jpg`, `.jpeg`, `.png`, `.heic`, `.tif`, `.tiff`, and `.webp`.
- [x] Write generated private artifacts under caller-provided output or ignored `data/private_real_photo_hybrid_evaluator_runs/<run-label>`.
- [x] Add `pilot:real-photo-hybrid-pack` to `package.json`.

### Task 3: Actual Folder Dry Run

**Files:**
- No committed private artifacts.

- [x] Run the pack script against the user-provided private `ApoM tgtg` source directory.
- [x] Confirm it detects 17 source photos and writes outputs under ignored `data/`.
- [x] Run `scripts/verify-real-photo-pilot.py` against the generated private manifest.
- [x] Do not commit generated private manifest/results/README.

### Task 4: Verification And Commit

**Files:**
- All task source/test/docs files only.

- [x] Run focused tests: `python -m pytest tests/test_private_accuracy_reporter.py tests/test_real_photo_hybrid_evaluator_run.py -q`.
- [x] Run broader verification: `npm run verify`.
- [x] Check `git status --short` and classify all changes.
- [x] Stage only task source/test/docs/package files.
- [x] Commit with a concise message.
