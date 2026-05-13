# Strict Photo E2E Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the default photo E2E path in `npm run verify` strict and non-skipping even when no real lab photo fixture database is available.

**Architecture:** Keep `scripts/verify-photo-e2e-cases.py` as the local real-photo verifier for optional lab-owned fixtures. Promote the synthetic/anonymized JPEG + SQLite generator path into the default `test:photo-e2e` gate, and have the gate fail if it ever reports skipped cases, missing coverage tags, or ambiguous layer boundaries.

**Tech Stack:** Python verifier scripts, pytest, npm scripts, local SQLite, generated Pillow JPEG fixtures.

---

### Task 1: Contract Tests

**Files:**
- Modify: `tests/test_synthetic_cage_card_fixtures.py`

- [x] **Step 1: Write failing tests**

Add assertions that `verify-synthetic-photo-e2e.py --json` reports:

```python
assert summary["strict_photo_e2e_gate"] is True
assert summary["verification"]["skipped"] == 0
assert summary["verification"]["status"] == "passed"
assert summary["layer_boundaries"]["raw_source"]["boundary"] == "raw source / test fixture"
assert summary["layer_boundaries"]["parsed_evidence"]["boundary"] == "parsed or intermediate result"
assert summary["layer_boundaries"]["review_item"]["boundary"] == "review item"
assert summary["layer_boundaries"]["export_view"]["boundary"] == "export or view"
```

Add package assertions:

```python
assert package["scripts"]["test:photo-e2e"] == "python scripts/verify-synthetic-photo-e2e.py --json"
assert package["scripts"]["test:real-photo-e2e"] == "python scripts/verify-photo-e2e-cases.py"
assert "npm run test:photo-e2e" in package["scripts"]["verify"]
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_synthetic_cage_card_fixtures.py -q`

Expected: FAIL because the summary does not yet expose `strict_photo_e2e_gate`, `status`, and `layer_boundaries`, and `test:photo-e2e` still points at the real-photo skip-capable script.

### Task 2: Strict Gate Implementation

**Files:**
- Modify: `scripts/verify-synthetic-photo-e2e.py`
- Modify: `package.json`

- [x] **Step 1: Implement strict summary checks**

Add a helper that marks the synthetic photo path as a strict gate and fails if any generated verification case is skipped, if coverage tags are missing, or if boundary metadata is absent.

- [x] **Step 2: Rewire npm scripts**

Set `test:photo-e2e` to the strict synthetic gate and preserve the old local real-photo verifier as `test:real-photo-e2e`.

- [x] **Step 3: Run test to verify it passes**

Run: `python -m pytest tests/test_synthetic_cage_card_fixtures.py -q`

Expected: PASS.

### Task 3: Documentation And Full Verification

**Files:**
- Modify: `docs/synthetic_cage_card_fixture_validation_ko.md`
- Modify if needed: `photo_e2e_validation_plan_ko.md`

- [x] **Step 1: Document the default strict gate**

State that `npm run test:photo-e2e` uses disposable synthetic/anonymized fixtures and must report `skipped: 0`; real-photo fixtures remain optional via `npm run test:real-photo-e2e`.

- [x] **Step 2: Run full verification**

Run: `npm run verify`

Expected: exit 0. After the run, immediately check `git status --short` and classify every changed or untracked file.
