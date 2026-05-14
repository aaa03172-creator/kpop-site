# Copied-Photo Pilot Go/No-Go Criteria - 2026-05-14

Layer classification: review item / pilot readiness guide.

Canonical: false.

This guide defines the readiness decision for the first 20-30 copied-photo pilot. It does not change active UI behavior, export behavior, schemas, or lab policy. If this guide conflicts with `AGENTS.md`, `final_mouse_colony_prd.md`, committed tests, or runtime code, those sources win.

## Required Pack

| Artifact | Boundary | Requirement |
| --- | --- | --- |
| Copied pilot photos | raw source | 20-30 copied files stored outside Git. Original lab source files remain unchanged. |
| Private pilot manifest | review item / test fixture | One case per copied photo with source pointer, traceability label, card type, review level, export-blocking expectation, and minimum expected fields. |
| Sanitized run log | review item / pilot run log | Generated with `scripts/prepare-copied-pilot-run.py`; omits private paths, raw OCR/AI payloads, generated workbook paths, database paths, and backup paths. |
| Backup/restore evidence | export or view / operational evidence | Recorded as labels and pass/fail booleans only; no backup or restore folder paths in committed artifacts. |

## Hard Go Gates

All hard gates must pass before expanding beyond the copied-photo pilot.

| Gate | Go condition | No-go condition |
| --- | --- | --- |
| Private data containment | Git contains no private photos, private manifests, raw copied-photo text, OCR/AI payloads, local database paths, backup paths, or generated pilot workbooks. | Any committed private path or raw source payload appears outside an explicitly approved sanitized fixture. |
| Manifest photo count | Verifier reports 20-30 cases. | Fewer than 20 or more than 30 cases. |
| Card-type coverage | Verifier reports separated, mating, unclear, and other coverage. | Any required card type is absent. |
| Review-level coverage | Verifier reports must_review, quick_check, and trace_only coverage. | Any required review level is absent. |
| Export-blocking expectations | Verifier reports at least one blocking and at least one non-blocking case, with unresolved must_review cases treated as export blockers. | Every case is non-blocking, every case is blocking without a control, or a must_review case is expected to export without review. |
| Source preservation | Copied source photos are retained even if blurry, cropped, or unreadable. | Failed or low-quality photos are discarded instead of remaining traceable raw evidence. |
| Review traceability | Corrections preserve before/after values and trace to a copied photo, note line, imported row, or accepted review item. | A correction or inferred state change can overwrite high-risk data without evidence. |
| Backup/restore drill | Before-backup label, after-backup label, restore-probe label, restore success, and overwrite-refusal success are present in the manifest readiness evidence. | Backup/restore evidence is missing, false, or includes local paths instead of labels. |

## Soft Go Gates

Soft misses do not automatically block the copied-photo pilot, but they block expansion until documented.

| Gate | Go condition | Follow-up condition |
| --- | --- | --- |
| Reviewer workload | Median review time is at or below 4 minutes per photo and 90th percentile is at or below 8 minutes. | Narrow the next pilot slice or improve runbook wording before adding more photos. |
| Manual transcription burden | Manual transcription is at or below 40% unless the run deliberately over-samples unclear cards. | Split unclear-card stress testing from ordinary copied-photo readiness. |
| Failure taxonomy | Each failure maps to a sanitized label in the run log. | Add a sanitized label before publishing the summary. |

## Commands

Run the private manifest verifier:

```powershell
python scripts/verify-real-photo-pilot.py --manifest "<private manifest path>"
```

Generate a sanitized run log:

```powershell
python scripts/prepare-copied-pilot-run.py --manifest "<private manifest path>" --run-label "<label>" --output-log docs/pilot_runs/YYYY-MM-DD-<label>.md
```

Check the committed example pack:

```powershell
python scripts/verify-real-photo-pilot.py --manifest config/copied_photo_pilot_readiness_manifest.example.json
python scripts/prepare-copied-pilot-run.py --manifest config/copied_photo_pilot_readiness_manifest.example.json --run-label copied-photo-pilot-readiness-example --output-log docs/pilot_runs/2026-05-14-copied-photo-pilot-readiness-example.md
```

## Decision Record

Use `go` only when the verifier reports `readiness.status=go`, every hard gate is satisfied, and the sanitized run log contains no private paths or raw copied-photo payloads.

Use `no_go` when any hard gate fails. Do not treat `no_go` as a data loss event; keep the copied photos, private manifest, review notes, and backup/restore evidence for the next reviewed run.
