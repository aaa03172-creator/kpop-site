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

- [x] **Step 1: Run the failing command**

Run:

```powershell
npm run test:local
```

Observed before the verifier fix: FAIL at `Could not update genotyping workflow state.`

- [x] **Step 2: Inspect the stale request payload**

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

- [x] **Step 3: Confirm the app-side enforcement**

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

- [x] **Step 1: Find existing evidence for MT321**

In the script, use source evidence already created for the MT321 note/card flow. Prefer a real source record or source photo over an invented fixture ID. The working-tree patch uses the existing audit trace source record:

```python
                genotyping_evidence_record_id = genotyping_target.get("source_record_id") or (
                    audit_payload["source_records"][0]["source_record_id"] if audit_payload["source_records"] else ""
                )
```

- [x] **Step 2: Add a guard assertion before the update**

Add this before the POST:

```python
                assert_true(
                    bool(genotyping_evidence_record_id),
                    "Genotyping result verification needs source evidence for the target mouse.",
                )
```

- [x] **Step 3: Include the source evidence in the POST**

Change the request to:

```python
                genotyping_update = client.post(
                    "/api/genotyping/update",
                    json={
                        "mouse_id": genotyping_target["mouse_id"],
                        "sample_id": "MT321",
                        "raw_result": "Tg/Tg",
                        "normalized_result": "Tg/Tg",
                        "source_record_id": genotyping_evidence_record_id,
                    },
                )
```

- [x] **Step 4: Run the local verification**

Run:

```powershell
npm run test:local
```

Observed: PASS.

## Task 3: Protect The Behavior With Focused Tests

**Files:**
- Modify: `tests/test_genotyping_evidence_enforcement.py`

- [x] **Step 1: Verify the existing negative test remains**

Keep this assertion:

```python
assert exc_info.value.status_code == 409
assert "evidence" in str(exc_info.value.detail).lower()
```

- [x] **Step 2: Verify the positive test records evidence**

Keep or add this assertion:

```python
assert record["source_photo_id"] == "photo_gt_evidence"
assert event["event_type"] == "genotyped"
assert "photo_gt_evidence" in event["details"]
```

- [x] **Step 3: Run the focused test**

Run:

```powershell
python -m pytest tests/test_genotyping_evidence_enforcement.py -q
```

Observed: PASS as part of the focused evidence tests.

## Task 3A: Protect High-Risk Mouse Events With Evidence

**Files:**
- Create or keep: `tests/test_mouse_event_evidence_enforcement.py`
- Verify: `app/main.py`

- [x] **Step 1: Add a negative test for evidence-free high-risk events**

The test should call `create_mouse_event` with a high-risk event such as `death` and no evidence:

```python
with pytest.raises(HTTPException) as exc_info:
    create_mouse_event(
        MouseEventCreate(
            mouse_id="mouse_event_evidence",
            event_type="death",
            event_date="2026-05-09",
            details={"observed_status": "found dead"},
        )
    )

assert exc_info.value.status_code == 409
assert "evidence" in str(exc_info.value.detail).lower()
```

- [x] **Step 2: Keep positive tests for source record and photo evidence**

The evidence-backed source record path should assert:

```python
assert row["event_type"] == "death"
assert row["source_record_id"] == source_record_id
```

The photo evidence path should assert:

```python
assert details["source_photo_id"] == "photo_event_evidence"
assert details["photo_evidence_id"] == "evidence_death_note"
```

- [x] **Step 3: Run the focused mouse event evidence test**

Run:

```powershell
python -m pytest tests/test_mouse_event_evidence_enforcement.py -q
```

Observed: 3 passed.

## Task 4: Run Full Verification

**Files:**
- Verify: `package.json`
- Verify: `scripts/verify-local-app.py`
- Verify: Python tests under `tests/`

- [x] **Step 1: Run full verification**

Run:

```powershell
npm run verify
```

Observed: PASS through all stages:

```text
npm test
npm run test:acceptance
npm run test:local
npm run test:photo-e2e
npm run test:cage-card-skill-gym
npm run test:python
```

- [x] **Step 2: Re-check worktree status**

Run:

```powershell
git status --short --branch --untracked-files=all
```

Observed after related implementation commits: only the current-state review document and this plan document remain modified.

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
| A24 | High-Risk Mouse Event Evidence | death, sacrificed, moved, weaned 같은 high-risk mouse event는 source evidence 없이 canonical event를 생성하지 않는다. | Done | `tests/test_mouse_event_evidence_enforcement.py` |
| A25 | Validation Report Artifact | canonical apply/export 전 validation report artifact가 pass/block 상태와 source refs를 남긴다. | Done | `tests/test_artifact_workflow.py` |
| A26 | Export Manifest Artifact | CSV/XLSX export는 manifest artifact로 validation report, source refs, state watermark, filename을 추적한다. | Done | `tests/test_artifact_workflow.py` |
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

- [x] **Step 1: Add export provenance text to the existing export log area**

Render validation and manifest status using existing API response fields. The current working-tree patch adds structured provenance parsing to `/api/export-log` and displays manifest path, validation report ID, and state watermark in the export log table.

The backend parser shape is:

```python
def parse_export_log_provenance(note: str) -> dict[str, str]:
    provenance = {
        "export_manifest_path": "",
        "validation_report_id": "",
        "state_watermark": "",
    }
    ...
    return provenance
```

- [x] **Step 2: Add artifact test assertions**

The artifact test checks the structured export log response:

```python
assert row["export_manifest_path"] == "mousedb_artifacts/export_manifests/animal_sheet.json"
assert row["validation_report_id"] == "validation_report_export_animal_sheet_xlsx_ApoM"
assert row["state_watermark"] == "2026-05-09T12:05:00Z"
```

- [x] **Step 3: Run local verification**

Run:

```powershell
npm run test:local
```

Observed: PASS.

## Task 7: Commit The Stabilization Slice

**Files:**
- Stage exact changed files only.

- [ ] **Step 1: Inspect status**

Run:

```powershell
git status --short --branch --untracked-files=all
```

Expected: modified files are limited to the current documentation task unless the acceptance matrix repair is added next.

- [ ] **Step 2: Stage exact files**

Run:

```powershell
git add docs/superpowers/specs/2026-05-09-current-state-design-implementation-review.md docs/superpowers/plans/2026-05-09-evidence-first-alignment-stabilization.md
```

If the acceptance matrix is repaired in the same slice, also stage `mvp_acceptance_matrix_ko.md` and `scripts/verify-acceptance-matrix.py` if that script changed. If implementation files change again during review, stage them only after re-running `npm run verify`.

- [ ] **Step 3: Commit**

Run:

```powershell
git commit -m "test: align verification with evidence-backed genotype updates"
```

Expected: commit succeeds and `git status --short --branch --untracked-files=all` is clean afterward.

## Self-Review

- Spec coverage: covers current verification failure, evidence enforcement, acceptance matrix repair, full verification, and the smallest UI provenance follow-up.
- Placeholder scan: no unresolved placeholder steps remain.
- Type consistency: uses existing fields `source_photo_id`, `photo_evidence_id`, `source_record_id`, and existing commands from the repository.
- Risk note: do not weaken genotype evidence enforcement to make the script pass. The script fixture should carry evidence because the product principle is evidence-backed canonical state.
