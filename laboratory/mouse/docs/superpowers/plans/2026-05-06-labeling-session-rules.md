# Labeling Session Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable labeling session rules that improve note-line and genotyping parsing while preserving raw evidence and reviewability.

**Architecture:** Add a small configuration layer for rule sets and ear-label sequences, then apply those rules in a post-processing service after raw note parsing. Canonical mouse, death, and genotype writes continue through existing evidence-backed writer paths.

**Tech Stack:** Python, FastAPI app modules in `app/`, SQLite schema in `app/db.py`, pytest tests in `tests/`.

---

## File Structure

- Modify `app/db.py`: add tables and seed data for labeling rule sets and ordered ear-label sequences.
- Create `app/labeling_rules.py`: pure functions for loading/applying rule sets to parsed note items and sample rows.
- Modify `app/main.py`: call the post-processor where note items and genotyping records are listed or written, keeping raw values unchanged.
- Create `tests/test_labeling_session_rules.py`: focused unit tests for sequence reset, number continuity, crossed-out death handling, and sample matching.
- Optionally modify `static/index.html`: expose the selected rule set in batch/review views after backend behavior is stable.

### Task 1: Schema And Seeds

**Files:**
- Modify: `app/db.py`
- Test: `tests/test_labeling_session_rules.py`

- [ ] **Step 1: Write the failing schema test**

```python
from app import db


def test_labeling_rule_schema_seeds_default_apom_rule(tmp_path):
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    db.init_db()

    with db.connection() as conn:
        rule = conn.execute(
            """
            SELECT display_name, numbering_order, mouse_number_scope,
                   ear_sequence_scope, crossed_out_handling, sample_mapping,
                   genotyping_target
            FROM labeling_rule_set
            WHERE display_name = ?
            """,
            ("ApoM Tg/Tg 2026-05-06",),
        ).fetchone()
        sequence = conn.execute(
            """
            SELECT ear_label_code
            FROM labeling_rule_ear_sequence
            WHERE rule_set_id = ?
            ORDER BY sequence_index
            """,
            ("label_rule_apom_tgtg_20260506",),
        ).fetchall()

    assert dict(rule) == {
        "display_name": "ApoM Tg/Tg 2026-05-06",
        "numbering_order": "male_first",
        "mouse_number_scope": "continues_across_cages_within_same_id",
        "ear_sequence_scope": "resets_per_cage",
        "crossed_out_handling": "dead",
        "sample_mapping": "sample_id_equals_mouse_display_id",
        "genotyping_target": "ApoM-tg",
    }
    assert [row["ear_label_code"] for row in sequence[:6]] == [
        "R_PRIME",
        "L_PRIME",
        "R_PRIME_L_PRIME",
        "R_CIRCLE",
        "L_CIRCLE",
        "R_CIRCLE_L_CIRCLE",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_labeling_session_rules.py::test_labeling_rule_schema_seeds_default_apom_rule -v`

Expected: FAIL because `labeling_rule_set` does not exist.

- [ ] **Step 3: Add schema and seed constants**

In `app/db.py`, add seed constants near `EAR_LABEL_MASTER_SEEDS`:

```python
LABELING_RULE_SET_SEEDS = [
    (
        "label_rule_apom_tgtg_20260506",
        "ApoM Tg/Tg 2026-05-06",
        "ApoM Tg/Tg",
        "2026-05-06",
        "male_first",
        "continues_across_cages_within_same_id",
        "resets_per_cage",
        "dead",
        "sample_id_equals_mouse_display_id",
        "ApoM-tg",
        1,
    ),
]

LABELING_RULE_EAR_SEQUENCE_SEEDS = [
    ("label_rule_apom_tgtg_20260506", 1, "R_PRIME"),
    ("label_rule_apom_tgtg_20260506", 2, "L_PRIME"),
    ("label_rule_apom_tgtg_20260506", 3, "R_PRIME_L_PRIME"),
    ("label_rule_apom_tgtg_20260506", 4, "R_CIRCLE"),
    ("label_rule_apom_tgtg_20260506", 5, "L_CIRCLE"),
    ("label_rule_apom_tgtg_20260506", 6, "R_CIRCLE_L_CIRCLE"),
    ("label_rule_apom_tgtg_20260506", 7, "R_PRIME_L_CIRCLE"),
    ("label_rule_apom_tgtg_20260506", 8, "R_CIRCLE_L_PRIME"),
    ("label_rule_apom_tgtg_20260506", 9, "R_DOUBLE_CIRCLE"),
    ("label_rule_apom_tgtg_20260506", 10, "L_DOUBLE_CIRCLE"),
    ("label_rule_apom_tgtg_20260506", 11, "R_DOUBLE_CIRCLE_L_DOUBLE_CIRCLE"),
    ("label_rule_apom_tgtg_20260506", 12, "R_PRIME_L_DOUBLE_CIRCLE"),
    ("label_rule_apom_tgtg_20260506", 13, "R_DOUBLE_CIRCLE_L_PRIME"),
]
```

