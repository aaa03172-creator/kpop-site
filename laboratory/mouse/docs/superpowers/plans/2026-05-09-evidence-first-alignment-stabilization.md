# Evidence-First Alignment Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the evidence-first Mouse Colony workflow so local verification, documentation, artifact provenance, and acceptance criteria match the adopted design.

**Architecture:** Keep raw source, parsed evidence, review items, canonical state, export/view artifacts, and cache artifacts separate. Fix stale verification fixtures before adding new behavior, then update human-readable documentation and acceptance criteria to match evidence-backed genotype and export flows.

**Tech Stack:** FastAPI, SQLite, static HTML/CSS/JavaScript, pytest, Node verification scripts, Markdown documentation.

---

## File Structure

- Modify: `scripts/verify-local-app.py`
  - Responsibility: browserless local workflow verification. It should seed or reference evidence before confirming genotype results.
- Modify: `mvp_acceptance_matrix_ko.md`
  - Responsibility: human-readable MVP acceptance matrix. It must be valid UTF-8 Korean and match current tests.
- Modify: `scripts/verify-acceptance-matrix.py`
  - Responsibility: structural acceptance matrix verification. Update only if new acceptance IDs are added.
- Modify: `tests/test_genotyping_evidence_enforcement.py`
  - Responsibility: focused unit tests for genotype result evidence requirements.
- Modify: `tests/test_artifact_workflow.py`
  - Responsibility: focused tests for proposed changeset, validation report, and export manifest artifacts.
- Modify: `tests/test_photo_evidence_ledger_schema.py`
  - Responsibility: focused tests for photo evidence ledger and review evidence links.
- Optionally modify: `static/index.html`
  - Responsibility: UI visibility for validation and export provenance after the verification stabilization passes.

## Task 1: Confirm The Local Verification Failure

**Files:**
- Read: `scripts/verify-local-app.py`
- Read: `app/main.py`
- Read: `tests/test_genotyping_evidence_enforcement.py`

- [ ] **Step 1: Run the failing command**

Run:

```powershell
npm run test:local
```

Expected: FAIL at `Could not update genotyping workflow state.`

- [ ] **Step 2: Inspect the stale request payload**

Check `scripts/verify-local-app.py` around the `/api/genotyping/update` call. The stale payload currently has this shape:

```python
genotyping_update = client.post(
    "/api/genotyping/update",
    json={
        "mouse_id": genotyping_target["mouse_id"],
        "sample_id": "MT321",
        "raw_result": "Tg/Tg",
        "normalized_result": "Tg/Tg",
    },
)
```

Expected finding: the payload confirms a genotype result but does not provide `source_photo_id`, `photo_evidence_id`, or `source_record_id`.

- [ ] **Step 3: Confirm the app-side enforcement**

Read `app/main.py` in `genotyping_result_evidence_refs`. The behavior to preserve is:

```python
if not any([source_record_id, source_photo_id, photo_evidence_id]):
    raise HTTPException(
        status_code=409,
        detail=(
            "Genotype result confirmation requires evidence: provide source_photo_id, "
            "photo_evidence_id, or source_record_id."
        ),
    )
```

Expected: this enforcement is correct and should not be weakened.

## Task 2: Fix The Local Verification Fixture To Use Evidence

**Files:**
- Modify: `scripts/verify-local-app.py`

- [ ] **Step 1: Find an existing source photo for MT321**

In the script, use the photo or source evidence already created for the MT321 note/card flow. Prefer a real seeded photo ID over an invented fixture ID. A safe patch shape is:

```python
                genotyping_source_photo_id = genotyping_target.get("source_photo_id") or mt321_export_row.get("source_photo_id")
```

If `mt321_export_row` stores compacted `source_photo_ids`, split the first non-empty value before use:

```python
                genotyping_source_photo_id = (
                    genotyping_target.get("source_photo_id")
                    or mt321_export_row.get("source_photo_id")
                    or str(mt321_export_row.get("source_photo_ids") or "").split(";")[0].strip()
                )
```

- [ ] **Step 2: Add a guard assertion before the update**

Add this before the POST:

```python
                assert_true(
                    bool(genotyping_source_photo_id),
                    "Genotyping result verification should use source photo evidence.",
                )
```

- [ ] **Step 3: Include the source evidence in the POST**

Change the request to:

```python
                genotyping_update = client.post(
                    "/api/genotyping/update",
                    json={
                        "mouse_id": genotyping_target["mouse_id"],
                        "sample_id": "MT321",
                        "raw_result": "Tg/Tg",
                        "normalized_result": "Tg/Tg",
                        "source_photo_id": genotyping_source_photo_id,
                    },
                )
```

- [ ] **Step 4: Run the local verification**

Run:

```powershell
npm run test:local
```

Expected: PASS, or the next failure should be unrelated to genotype evidence enforcement and should be investigated separately before changing code.

## Task 3: Protect The Behavior With Focused Tests

**Files:**
- Modify: `tests/test_genotyping_evidence_enforcement.py`

- [ ] **Step 1: Verify the existing negative test remains**

Keep this assertion:

```python
assert exc_info.value.status_code == 409
assert "evidence" in str(exc_info.value.detail).lower()
```

- [ ] **Step 2: Verify the positive test records evidence**

Keep or add this assertion:

```python
assert record["source_photo_id"] == "photo_gt_evidence"
assert event["event_type"] == "genotyped"
assert "photo_gt_evidence" in event["details"]
```

- [ ] **Step 3: Run the focused test**

Run:

```powershell
python -m pytest tests/test_genotyping_evidence_enforcement.py -q
```

Expected: PASS.

## Task 4: Run Full Verification

**Files:**
- Verify: `package.json`
- Verify: `scripts/verify-local-app.py`
- Verify: Python tests under `tests/`

- [ ] **Step 1: Run full verification**

Run:

```powershell
npm run verify
```

Expected: PASS through all stages:

```text
npm test
npm run test:acceptance
npm run test:local
npm run test:photo-e2e
npm run test:cage-card-skill-gym
npm run test:python
```

- [ ] **Step 2: Re-check worktree status**

Run:

```powershell
git status --short --branch --untracked-files=all
```

Expected: only intentional source/doc/test files are modified.

## Task 5: Repair The Korean Acceptance Matrix

**Files:**
- Modify: `mvp_acceptance_matrix_ko.md`
- Modify if needed: `scripts/verify-acceptance-matrix.py`

- [ ] **Step 1: Replace mojibake with valid UTF-8 Korean**

Rewrite the opening sections so they are human-readable and preserve these requirements:

```markdown
# Mouse Colony MVP Acceptance Matrix

Layer classification: implementation verification / non-canonical project note.

이 문서는 현재 MVP가 cage-card 기반 colony tracking의 핵심 흐름을 어느 정도 만족하는지 확인하기 위한 acceptance matrix이다. Canonical 제품 요구사항은 `final_mouse_colony_prd.md`와 `AGENTS.md`를 따른다.
```

- [ ] **Step 2: Add acceptance criteria for recent evidence work**

Append rows after the current safety eval row:

```markdown
| A22 | Photo Evidence Ledger | photo/card/note evidence item이 source photo, raw observed text, confidence, reviewability, linked mouse/event trace를 보존한다. | Done | `tests/test_photo_evidence_ledger_schema.py` |
| A23 | Genotype Evidence Enforcement | genotype result confirmation은 source photo, photo evidence item, 또는 source record 없이 canonical genotype state를 갱신하지 않는다. | Done | `tests/test_genotyping_evidence_enforcement.py` |
| A24 | Validation Report Artifact | canonical apply/export 전 validation report artifact가 pass/block 상태와 source refs를 남긴다. | Done | `tests/test_artifact_workflow.py` |
| A25 | Export Manifest Artifact | CSV/XLSX export는 manifest artifact로 validation report, source refs, state watermark, filename을 추적한다. | Done | `tests/test_artifact_workflow.py` |
```

- [ ] **Step 3: Run acceptance matrix verification**

Run:

```powershell
python scripts/verify-acceptance-matrix.py
```

Expected: `Acceptance matrix verification passed.`

## Task 6: Add UI Visibility For Export Provenance

**Files:**
- Modify: `static/index.html`
- Modify: `scripts/verify-local-app.py`

- [ ] **Step 1: Add export provenance text to the existing export preview area**

Render validation and manifest status using existing API response fields. If the API does not expose manifest details yet, keep this task scoped to validation/export readiness already present in the response and create a separate API plan after verification.

Use wording that matches lab workflow:

```javascript
const provenanceBits = [
  preview.export_ready ? 'Export ready' : 'Review needed before export',
  preview.export_stale ? 'Data changed after last export' : '',
].filter(Boolean);
```

- [ ] **Step 2: Add local verifier assertions**

In `scripts/verify-local-app.py`, assert that the export preview shows blocker/readiness text after review blockers exist and ready text after blockers are resolved:

```python
assert_true("Review needed before export" in index_html or export_preview["export_ready"] is False, "Export preview should expose review-needed state.")
```

If the UI is rendered dynamically and not visible in static HTML, use API assertions instead of a brittle string check.

- [ ] **Step 3: Run local verification**

Run:

```powershell
npm run test:local
```

Expected: PASS.

## Task 7: Commit The Stabilization Slice

**Files:**
- Stage exact changed files only.

- [ ] **Step 1: Inspect status**

Run:

```powershell
git status --short --branch --untracked-files=all
```

Expected: modified files are limited to the current task.

- [ ] **Step 2: Stage exact files**

Run:

```powershell
git add scripts/verify-local-app.py tests/test_genotyping_evidence_enforcement.py mvp_acceptance_matrix_ko.md scripts/verify-acceptance-matrix.py static/index.html
```

If `scripts/verify-acceptance-matrix.py` or `static/index.html` did not change, omit them from the command.

- [ ] **Step 3: Commit**

Run:

```powershell
git commit -m "test: align verification with evidence-backed genotype updates"
```

Expected: commit succeeds and `git status --short --branch --untracked-files=all` is clean afterward.

## Self-Review

- Spec coverage: covers current verification failure, evidence enforcement, acceptance matrix repair, full verification, and the smallest UI provenance follow-up.
- Placeholder scan: no `TBD`, no open-ended "handle later" steps.
- Type consistency: uses existing fields `source_photo_id`, `photo_evidence_id`, `source_record_id`, and existing commands from the repository.
- Risk note: do not weaken genotype evidence enforcement to make the script pass. The script fixture should carry evidence because the product principle is evidence-backed canonical state.
