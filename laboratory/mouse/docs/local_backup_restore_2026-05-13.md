# Local Backup And Restore - 2026-05-13

Layer classification: export or view / local operational procedure.

Canonical: false.

This procedure protects local pilot work. It is not a canonical archive policy, not a replacement for institutional backup rules, and not permission to treat the local MVP as the lab's only source of truth.

## What Gets Backed Up

| Path | Boundary | Reason |
| --- | --- | --- |
| `data/mouse_lims.sqlite` | canonical structured state / local pilot copy | Local accepted state, review queue, action log, export log, and source references. |
| `data/photos/` | raw source / local pilot copy | Copied cage-card source photos uploaded to the local pilot. |
| `data/exports/` | export or view / local pilot copy | Generated CSV/XLSX outputs. |
| `mousedb_artifacts/` | export or view / local pilot copy | Proposed changesets, validation reports, export manifests, and preview artifacts. |

Missing paths are reported in the backup manifest rather than treated as fatal. This allows a dry run before any photos or exports exist.

## Backup

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup-local-pilot.ps1 -Label before-first-pilot
```

By default the backup is written outside Git under:

```text
%LOCALAPPDATA%\MouseDB\pilot-backups\<timestamp>-<label>
```

The script writes `backup-manifest.json` with:

- data boundary: `export or view`
- `canonical=false`
- project root
- backup path
- copied paths
- missing paths
- a restore command template

## Restore

Restore refuses to overwrite an existing target unless `-Force` is provided.

Safe preview of the refusal behavior:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/restore-local-pilot.ps1 -BackupPath "C:\path\to\backup" -TargetRoot "C:\path\to\restore-target"
```

Force restore after confirming the target can be overwritten:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/restore-local-pilot.ps1 -BackupPath "C:\path\to\backup" -TargetRoot "C:\path\to\restore-target" -Force
```

## Restore Drill

Before any real pilot:

1. Create a copied pilot workspace or empty temporary target outside Git.
2. Run `scripts/backup-local-pilot.ps1`.
3. Run `scripts/restore-local-pilot.ps1` without `-Force` against a target that already contains data and confirm it refuses to overwrite.
4. Run the restore with `-Force` against a disposable target.
5. Confirm `data/mouse_lims.sqlite`, `data/photos/`, `data/exports/`, and `mousedb_artifacts/` are restored when present in the backup.
6. Run the relevant verification command after restore, such as `npm run test:real-photo-pilot` for the manifest harness or the full baseline gate before a real pilot.

## Git Hygiene

Backups are generated local operational artifacts. Do not commit backup folders, private source photos, copied pilot manifests with private paths, or restored runtime data.

