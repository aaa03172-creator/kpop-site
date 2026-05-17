# Pilot Runs

Layer classification: review item / pilot run log index.

Canonical: false.

Store sanitized pilot run logs here after synthetic or copied non-production dry runs. Use `docs/pilot_run_log_template_2026-05-13.md` as the starting point, or generate a prefilled copied-photo shell with:

```powershell
python scripts/prepare-copied-pilot-run.py --manifest <private manifest> --run-label <label> --output-log docs/pilot_runs/YYYY-MM-DD-<label>.md
```

Use `2026-05-14-copied-photo-pilot-readiness-example.md` as the committed sanitized example for the 20-photo readiness pack. It is generated from `config/copied_photo_pilot_readiness_manifest.example.json` and intentionally includes only labels, counts, and go/no-go evidence.

After a private copied-photo run, score local accuracy with:

```powershell
python scripts/report-private-accuracy.py --manifest <private manifest> --results <private scoring results> --output-report docs/pilot_runs/YYYY-MM-DD-<label>-accuracy.md --json
```

The scoring results file is local-only. Commit the generated accuracy report only after confirming it contains aggregate counts, rates, thresholds, workload metrics, and failure taxonomy labels without raw field text or private paths.

Do not commit private source photos, private manifests, local absolute paths that reveal sensitive storage, generated workbooks, local databases, backup folders, or raw OCR/AI payloads from real lab photos.
