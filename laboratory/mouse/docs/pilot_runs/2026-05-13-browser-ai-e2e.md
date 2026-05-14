# Browser AI E2E Pilot Run - 2026-05-13

Layer classification: review item / pilot run log.

Canonical: false.

This sanitized run log records the synthetic copied-photo browser pilot closure check. It does not include private source photos, private manifests, generated workbooks, local database files, or backup folders.

## Run Metadata

| Field | Value |
| --- | --- |
| Run label | browser-ai-e2e |
| Date/time | 2026-05-13 |
| Operator | Codex local verification |
| Branch | codex/verify-setup-doc |
| Dataset type | synthetic copied-photo stand-in |
| Photo count | 1 browser-uploaded source photo |
| Manifest used | example real-photo manifest plus synthetic E2E fixtures |
| Backup before run | disposable backup/restore drill only |
| Backup after run | disposable backup/restore drill only |

## Data Boundary Summary

| Artifact | Boundary | Notes |
| --- | --- | --- |
| Uploaded source photo | raw source | Browser E2E used the committed synthetic cage-card evidence image. |
| AI extraction output | parsed or intermediate result | External provider was locally faked; browser approval path and payload-minimization record were exercised. |
| Review resolutions | review item | Numeric note and auxiliary reviews were resolved before export readiness. |
| Applied candidate | canonical structured state | Candidate apply wrote accepted source-backed mouse state during the disposable run. |
| XLSX exports | export or view | Separation and animal-sheet XLSX downloads were generated only after readiness. |
| Backup/restore drill | export or view / local operational copy | Disposable temp project root; restore refused overwrite without `-Force`, then restored with `-Force`. |

## Workflow Counts

| Metric | Count |
| --- | ---: |
| Photos uploaded | 1 |
| AI extraction attempts | 1 |
| Manual transcriptions | 0 |
| Source-note review resolved | 1 |
| Auxiliary reviews resolved | 4 |
| Canonical candidates applied | 1 |
| XLSX exports downloaded | 2 |
| Blocked export attempts | 0 in final ready state |

## Evidence Traceability Findings

- AI extraction approval recorded `approved_external_inference=true` with scope `single_photo_ai_transcription_draft`.
- Payload review recorded no full colony records, no Excel rows, no raw source photo, derived ROI crops sent, and assigned strain scope sent.
- Export rows were produced after review resolution and canonical candidate apply, not directly from OCR/AI draft output.
- Backup manifest and restore output both retained `layer=export or view` and `canonical=false`.

## Gap Closed

- The review detail panel was re-rendered when an operator clicked `Inspect`, but its resolve/correction handlers were only attached during the full refresh path. The UI now reattaches those handlers after detail-panel re-renders.
- The browser E2E verifier now exercises the approval-gated AI extraction path instead of substituting manual transcription, and it asserts the external approval and payload-minimization record.

## Verification After Run

```powershell
npm run test:browser-photo-export-e2e
npm run test:real-photo-pilot
npm run test:photo-e2e
powershell backup/restore drill against disposable temp project root
.venv\Scripts\python.exe -m pytest tests/test_ai_payload_minimization.py tests/test_artifact_workflow.py tests/test_browser_photo_export_e2e.py -q
npm run verify
```

Observed results:

- `npm run test:browser-photo-export-e2e`: passed; AI extraction method was `ai_photo_extraction`; XLSX downloads covered separation and animal sheet.
- `npm run test:real-photo-pilot`: passed 4/4 example manifest cases.
- `npm run test:photo-e2e`: passed 5/5 strict synthetic photo E2E cases.
- Backup/restore drill: passed; restore refused overwrite without `-Force` and restored database, photos, exports, and artifacts with `-Force`.
- Focused pytest: 21 passed.
- `npm run verify`: passed; final Python suite reported 223 passed, 92 warnings.

## Environment Note

The in-app Browser plugin was attempted for a lightweight localhost render smoke check, but this workspace's browser client returned `net::ERR_BLOCKED_BY_CLIENT` for both `127.0.0.1` and `localhost`. The actual browser E2E evidence above comes from the repository Playwright verifier.

## Go / No-Go Notes

- No lost source photos: pass for the disposable run.
- No silent canonical overwrite: pass; review and candidate apply gates were exercised.
- No final export while blockers remained open: pass for the ready final export state.
- Operator could explain source evidence for exported rows: pass for synthetic evidence.
- Backup and restore confidence: pass for disposable local drill.
