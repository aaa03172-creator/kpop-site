# Manual Pilot Walkthrough - 2026-05-13

Layer classification: review item / local pilot procedure.

Canonical: false.

This walkthrough is for controlled local pilot sessions using copied cage-card photos. It does not replace lab SOPs or make the local MVP the only source of truth.

## 1. Prepare The Pilot Inputs

1. Copy 5-30 cage-card photos into a local folder outside Git.
2. Keep original photo storage unchanged.
3. Label each copied photo according to `docs/real_photo_pilot_protocol_2026-05-13.md`.
4. Confirm expected review levels and export-blocking expectations.
5. Run a pre-session backup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup-local-pilot.ps1 -Label before-manual-walkthrough
```

Decision point:

- Continue only if copied photos open locally and the backup manifest is written outside Git.

## 2. Start The Local App

Run:

```powershell
start.bat
```

Open:

```text
http://127.0.0.1:8765
```

Expected:

- The Photo Review Workbench opens.
- Existing local data, if any, appears from `data/mouse_lims.sqlite`.

Failure handling:

- If dependencies fail to install, run `python -m pip install -r requirements.txt` and retry.
- If port `8765` is already in use, stop the existing local server or run uvicorn manually on another port.
- If the page loads but API calls fail, check that the terminal still shows the uvicorn server running.

## 3. Confirm Assigned Strain Scope

1. Open the settings or assigned strain section.
2. Confirm `My Assigned Strains` contains only strains relevant to this pilot.
3. Add missing assigned strains or aliases only from approved local knowledge.
4. Do not create new strain names automatically from OCR text.

Decision point:

- If assigned strain scope is uncertain, stop extraction and resolve the strain list first.

## 4. Upload Photos

1. Open Photo Review.
2. Click `Upload Photos`.
3. Select copied pilot photos.
4. Confirm every selected photo appears in the workbench.
5. Confirm each uploaded photo remains visible as source evidence.

Expected data boundaries:

- Uploaded photos: `raw source`.
- Upload batch: `raw source batch workflow`.
- Any preview crop: `cache`.

Failure handling:

- If one upload fails, do not re-upload the whole batch blindly. Confirm which photos were stored first.
- If a source photo is missing or cannot be opened, stop the pilot and fix the copied input folder.
- The Codex in-app Browser control surface does not provide file upload support for this private copied-photo pilot. Use the normal local browser UI or a standalone Playwright run when the verification step must upload private copied photos.
- For unexpected card formats, select `Other / Unknown`. Treat these as trace-only until source evidence supports a supported separated or mating workflow.

## 5. Choose Extraction Mode

Use one of these paths:

| Mode | Use when | Boundary |
| --- | --- | --- |
| Manual transcription | Card is unclear, OCR is unavailable, or external inference is not approved. | parsed or intermediate result |
| Local OCR draft | Local Tesseract is available and output is used only as a review aid. | parsed or intermediate result |
| AI extraction | User explicitly approves the external inference run. | parsed or intermediate result |

AI decision point:

- Do not use external AI unless approved for this specific run.
- If approved, send only the selected source photo plus minimal assigned-strain scope.
- Do not send predecessor Excel rows or unnecessary full colony records.

Failure handling:

- If `OPENAI_API_KEY` is missing, use manual transcription or local OCR only.
- If OCR is empty, garbled, or low-confidence, keep the item reviewable.
- If the extraction result creates a surprising biological claim, route it to review.

## 6. Manually Correct Or Confirm Parsed Fields

For each photo:

1. Compare raw visible text against normalized fields.
2. Keep uncertain raw text unchanged.
3. Correct only fields supported by source photo or note-line evidence.
4. Preserve before/after values through the review flow.
5. Confirm note lines, mouse IDs, ear labels, sex/count, DOB, mating notes, and litter notes.

Decision point:

- If the raw photo does not support a normalized value, do not accept it.

## 7. Resolve Focus Review Items

1. Open Focus Review or Review Queue.
2. Start with `must_review` items.
3. Inspect source photo for each blocking item.
4. Resolve low-confidence, conflicting, biologically unlikely, or unclear evidence.
5. Use the dedicated movement review for duplicate active mouse conflicts.
6. Leave `quick_check` and `trace_only` items visible for audit if they are not export-blocking.

Failure handling:

- If a duplicate active mouse cannot be resolved from source evidence, stop before canonical apply.
- If a date is ambiguous and affects age, mating, litter, or export grouping, keep it reviewable.
- If a genotype category is unsupported, route to review and do not export as accepted state.

## 8. Apply Canonical Candidates

1. Open Candidate Records or the canonical candidate view.
2. Open apply preview before applying.
3. Confirm proposed writes are source-backed.
4. Confirm validation report has no blockers.
5. Apply only reviewed candidates.

Expected data boundaries:

- Apply preview: `export or view`.
- Applied mouse/cage/mating/litter/event state: `canonical structured state`.
- Review resolution and correction context: `review item`.

Failure handling:

- If validation blocks apply, return to Review Queue.
- If source photo or note item traceability is missing, do not apply.
- If the candidate was created only from uncertain OCR, do not apply.

## 9. Generate Excel Export

1. Open Export Center.
2. Confirm unresolved `must_review` blockers are zero.
3. Confirm export preview rows are generated from accepted structured state.
4. Confirm source evidence or trace links are visible for preview rows.
5. Confirm expected filename.
6. Click `Download Separation XLSX` or `Download Animal Sheet XLSX`.

Expected data boundaries:

- Workbook preview: `export or view`.
- XLSX download: `export or view`.
- Export manifest and validation report: `export or view`.

Failure handling:

- If export returns blocked status, open the blocker and resolve review evidence first.
- If accepted rows are missing, do not create workaround rows in Excel.
- If export filename or row grouping looks wrong, stop and inspect accepted state and source evidence.

## 10. Inspect The Session Outputs

After the run, inspect:

| Area | What to check |
| --- | --- |
| `data/` | Local SQLite state and uploaded photo folders exist as expected. |
| `mousedb_artifacts/` | Proposed changesets, validation reports, or export manifests were generated when expected. |
| Export log | Generated and blocked export attempts are recorded. |
| Review Queue | Remaining `must_review` items are understood and not ignored. |
| Downloaded XLSX | Rows match accepted source-backed state, not raw OCR or predecessor Excel alone. |

Run a post-session backup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup-local-pilot.ps1 -Label after-manual-walkthrough
```

## 11. Record The Pilot Notes

Record:

- number of photos uploaded
- number of photos requiring manual transcription
- number of `must_review`, `quick_check`, and `trace_only` items
- number of corrections applied
- number of canonical candidates applied
- exports generated
- blocked export attempts
- top friction points
- any evidence traceability gaps

Do not commit private photos, copied private manifests, generated workbooks, local database files, or backup folders.
