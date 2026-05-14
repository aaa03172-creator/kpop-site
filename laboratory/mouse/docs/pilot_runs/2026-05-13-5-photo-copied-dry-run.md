# 5-Photo Copied Pilot Dry Run - 2026-05-13

Layer classification: review item / pilot run log.

Canonical: false.

This sanitized run log records an operator-style dry run with five real copied cage-card photo files in a private local manifest. It intentionally omits private photo content, private source paths, raw OCR payloads, generated workbook files, local database files, backup folders, and exact private source filenames.

## Run Metadata

| Field | Value |
| --- | --- |
| Run label | 5-photo-copied-dry-run |
| Date/time | 2026-05-13 |
| Operator | Codex local verification |
| Branch | codex/verify-setup-doc |
| Dataset type | real copied local photos, private manifest |
| Photo count | 5 browser-uploaded source photos |
| Extraction path | manual transcription path; AI unavailable, no external inference sent |
| Browser surface | Standalone Playwright against private local app instance |
| App data scope | private disposable app project |

## Data Boundary Summary

| Artifact | Boundary | Notes |
| --- | --- | --- |
| Copied source photos | raw source | Five image files were copied into the private pilot folder and uploaded through the browser flow. |
| Private manifest | review item / test fixture | Local-only; verified five source-photo paths and review coverage. |
| Manual extraction records | parsed or intermediate result | Manual transcription was selected because AI was unavailable and no external provider was approved. |
| Review resolutions | review item | Manual-photo, comparison, legacy-row, and strain-registry review items were resolved before export readiness. |
| Applied candidate | canonical structured state | One candidate applied from source-backed note lines, creating two mouse rows and two events in the private run. |
| CSV/XLSX downloads | export or view | Ready CSV, separation XLSX, and animal-sheet XLSX were generated after readiness. |
| Backup/restore drill | export or view / local pilot copy | Backup copied DB, photos, exports, and artifacts; restore was validated in a separate probe folder. |

## Workflow Counts

| Metric | Count |
| --- | ---: |
| Manifest cases verified | 5 |
| Photos uploaded | 5 |
| Manual transcriptions saved | 5 |
| External AI/OCR calls | 0 |
| Review items total | 19 |
| Open reviews after resolution | 0 |
| Canonical candidates applied | 1 |
| Mouse rows created | 2 |
| Generated export log entries | 3 |
| Downloaded XLSX files | 2 |
| Restored photo files in restore probe | 5 |
| Restored artifact JSON files | 4 |

## Evidence Traceability Findings

- Private manifest verification passed with five existing source photo files and coverage for separated, mating, unclear, and other/trace-only cases.
- Upload preserved all five photos as raw source records before any parsed/manual evidence.
- Manual extraction kept the run local-only; health status reported AI unavailable and approval required for external inference.
- Comparison review mapping first tried a trace-only case; canonical apply correctly blocked it because there were no parsed mouse note lines.
- Mapping a source-backed note-line case produced an apply preview with two proposed mouse rows, two events, no duplicate risks, and no blockers.
- Export readiness became true only after review resolution and canonical candidate apply.
- Export log recorded generated `mouse_csv`, `separation_xlsx`, and `animal_sheet_xlsx` entries with zero blocked reviews.
- Restore probe verified the recovered DB contained 5 photo rows, 0 open reviews, 1 applied candidate, 2 mouse rows, and 3 generated export logs.

## UX / Data Gaps

- Closed in follow-up: a trace-only or note-line-weak comparison mapping now shows a preflight warning before creating a candidate draft.
- Closed in follow-up: canonical candidate apply now updates the candidate table through the applied response before the next refresh.
- Closed in follow-up: upload batch summary and release preview now include operator-facing status label, detail, and next action wording for `comparison_needed` and mapping states.
- Still open: the in-app Browser control surface did not expose file upload support, so the operator dry run used standalone Playwright for the upload/download browser path.
- Still open: the UI card-type selector has `Separated`, `Mating`, and `Unknown`; the manifest's `other` case had to map to `Unknown`.
- The sanitized dry run avoids recording private photo text. That protects privacy, but it also means this public log cannot prove manual transcription accuracy against the raw image content.

## Verification Evidence

```powershell
python scripts/verify-real-photo-pilot.py --manifest <private manifest>
node <private browser dry-run script>
powershell -ExecutionPolicy Bypass -File scripts/backup-local-pilot.ps1 -ProjectRoot <private app project> -BackupRoot <private backup folder> -Label 5-photo-copied-dry-run
powershell -ExecutionPolicy Bypass -File scripts/restore-local-pilot.ps1 -BackupPath <private backup> -TargetRoot <private restore probe>
python <restore probe count check>
```

Observed results:

- Real-photo manifest verifier: passed; 5 cases, 0 failures.
- Browser dry run: passed after timing and candidate-selection retries; final state had 5 photos, 0 open reviews, 1 applied candidate, export readiness true, and three downloads.
- Backup: passed; DB, photos, exports, and artifacts copied with no missing items.
- Restore: passed; DB, photos, exports, and artifacts restored into a separate probe folder.
- Restore probe count check: passed; restored DB and files matched the expected dry-run state.
- Follow-up UX closure tests: `tests/test_review_assistant_draft.py`, `tests/test_upload_batch_operator_language.py`, and `npm run test:browser-photo-export-e2e` passed after the warning, apply-refresh, and operator wording changes.

## Go / No-Go Notes

- Raw photo preservation: pass for the private run.
- External payload safety: pass; no external inference was sent.
- Review gate before export: pass; final open review count was zero.
- Candidate apply gate: pass; note-line-free candidate was blocked and source-backed candidate applied.
- XLSX readiness/download: pass; separation and animal-sheet XLSX files downloaded.
- Backup/restore confidence: pass for the private pilot copy.
- Public auditability of exact manual transcription: limited by privacy sanitization; verify against private raw photos before using this as scientific data.