Also add missing ear-label master rows for double-circle codes.

- [ ] **Step 4: Add tables and insert seeds**

In `init_db()`, create:

```sql
CREATE TABLE IF NOT EXISTS labeling_rule_set (
    rule_set_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL UNIQUE,
    applies_to_strain_text TEXT NOT NULL DEFAULT '',
    session_date TEXT NOT NULL DEFAULT '',
    numbering_order TEXT NOT NULL DEFAULT 'unknown',
    mouse_number_scope TEXT NOT NULL DEFAULT 'unknown',
    ear_sequence_scope TEXT NOT NULL DEFAULT 'unknown',
    crossed_out_handling TEXT NOT NULL DEFAULT 'review',
    sample_mapping TEXT NOT NULL DEFAULT 'review',
    genotyping_target TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS labeling_rule_ear_sequence (
    rule_set_id TEXT NOT NULL,
    sequence_index INTEGER NOT NULL,
    ear_label_code TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (rule_set_id, sequence_index),
    FOREIGN KEY (rule_set_id) REFERENCES labeling_rule_set(rule_set_id),
    FOREIGN KEY (ear_label_code) REFERENCES ear_label_master(ear_label_code)
);
```

Insert the seed rows with `INSERT OR IGNORE`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_labeling_session_rules.py::test_labeling_rule_schema_seeds_default_apom_rule -v`

Expected: PASS.

### Task 2: Pure Rule Application

**Files:**
- Create: `app/labeling_rules.py`
- Test: `tests/test_labeling_session_rules.py`

- [ ] **Step 1: Write failing sequence and death tests**

```python
from app.labeling_rules import apply_ear_sequence, interpret_crossed_out_status


def test_ear_sequence_resets_for_each_cage_group():
    sequence = ["R_PRIME", "L_PRIME", "R_PRIME_L_PRIME"]
    note_groups = [
        [{"mouse": "1"}, {"mouse": "2"}],
        [{"mouse": "3"}, {"mouse": "4"}],
    ]

    result = apply_ear_sequence(note_groups, sequence)

    assert result[0][0]["expected_ear_label_code"] == "R_PRIME"
    assert result[0][1]["expected_ear_label_code"] == "L_PRIME"
    assert result[1][0]["expected_ear_label_code"] == "R_PRIME"
    assert result[1][1]["expected_ear_label_code"] == "L_PRIME"


def test_crossed_out_mouse_line_interprets_as_dead_under_rule():
    assert interpret_crossed_out_status("double", "dead") == "dead"
    assert interpret_crossed_out_status("single", "dead") == "dead"
    assert interpret_crossed_out_status("none", "dead") == "active"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_labeling_session_rules.py::test_ear_sequence_resets_for_each_cage_group tests/test_labeling_session_rules.py::test_crossed_out_mouse_line_interprets_as_dead_under_rule -v`

Expected: FAIL because `app.labeling_rules` does not exist.

- [ ] **Step 3: Implement pure functions**

Create `app/labeling_rules.py`:

```python
from __future__ import annotations

from copy import deepcopy
from typing import Any


def apply_ear_sequence(
    note_groups: list[list[dict[str, Any]]],
    sequence: list[str],
) -> list[list[dict[str, Any]]]:
    result: list[list[dict[str, Any]]] = []
    for group in note_groups:
        rewritten_group: list[dict[str, Any]] = []
        active_index = 0
        for note in group:
            rewritten = deepcopy(note)
            if str(note.get("interpreted_status") or "active") == "dead":
                rewritten["expected_ear_label_code"] = None
            else:
                rewritten["expected_ear_label_code"] = (
                    sequence[active_index] if active_index < len(sequence) else None
                )
                active_index += 1
            rewritten_group.append(rewritten)
        result.append(rewritten_group)
    return result


def interpret_crossed_out_status(strike_status: str, crossed_out_handling: str) -> str:
    normalized_strike = (strike_status or "none").strip().lower()
    normalized_rule = (crossed_out_handling or "review").strip().lower()
    if normalized_rule == "dead" and normalized_strike in {"single", "double"}:
        return "dead"
    if normalized_strike == "none":
        return "active"
    return "review"
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_labeling_session_rules.py -v`

Expected: PASS for the new pure-function tests and the schema test.

### Task 3: Sample Matching

**Files:**
- Modify: `app/labeling_rules.py`
- Test: `tests/test_labeling_session_rules.py`

- [ ] **Step 1: Write failing sample matching tests**

```python
from app.labeling_rules import match_samples_to_mice


def test_sample_id_matches_mouse_display_id():
    mice = [{"mouse_id": "mouse_24", "display_id": "24"}]
    samples = [{"sample_id": "24", "target_name": "ApoM-tg"}]

    [match] = match_samples_to_mice(samples, mice)

    assert match["match_status"] == "matched"
    assert match["mouse_id"] == "mouse_24"


