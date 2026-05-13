# Pilot Operator Checklist - 2026-05-13

Layer classification: review item / local pilot checklist.

Canonical: false.

Use this checklist for a controlled local pilot with copied cage-card photos. It does not replace lab SOPs, animal records, institutional backup policy, or the adopted PRD.

## Before The Session

- [ ] Use copied photos only. Keep original handwritten cage-card photos and source folders unchanged.
- [ ] Confirm the copied photo folder is outside Git.
- [ ] Confirm the pilot photo set follows `docs/real_photo_pilot_protocol_2026-05-13.md`.
- [ ] Confirm each photo has a local label with card type, traceability label, expected review level, and expected export-blocking state.
- [ ] Confirm `My Assigned Strains` is up to date before extraction or review.
- [ ] Run a backup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup-local-pilot.ps1 -Label before-pilot-session
```

- [ ] Confirm the backup manifest was written outside Git.
- [ ] Start the local app with `start.bat`.

## During Upload And Extraction

- [ ] Upload photos in a named batch.
- [ ] Confirm every uploaded photo appears in Photo Review.
- [ ] Keep original photos as `raw source`, even if blurry or unreadable.
- [ ] Use local/manual transcription when the card is unclear.
- [ ] Use external AI extraction only after explicit approval for that run.
- [ ] If external AI is approved, send only the selected source photo and minimal assigned-strain scope.
- [ ] Treat OCR, local OCR, and AI drafts as `parsed or intermediate result`.

## During Review

- [ ] Inspect the source photo for every `must_review` item.
- [ ] Do not accept low-confidence, conflicting, biologically unlikely, or unclear records without review.
- [ ] Preserve raw values separately from normalized values.
- [ ] Preserve before/after values for corrections.
- [ ] Confirm duplicate active mouse conflicts through the movement-review flow, not a generic correction.
- [ ] Confirm note-line evidence remains visible for mouse IDs, ear labels, litter notes, and struck-through lines.

## Before Canonical Apply

- [ ] Open the canonical candidate apply preview.
- [ ] Confirm proposed writes link to source photo or note item.
- [ ] Confirm validation report has no blocking checks.
- [ ] Apply only reviewed candidates.
- [ ] Do not apply candidates produced only from uncertain OCR.
- [ ] Confirm action log or audit trail records the reviewed change.

## Before Export

- [ ] Confirm unresolved `must_review` blockers are zero.
- [ ] Confirm export preview rows are generated from accepted structured state.
- [ ] Confirm each exported row has source photo, note item, or accepted-state traceability.
- [ ] Confirm the expected workbook filename before download.
- [ ] Download XLSX only after export readiness is true.
- [ ] Preview export manifest and validation report when available.

## After The Session

- [ ] Record number of uploaded photos.
- [ ] Record number of manual corrections.
- [ ] Record number of `must_review`, `quick_check`, and `trace_only` items.
- [ ] Record number of canonical candidates applied.
- [ ] Record exports generated and any blocked export attempts.
- [ ] Run a post-session backup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup-local-pilot.ps1 -Label after-pilot-session
```

- [ ] Keep private photos, private manifests, generated workbooks, and backup folders out of Git.

## Stop Conditions

Stop the pilot session and do not export if any of these occur:

- A source photo is missing or cannot be opened.
- A mouse identity conflict cannot be resolved from source evidence.
- A duplicate active mouse review is unresolved.
- A genotype result or target category is unexpected or unsupported.
- A date is ambiguous and would change biological interpretation.
- A low-confidence or garbled OCR result is needed for export but has not been reviewed.
- Export validation fails or final export is blocked.
- Any external inference payload feels unsafe or too broad.
- The operator cannot explain the source evidence for an exported row.

