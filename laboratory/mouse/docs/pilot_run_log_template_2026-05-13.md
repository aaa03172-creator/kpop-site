# Pilot Run Log Template - 2026-05-13

Layer classification: review item / pilot run log template.

Canonical: false.

Copy this template to `docs/pilot_runs/YYYY-MM-DD-<label>.md` after a synthetic or copied non-production pilot run. Do not include private source photos, private manifests, animal-room details, or local paths that should not be committed.

## Run Metadata

| Field | Value |
| --- | --- |
| Run label |  |
| Date/time |  |
| Operator |  |
| Branch |  |
| Commit |  |
| Dataset type | synthetic / copied non-production / copied real pilot |
| Photo count |  |
| Manifest used |  |
| Browser/upload surface | normal browser UI / standalone Playwright / in-app Browser not used for upload |
| Extraction mode chosen | AI / local OCR / manual extraction decision |
| Backup before run |  |
| Backup after run |  |

## Data Boundary Summary

| Artifact | Boundary | Notes |
| --- | --- | --- |
| Source photos | raw source | Copied files only; originals unchanged. |
| Pilot expected labels | review item / test fixture | Local evaluation labels, not canonical colony state. |
| OCR or AI draft output | parsed or intermediate result | Review aid only. |
| Review resolutions | review item | Preserve before/after values and evidence. |
| Applied candidates | canonical structured state | Only after explicit reviewed apply. |
| XLSX/CSV/export manifest | export or view | Generated from accepted structured state. |
| Temporary screenshots/logs/cache | cache | Do not commit unless explicitly adopted. |

## Workflow Counts

| Metric | Count |
| --- | ---: |
| Photos uploaded |  |
| Parse/extraction attempts |  |
| Manual transcriptions |  |
| AI extraction attempts |  |
| `must_review` items opened |  |
| `quick_check` items opened |  |
| `trace_only` items retained |  |
| Corrections applied |  |
| Duplicate active mouse conflicts |  |
| Canonical candidates created |  |
| Canonical candidates applied |  |
| Exports generated |  |
| Blocked export attempts |  |

## Sanitized Metrics To Publish

Publish aggregate counts and rates only. Do not include private photo paths, raw card text, raw OCR/AI payloads, generated workbook paths, local database paths, backup paths, or case-level animal-room details.

| Metric | Value |
| --- | ---: |
| Manifest cases verified |  |
| Photos with extraction draft |  |
| Photos requiring manual transcription |  |
| Review items corrected |  |
| Review items accepted without correction |  |
| Export-blocking items found |  |
| Export-blocking items resolved |  |
| XLSX exports generated |  |

## Failure Taxonomy

| Failure label | Count | Sanitized note |
| --- | ---: | --- |
| `source_trace_missing` |  |  |
| `low_confidence_unreviewed` |  |  |
| `raw_normalized_mixed` |  |  |
| `mouse_id_or_note_line_error` |  |  |
| `date_or_count_error` |  |  |
| `mating_litter_context_error` |  |  |
| `export_safety_error` |  |  |
| `privacy_leak` |  |  |
| `operator_workload_excessive` |  |  |

## Per-Photo Notes

| Case/photo label | Card type | Review level | Action taken | Evidence trace OK? | Notes |
| --- | --- | --- | --- | --- | --- |
|  | separated / mating / unclear / Other / Unknown | must_review / quick_check / trace_only |  | yes / no |  |

## Timing

| Activity | Approximate time |
| --- | ---: |
| Input preparation |  |
| Upload |  |
| Transcription/extraction |  |
| Review |  |
| Canonical apply |  |
| Export |  |
| Backup and notes |  |

## Reviewer Workload Criteria

| Criterion | Go threshold | Run value |
| --- | --- | ---: |
| Median review time per photo | At or below 4 minutes |  |
| 90th percentile review time per photo | At or below 8 minutes |  |
| Manual transcription required | At or below 40% unless intentionally testing unclear cards |  |
| Reviewer can explain evidence for exported rows | 100% of exported rows |  |
| Unresolved `must_review` items at export time | 0 |  |

## Accuracy Evaluation Criteria

Use the same private manifest expected fields for local scoring, then publish only aggregate results.

| Field family | Go threshold | Run value |
| --- | --- | ---: |
| Mouse IDs and note-line continuity | 95% exact or reviewer-corrected before apply; 0 unreviewed high-risk misses |  |
| Card type and review routing | 100% of unclear/blocker cases route to review |  |
| Sex/count and DOB/date handling | 90% correct after review; ambiguous dates stay raw until confirmed |  |
| Mating/litter context | 90% correct after review with traceable sire/dam/litter notes |  |
| Export provenance | 100% of exported rows trace to copied photo, note item, or accepted correction |  |

## Friction Points

1. 
2. 
3. 

Record whether the in-app Browser control surface was avoided for private file upload. It does not provide file upload support for this copied-photo pilot, so upload/download verification should use the normal local browser UI or standalone Playwright.

## Evidence Traceability Findings

- Exported rows with clear source photo or note trace:
- Rows or candidates needing traceability improvement:
- Review items that were difficult to resolve:

## Verification After Run

Run relevant commands and record exact results:

```powershell
npm run test:real-photo-pilot
python -m pytest tests/test_real_photo_pilot_verifier.py -v
git status --short --ignored
```

For broader changes, run:

```powershell
python -m pytest tests
npm test
npm run test:local
npm run test:photo-e2e
npm run test:browser-photo-export-e2e
npm run test:synthetic-draft-extraction
npm run test:cage-card-skill-gym
python scripts/verify-acceptance-matrix.py
```

## Go / No-Go Notes

- No lost source photos:
- No silent canonical overwrite:
- No final export while `must_review` blockers remained open:
- Operator could explain source evidence for exported rows:
- Backup and restore confidence:
- Private data containment:
- 20-30 photo manifest coverage:
- Accuracy threshold decision:
- Reviewer workload decision:
