# Ctx2Skill-lite Adoption Review For MouseDB

Layer classification: implementation planning / non-canonical project note.

Canonical: false. This document does not define product schema, runtime behavior, API contracts, database contracts, or final user workflow. It records why only a small evaluation-loop subset of Ctx2Skill is useful for this MouseDB repository.

## Executive Summary

Decision: **partial adoption**.

Do not import Ctx2Skill as a full framework. The useful part for this repository is not automatic Skill.md rewriting. The useful part is a small offline evaluation loop:

1. Challenger-style probe set
2. deterministic baseline runner
3. binary pass/fail judge
4. failure report
5. cross-time replay

This repository is MouseDB: a local-first, handwritten cage-card and Excel export workflow. It is not the PaperPipe/Lattice paper-reading workspace described in the original prompt. The correct fit is therefore `cage_card_skill_gym`, not `paper_skill_gym`.

## Repo Fit

Fits this repo:

- Data-boundary probes can enforce raw source, parsed/intermediate result, review item, canonical structured state, export/view, and cache separation.
- Regression probes can cover low-confidence OCR, impossible ear labels, duplicate active mice, ambiguous dates, legacy workbook conflicts, ROI cache behavior, and export blockers.
- The judge should be deterministic and binary before any LLM judge is considered.
- Failures should produce reports or candidate guidance patches, not runtime auto-edits.
- Cross-time replay helps avoid overfitting to hard probes while regressing easy review-safety cases.

Does not fit this repo:

- Adding Ctx2Skill multi-agent orchestration to product runtime.
- Automatically modifying `AGENTS.md` or a future project `Skill.md`.
- Changing DB, API, or runtime contracts because of the evaluation harness.
- Applying paper-reading probe categories to MouseDB before the repo has paper-reading modules.

## Existing Repo Evidence

Files inspected:

- `AGENTS.md`: raw photo preservation, raw/normalized separation, review routing, traceability, and external inference minimization.
- `README.md`: MouseDB is independent and should not hard-code PaperPipe integration.
- `final_mouse_colony_prd.md`: handwritten cage cards remain primary source; Excel is an output/view; review queue gates uncertainty.
- `mvp_vertical_slice_plan.md`: raw source, parsed/intermediate result, review item, canonical candidate, export/view, and cache boundaries are already defined.
- `app/main.py`: AI extraction approval gate, ROI payload minimization, draft schema, plausibility checks, review attention, canonical candidate apply gate, and export blockers.
- `app/db.py`: `photo_log`, `parse_result`, `review_queue`, `source_record`, `correction_log`, `canonical_candidate`, `card_snapshot`, `export_log`, `card_note_item_log`, and `mouse_master`.
- `config/photo_e2e_validation_cases.json`: existing real-photo regression cases.
- `scripts/verify-photo-e2e-cases.py`: existing deterministic validation harness.

Requested but not present in this repo:

- `docs/Lattice_v3_Master_Spec.md`
- `docs/PERSONA_MODE_BOUNDARY.md`
- `docs/README.md`
- `backend/main.py`
- `src/db_utils.py`
- project-level `Skill.md`
- paper-reading modules such as `reader_agent`, `citation_grounding`, `deep-read job`, `Research DNA`, or `Meeting Pack`

## Adopted PoC Design

The adopted PoC is `evals/cage_card_skill_gym/`.

Components:

- `probes/*.yaml`: JSON-compatible YAML fixtures. Boundary is `review item / test fixture`; canonical is false.
- `run_baseline.py`: dependency-free deterministic evaluator.
- `rubric.schema.json`: binary rubric shape.
- `README.md`: explains scope and non-runtime status.
- `tests/test_cage_card_skill_gym.py`: verifies pass/fail behavior.
- `package.json` script: `npm run test:cage-card-skill-gym`.

The harness checks only basic safety expectations:

- probe is non-canonical
- probe boundary is `review item / test fixture`
- expected boundary is a known project data boundary
- risky scenarios route to review
- traceability must be preserved
- canonical writes are forbidden
- external inference policy is local-only or explicitly approval-gated

This is intentionally narrow. It is not an OCR evaluator, not an LLM benchmark, and not a substitute for `scripts/verify-photo-e2e-cases.py`.

## Seed Probe Taxonomy

Current probe categories:

- `photo_roi_grounding`
- `excel_table_interpretation`
- `claim_evidence_separation`
- `event_reconstruction`
- `limitation_detection`
- `reproducibility`
- `unsupported_unknown_logging`

Current seed probes:

1. impossible ear label stays reviewable
2. numeric notes are not mouse IDs
3. low-confidence card blocks export
4. external AI requires per-request approval
5. legacy workbook row stays export/view candidate
6. duplicate active mouse blocks canonical apply
7. struck note line is preserved as event evidence
8. ambiguous date does not overwrite raw
9. ROI crop is cache, not raw source
10. export is generated from accepted structured state

## Accept / Reject Criteria For Future Guidance Changes

Accept a candidate guidance change only when:

- all existing replay probes still pass
- the new failing probe is fixed by narrow wording or rule clarification
- source/canonical/export boundaries remain explicit
- raw evidence and normalized values remain separate
- external inference remains local-only or approval-gated
- no hard-coded strain, genotype, protocol, or date rule is introduced
- the change does not alter runtime, DB, or API contracts

Reject a candidate guidance change when:

- it encourages OCR or LLM output to become canonical immediately
- it removes traceability back to source photo, note line, or workbook row
- it overfits a single hard probe while weakening easier regression probes
- it expands AGENTS or future Skill guidance without measurable failure evidence
- it requires product multi-agent orchestration

## Verification Snapshot

Commands run during the PoC:

```powershell
python -m pytest tests/test_cage_card_skill_gym.py -q
npm run test:cage-card-skill-gym
python -m json.tool evals/cage_card_skill_gym/rubric.schema.json
```

Observed result:

- `tests/test_cage_card_skill_gym.py`: 3 passed
- `npm run test:cage-card-skill-gym`: 10 passed, 0 failed
- schema and probes parse as JSON-compatible YAML

## Current Worktree Caution

At the time of this review, the active branch was `codex/scoped-comparison-review-actions`.

Unrelated existing modified files were observed:

- `app/main.py`
- `scripts/verify-local-app.py`
- `static/index.html`

The Ctx2Skill-lite PoC source files are:

- `package.json`
- `docs/superpowers/plans/2026-05-09-cage-card-skill-gym.md`
- `docs/ctx2skill_lite_adoption_review.md`
- `evals/`
- `tests/test_cage_card_skill_gym.py`

Before committing, stage only the Ctx2Skill-lite files unless the scoped comparison review changes are intentionally part of the same branch slice.

## Final Recommendation

Do now:

- Keep `cage_card_skill_gym` as a tiny offline guardrail.
- Use it before changing project guidance, extraction prompts, or review rules.
- Treat every probe as non-canonical review/test evidence.

Do later:

- Add probes when a real review failure or OCR ambiguity appears.
- Add a report file only if baseline reports are intentionally adopted as review artifacts.
- Consider an LLM judge only as a secondary note generator, never as the binary accept gate.

Do not do:

- Do not import the full Ctx2Skill framework.
- Do not add product runtime Challenger/Reasoner/Judge orchestration.
- Do not auto-edit `AGENTS.md` or future `Skill.md`.
- Do not use paper-reading probe categories until this repo actually contains paper-reading modules.
