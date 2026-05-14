# Pilot Readiness Baseline - 2026-05-13

Layer classification: export or view / non-canonical baseline record.

Canonical: false.

This document records the executable baseline used to begin local pilot readiness work. It does not define product behavior, schema, API contracts, or lab policy. When this document disagrees with `AGENTS.md`, `final_mouse_colony_prd.md`, runtime code, or committed tests, those sources win.

## Scope

This baseline supports a controlled local pilot only. The first pilot must use copied or synthetic cage-card photos and copied workbook inputs. Do not make this checkout the lab's only operational source of truth until the real-photo pilot harness, backup/restore drill, operator checklist, and go/no-go criteria are complete.

## Snapshot

| Field | Value |
| --- | --- |
| Captured at | 2026-05-13 12:40:58 +09:00 |
| Branch | `codex/pilot-readiness` |
| Commit | `a1d1ef35618aedcfbfff0ed53b0cbde40881b274` |
| Python | `Python 3.14.4` |
| Node.js | `v24.15.0` |
| npm | `11.12.1` |

## Data Boundary Reminder

| Artifact | Boundary | Pilot rule |
| --- | --- | --- |
| Copied cage-card photo | raw source | Preserve unchanged; never delete because OCR quality is poor. |
| Synthetic validation photo | raw source / test fixture | Local-only verification input; not lab evidence. |
| OCR text or AI draft | parsed or intermediate result | Review aid only; not canonical truth. |
| Pilot expected labels | review item / test fixture | Used to evaluate workflow behavior; not canonical colony state. |
| Reviewed correction | review item | Preserve before/after values and source evidence. |
| Applied mouse/cage/mating/litter state | canonical structured state | Only after explicit reviewed apply with traceability. |
| Workbook preview, export manifest, validation report | export or view | Generated from accepted structured state; not source of truth. |
| ROI crops, caches, generated logs | cache | Disposable unless explicitly adopted as source documentation. |

## Verification Commands

Run these commands before treating this baseline as pilot-ready:

```powershell
python -m pytest tests
npm test
npm run test:local
npm run test:photo-e2e
npm run test:browser-photo-export-e2e
npm run test:synthetic-draft-extraction
npm run test:cage-card-skill-gym
python scripts/verify-acceptance-matrix.py
git status --short --ignored
```

## Verification Results

Results captured after this document was created:

| Command | Expected result | Actual result |
| --- | --- | --- |
| `python -m pytest tests` | All tests pass | `219 passed, 92 warnings` |
| `npm test` | `MVP verification passed.` | Passed |
| `npm run test:local` | `Local app scaffold verification passed.` | Passed |
| `npm run test:photo-e2e` | JSON status passed with zero strict failures | Passed: 5 cases, 5 passed, 0 failed, 0 strict failures |
| `npm run test:browser-photo-export-e2e` | JSON status passed | Passed; data boundaries reported for photo upload, manual transcription, review resolution, candidate apply, export download, and upload batch release |
| `npm run test:synthetic-draft-extraction` | JSON verification passed; no external inference | Passed: 5 cases, 5 passed, 0 failed, `external_inference_used=false`, `canonical_writes=0` |
| `npm run test:cage-card-skill-gym` | 10/10 probes pass | Passed: 10 passed, 0 failed |
| `python scripts/verify-acceptance-matrix.py` | Acceptance matrix verification passed | Passed |
| `git status --short --ignored` | Only task docs/source plus ignored runtime artifacts | Passed with intended task documentation changes and ignored runtime artifacts only |

Note: an earlier exploratory run on the prior branch observed 221 pytest items. This baseline records the actual pilot branch rerun result: 219 collected tests, all passing.

## Ignored Runtime Artifacts

These paths may appear in `git status --short --ignored` during local pilot work and should not be committed unless explicitly adopted:

- `.venv/`
- `node_modules/`
- `data/`
- `mousedb_artifacts/`
- `app/__pycache__/`
- `evals/__pycache__/`
- `evals/cage_card_skill_gym/__pycache__/`
- `mousedb/__pycache__/`
- `scripts/__pycache__/`
- `tests/__pycache__/`
- `.pytest_cache/`
- `.env.local`

## Current Limitation

This baseline has strong synthetic and fixture-backed coverage, but real cage-card photo accuracy is not yet proven. The next required task is `docs/real_photo_pilot_protocol_2026-05-13.md`, followed by a private-photo-safe real-photo pilot harness.