def test_duplicate_sample_match_requires_review():
    mice = [
        {"mouse_id": "mouse_a", "display_id": "24"},
        {"mouse_id": "mouse_b", "display_id": "24"},
    ]
    samples = [{"sample_id": "24", "target_name": "ApoM-tg"}]

    [match] = match_samples_to_mice(samples, mice)

    assert match["match_status"] == "duplicate_mouse_match"
    assert match["mouse_id"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_labeling_session_rules.py::test_sample_id_matches_mouse_display_id tests/test_labeling_session_rules.py::test_duplicate_sample_match_requires_review -v`

Expected: FAIL because `match_samples_to_mice` does not exist.

- [ ] **Step 3: Implement sample matching**

Add to `app/labeling_rules.py`:

```python
def match_samples_to_mice(
    samples: list[dict[str, Any]],
    mice: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_display: dict[str, list[dict[str, Any]]] = {}
    for mouse in mice:
        display_id = str(mouse.get("display_id") or "").strip()
        if display_id:
            by_display.setdefault(display_id, []).append(mouse)

    results: list[dict[str, Any]] = []
    for sample in samples:
        rewritten = deepcopy(sample)
        sample_id = str(sample.get("sample_id") or "").strip()
        candidates = by_display.get(sample_id, [])
        if len(candidates) == 1:
            rewritten["match_status"] = "matched"
            rewritten["mouse_id"] = candidates[0].get("mouse_id")
        elif len(candidates) > 1:
            rewritten["match_status"] = "duplicate_mouse_match"
            rewritten["mouse_id"] = None
        else:
            rewritten["match_status"] = "unmatched"
            rewritten["mouse_id"] = None
        results.append(rewritten)
    return results
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_labeling_session_rules.py -v`

Expected: PASS.

### Task 4: Integrate With Existing Note Item Writes

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_labeling_session_rules.py`

- [ ] **Step 1: Write integration test around existing writer**

Use `write_note_items_and_mouse_candidates()` with two cage/card groups and assert that expected labels are recorded in metadata without changing raw line text.

Expected stored metadata key:

```json
{
  "expected_ear_label_code": "R_PRIME",
  "labeling_rule_set_id": "label_rule_apom_tgtg_20260506"
}
```

- [ ] **Step 2: Run the integration test**

Run: `pytest tests/test_labeling_session_rules.py::test_writer_stores_expected_ear_label_metadata_without_overwriting_raw_note -v`

Expected: FAIL because existing writer does not store rule metadata.

- [ ] **Step 3: Add minimal optional rule-set parameter**

Extend the writer path with an optional `labeling_rule_set_id` parameter. Load the sequence from SQLite, call `apply_ear_sequence()`, and merge only expected-code metadata into `parsed_metadata_json`. Do not overwrite `raw_line_text`, `parsed_ear_label_raw`, or user-corrected values.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_labeling_session_rules.py tests/test_review_attention.py -v`

Expected: PASS. Existing ear-label review tests must keep passing.

### Task 5: Integrate With Genotyping Records

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_labeling_session_rules.py`

- [ ] **Step 1: Write integration test for exact sample matching**

Create a mouse with `display_id = "24"`, submit sample `"24"`, and assert the genotyping record links to that mouse and target `ApoM-tg`.

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_labeling_session_rules.py::test_genotyping_submission_uses_rule_set_sample_id_match -v`

Expected: FAIL until the rule-set target/default matching is wired.

- [ ] **Step 3: Apply default target and match status**

When the selected rule set has `sample_mapping = sample_id_equals_mouse_display_id`, use exact display ID matching before falling back to existing behavior. If no unique mouse match exists, create or return a reviewable status instead of silently attaching the sample.

- [ ] **Step 4: Run genotyping and review tests**

Run: `pytest tests/test_labeling_session_rules.py tests/test_review_attention.py -v`

Expected: PASS.

### Task 6: Documentation And Verification

**Files:**
- Modify: `final_mouse_colony_prd.md`
- Modify: `mvp_vertical_slice_plan.md`

- [ ] **Step 1: Add PRD note**

Add a short section describing labeling session rule sets as configurable parsing policy, with explicit data boundaries.

- [ ] **Step 2: Add vertical-slice acceptance checks**

Add acceptance checks for ear-label sequence reset, mouse number continuity, crossed-out dead handling, and sample-to-mouse genotyping matching.

- [ ] **Step 3: Run verification**

Run:

```powershell
pytest tests/test_labeling_session_rules.py tests/test_review_attention.py -v
git status --short
```

Expected: tests pass; changed files are limited to the task source/docs.

---

## Self-Review Checklist

- Every raw value remains preserved.
- Crossed-out handling is configurable but defaults to dead only for the selected rule set.
- ApoM Tg/Tg and ApoM-tg are seed data, not hard-coded branches in parser logic.
- Existing ear-label review behavior remains bounded and reviewable.
- Genotyping sample matching never silently overwrites conflicting confirmed results.
