# Current State, Design Alignment, and Next Direction Review

Layer classification: review item / non-canonical project documentation.

Canonical status: non-canonical. This document summarizes project state as of 2026-05-09 and does not define database truth. Canonical state remains in source-backed tables, accepted project documents, tests, and committed implementation.

## Snapshot

- Date: 2026-05-09
- Branch: `codex/artifact-workflow-contracts`
- Latest observed commit: `ba6a927 feat: extend artifact evidence provenance`
- Worktree state after status refresh: clean, branch reported as ahead by 1 commit
- Targeted verification passed:
  - `python -m pytest tests/test_artifact_workflow.py tests/test_photo_evidence_ledger_schema.py tests/test_genotyping_evidence_enforcement.py -q`
  - Result: 12 passed, 78 FastAPI deprecation warnings
- Full verification currently fails:
  - Command: `npm run verify`
  - Passing before failure: `npm test`, `npm run test:acceptance`
  - Failing step: `npm run test:local`
  - Failure: `scripts/verify-local-app.py` posts `/api/genotyping/update` without `source_photo_id`, `photo_evidence_id`, or `source_record_id`.
  - Likely root cause: recent evidence enforcement correctly blocks genotype result confirmation without source evidence, while the local app verification script still uses the older evidence-free fixture update path.

## Original Design Intent

The original mouse colony concept was a Mouse Strain Knowledge Graph plus Colony Tracking System:

- `Strain` is the genetic line or design layer.
- `Mouse` is the real animal instance.
- `Event` is durable history.
- `Visualization` explains relationships and workflow state.

The guiding principle was:

> Strain is detailed, Mouse is lightweight, Event is extensible, Visualization is a map.

## Current Product Direction

The implementation has shifted into a more evidence-first MVP:

- handwritten cage-card photos and related records are preserved as raw evidence;
- Excel files are import/export views, not the source of truth;
- raw extracted values and normalized values are kept separate;
- review/correction paths gate risky canonical writes;
- cage/card records are treated as snapshots;
- durable history is represented through events, actions, corrections, and artifact provenance.

This direction is compatible with the original design, but it changes the immediate priority. The first usable product is no longer a clean Strain Registry first. It is a photo, review, correction, canonical-apply, and export workflow that protects the lab's existing handwritten cage-card practice.

## Alignment With The Design

Strongly aligned areas:

- `Strain` and `Mouse` are conceptually separated, even though the web app still has more workflow weight around `mouse_master` and raw strain text than around normalized gene/allele tables.
- `Mouse` remains relatively lightweight; detailed lifecycle changes are captured through `mouse_event`, `action_log`, correction logs, review items, and artifact records.
- `Event` as durable history is well aligned with the product principle that cage cards are snapshots and history should be event-like.
- Review-first processing is consistent with wet-lab reality: OCR, handwritten notes, and Excel rows are not reliable enough to write directly into canonical state.
- Recent artifact work strengthens traceability:
  - proposed changeset artifacts are export/view records, not canonical state;
  - validation report artifacts preserve blocker checks and source references;
  - export manifest artifacts preserve export provenance, validation report links, state watermark, and source references;
  - review evidence links connect review decisions back to photo evidence items.
- Genotype result enforcement is directionally correct: confirmed genotype state should not change without source evidence.

## Mismatches And Gaps

Important mismatches against the broader design:

- `Gene`, `Allele`, and `StrainAllele` are not yet a mature canonical knowledge graph surface in the app workflow.
- Experiment traceability is still thin compared with the original `Experiment` and `ExperimentMouse` design.
- Visualization remains secondary. Network graph, pedigree tree, radar chart, heatmap, and Sankey-style breeding flow are not yet the practical center of the product.
- Controlled vocabulary is only partly centralized. Some statuses, workflow rules, and genotype categories are improved, but the system still needs a stronger configurable master layer.
- The current local app E2E script has a stale assumption: it attempts genotype result confirmation without evidence.
- `mvp_acceptance_matrix_ko.md` appears mojibake-encoded in the current checkout. The verifier still passes structurally, but humans cannot reliably review the Korean content.

## Current Data Layer Classification

| Item | Layer | Notes |
| --- | --- | --- |
| Uploaded cage-card photo | raw source | Preserve original photo even when quality is poor. |
| Excel import row | raw source or parsed input view | Useful source record, but not canonical truth by itself. |
| Manual/AI transcription | parsed or intermediate result | Should keep confidence and raw text. |
| `photo_evidence_item` | parsed/intermediate evidence ledger | Links source photo, parsed fields, note lines, ROI labels, and reviewability. |
| `review_evidence_link` | review traceability link | Connects review item to photo evidence items. |
| `mouse_master` | canonical structured state | Must change only through accepted evidence-backed paths. |
| `mouse_event` | canonical structured history | Durable state transition record. |
| proposed changeset artifact | export or view | Non-canonical preview of possible writes. |
| validation report artifact | export or view | Non-canonical pass/block report for apply/export readiness. |
| export manifest artifact | export or view | Non-canonical provenance wrapper for generated exports. |
| ROI/crop preview | cache | Derived review aid only; raw photo remains source. |
| this document | review item | Project state summary, not product truth. |

## Wet-Lab Workflow Reading

Given the user's clarification that data entry will not happen inside the animal room, the realistic workflow should be:

1. Animal room work continues on handwritten cage cards.
2. Photos are taken after work or during a controlled handoff.
3. A reviewer uploads photos and/or imports Excel outside the animal room.
4. The system extracts or receives transcription as parsed evidence.
5. Low-confidence, conflicting, or biologically unlikely records go to review.
6. The user corrects or accepts review items.
7. Only accepted candidates write to canonical mouse, cage, mating, litter, genotype, or event state.
8. Exports are generated as views with a manifest, validation report, and source references.

This keeps the initial product from disrupting the animal room while still building a reliable digital record.

## High-Risk Areas To Guard

- Do not infer death, sacrifice, parent replacement, cage closure, or genotype confirmation without evidence and review.
- Do not let Excel overwrite photo-backed or review-backed state silently.
- Do not globally encode ApoM-specific genotype or labeling rules as general colony biology.
- Do not hide uncertain OCR states behind clean-looking normalized values.
- Do not export final files without blocker context, validation status, and manifest provenance.

## Recommended Next Direction

The next step should be a stabilization slice, not a new domain feature:

1. Fix the stale local verification script so genotype result updates include explicit source evidence.
2. Re-run full verification.
3. Keep the artifact/evidence/export manifest branch clean and coherent.
4. Repair or rewrite the mojibake Korean acceptance matrix.
5. Add acceptance rows for photo evidence ledger, genotype evidence enforcement, validation reports, and export manifests.

After that, the next product choice should be one of:

- evidence artifact visibility in the UI, if the priority is operational trust;
- Gene/Allele/StrainAllele normalization, if the priority is the original strain knowledge graph;
- ExperimentMouse traceability, if the priority is publication and data provenance;
- visualization, only after the canonical/evidence layer is stable enough to support it.

Recommendation: finish evidence artifact visibility first. It is the smallest step that directly supports the lab workflow and makes later knowledge-graph features safer.
