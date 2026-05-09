# Cage Card Skill Gym Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tiny Ctx2Skill-lite evaluation harness for MouseDB cage-card workflow guidance without changing runtime behavior.

**Architecture:** The harness is an offline evaluator under `evals/cage_card_skill_gym/`. Probe YAML files describe review-safety scenarios, a deterministic Python runner applies binary rubric checks, and tests prove the runner catches regressions before any Skill or AGENTS guidance changes are proposed.

**Tech Stack:** Python standard library, pytest, YAML when available through the existing environment.

---

### Task 1: Deterministic Probe Runner

**Files:**
- Create: `evals/cage_card_skill_gym/README.md`
- Create: `evals/cage_card_skill_gym/run_baseline.py`
- Create: `evals/cage_card_skill_gym/rubric.schema.json`
- Create: `evals/cage_card_skill_gym/probes/*.yaml`
- Test: `tests/test_cage_card_skill_gym.py`
- Modify: `package.json`

- [ ] **Step 1: Write failing tests**

Create pytest tests that write temporary probes, call the runner, and assert that a good probe passes while a missing traceability expectation fails.

- [ ] **Step 2: Verify red**

Run `python -m pytest tests/test_cage_card_skill_gym.py -q`; expected failure because the runner does not exist.

- [ ] **Step 3: Implement minimal runner**

Implement YAML loading, deterministic pass/fail rubric checks, JSON summary output, and nonzero exit on failed probes.

- [ ] **Step 4: Add seed probes and docs**

Add 10 source/review/export probes adapted from current MouseDB principles. Mark them non-canonical fixtures.

- [ ] **Step 5: Verify green**

Run `python -m pytest tests/test_cage_card_skill_gym.py -q` and `python evals/cage_card_skill_gym/run_baseline.py --probes evals/cage_card_skill_gym/probes`.

- [ ] **Step 6: Re-check worktree**

Run `git status --short` and classify changes as task source or adopted documentation.
