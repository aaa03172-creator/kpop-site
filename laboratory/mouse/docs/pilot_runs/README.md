# Pilot Runs

Layer classification: review item / pilot run log index.

Canonical: false.

Store sanitized pilot run logs here after synthetic or copied non-production dry runs. Use `docs/pilot_run_log_template_2026-05-13.md` as the starting point, or generate a prefilled copied-photo shell with:

```powershell
python scripts/prepare-copied-pilot-run.py --manifest <private manifest> --run-label <label> --output-log docs/pilot_runs/YYYY-MM-DD-<label>.md
```

Do not commit private source photos, private manifests, local absolute paths that reveal sensitive storage, generated workbooks, local databases, backup folders, or raw OCR/AI payloads from real lab photos.
