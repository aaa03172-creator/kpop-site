# Cage Card Skill Gym Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the non-canonical cage-card skill gym from 10 probes to 20 probes covering documented pilot-readiness, evidence-enforcement, privacy, and assistant-summary safety cases.

**Architecture:** Keep the harness offline under `evals/cage_card_skill_gym/`. Add fixture probes only; do not change runtime behavior, database schema, API contracts, or `AGENTS.md`. Tests assert the expanded probe pack contains the expected second-batch scenarios and still passes the deterministic baseline runner.

**Tech Stack:** Python standard library, pytest, JSON-compatible YAML probe fixtures.

---

### Task 1: Expanded Probe-Pack Coverage Tests

**Files:**
- Modify: `tests/test_cage_card_skill_gym.py`

- [ ] **Step 1: Write failing tests**

Add tests that load committed probe files from `evals/cage_card_skill_gym/probes` and assert:

```python
def test_committed_probe_pack_contains_second_batch_safety_cases() -> None:
    probes_dir = Path("evals/cage_card_skill_gym/probes")
    probe_ids = {
        json.loads(path.read_text(encoding="utf-8"))["probe_id"]
        for path in probes_dir.glob("*.yaml")
    }

    assert len(probe_ids) >= 20
    assert {
        "batch_upload_partial_failure_preserves_unrelated_photos",
        "real_photo_manifest_requires_private_safe_coverage",
        "pilot_export_blocking_mix_requires_control_cases",
        "backup_restore_evidence_uses_labels_not_paths",
        "genotype_result_requires_source_evidence",
        "high_risk_mouse_event_requires_source_evidence",
        "blocked_export_keeps_manifest_without_workbook",
        "public_pilot_log_redacts_private_payloads",
        "assistant_summary_keeps_review_blockers_visible",
        "rule_masters_prevent_hard_coded_domain_logic",
    }.issubset(probe_ids)
```

Add a second test that runs `build_report(probes_dir)` and expects all committed probes to pass with total count at least 20.

- [ ] **Step 2: Verify red**

Run:

```powershell
python -m pytest tests/test_cage_card_skill_gym.py -q
```

Expected: the new coverage test fails because the second-batch probe IDs do not exist yet.

### Task 2: Second-Batch Probe Fixtures

**Files:**
- Create: `evals/cage_card_skill_gym/probes/11_batch_upload_partial_failure.yaml`
- Create: `evals/cage_card_skill_gym/probes/12_real_photo_manifest_private_safe_coverage.yaml`
- Create: `evals/cage_card_skill_gym/probes/13_pilot_export_blocking_mix.yaml`
- Create: `evals/cage_card_skill_gym/probes/14_backup_restore_evidence_labels.yaml`
- Create: `evals/cage_card_skill_gym/probes/15_genotype_result_source_evidence.yaml`
- Create: `evals/cage_card_skill_gym/probes/16_high_risk_mouse_event_source_evidence.yaml`
- Create: `evals/cage_card_skill_gym/probes/17_blocked_export_manifest_no_workbook.yaml`
- Create: `evals/cage_card_skill_gym/probes/18_public_pilot_log_redaction.yaml`
- Create: `evals/cage_card_skill_gym/probes/19_assistant_summary_review_blockers.yaml`
- Create: `evals/cage_card_skill_gym/probes/20_rule_masters_no_hard_coding.yaml`
- Modify: `evals/cage_card_skill_gym/README.md`

- [ ] **Step 1: Add JSON-compatible YAML probes**

Each new probe must include:

```json
{
  "probe_id": "<stable_id>",
  "taxonomy": "<existing_or_new_taxonomy>",
  "boundary": "review item / test fixture",
  "canonical": false,
  "scenario": "<MouseDB safety scenario>",
  "expected": {
    "boundary": "<known project data boundary>",
    "must_route_to_review": true,
    "must_preserve_traceability": true,
    "must_not_write_canonical": true,
    "external_inference_policy": "local_only"
  }
}
```

Use `local_or_approved_only` only for cases that involve optional AI/OCR extraction. Use `local_only` for manifest, backup, export, assistant summary, and configurable-rule probes.

- [ ] **Step 2: Update README**

Update `evals/cage_card_skill_gym/README.md` to state the harness now has 20 seed probes and list the second-batch coverage areas without promoting them to canonical product behavior.

- [ ] **Step 3: Verify green**

Run:

```powershell
python -m pytest tests/test_cage_card_skill_gym.py -q
npm run test:cage-card-skill-gym
```

Expected: pytest passes and the baseline runner reports 20 passed, 0 failed.

### Task 3: Completion Checks

**Files:**
- Inspect all changed task files.

- [ ] **Step 1: Check formatting and parseability**

Run:

```powershell
python -m json.tool evals/cage_card_skill_gym/rubric.schema.json
```

Expected: schema parses successfully.

- [ ] **Step 2: Re-check worktree**

Run:

```powershell
git status --short
```

Expected: task changes are limited to the plan doc, probe fixtures, README, and test file. If unrelated line-ending-only changes remain, leave them unstaged and call them out.
