# Labeling Rule UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make labeling session rule assumptions visible and active in the Genotyping Worklist request flow.

**Architecture:** Add one read-only FastAPI endpoint backed by the existing `labeling_rule_set` and `labeling_rule_ear_sequence` tables. Update the existing static single-page app to fetch rule sets, render a selector and summary, and include `labeling_rule_set_id` in genotyping requests.

**Tech Stack:** FastAPI, SQLite, static HTML/CSS/JavaScript, pytest, local verification script.

---

### Task 1: Rule Set API

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_labeling_session_rules.py`

- [x] Add a function or endpoint that returns active rule sets with ID, display name, strain text, session date, numbering order, mouse-number scope, ear-sequence scope, crossed-out handling, sample mapping, default genotyping target, active flag, and ordered ear-label codes.
- [x] Add a pytest that initializes the database and asserts the default ApoM rule appears with `sample_mapping = "sample_id_equals_mouse_display_id"` and first ear labels `R_PRIME`, `L_PRIME`.
- [x] Run `python -m pytest -p no:cacheprovider tests/test_labeling_session_rules.py -v`.

### Task 2: Genotyping Worklist Selector

**Files:**
- Modify: `static/index.html`
- Verify: `scripts/verify-local-app.py`

- [x] Add a `select#requestLabelingRuleSet` to the Request Genotyping form.
- [x] Add a compact summary element showing selected rule policy: strain/session, sample mapping, default target, crossed-out handling, and first ear-label codes.
- [x] Fetch `/api/labeling-rule-sets` during `refresh()`.
- [x] Preserve the selected rule across refreshes when still available; otherwise choose the first active rule.
- [x] Include `labeling_rule_set_id` in the `/api/genotyping/request` POST body.
- [x] Wrap the request handler in `try/catch` so HTTP 409 details are displayed in `requestGenotypingMessage`.

### Task 3: Verification

**Files:**
- Verify: `tests/test_labeling_session_rules.py`
- Verify: `scripts/verify-local-app.py`

- [x] Run `python -m pytest -p no:cacheprovider tests/test_labeling_session_rules.py tests/test_review_attention.py -v`.
- [x] Run `npm run test:local`.
- [x] Re-check `git status --short --branch` and remove disposable caches.
