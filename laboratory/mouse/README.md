# MouseDB

MouseDB is a CLI-first local tool for managing mouse strains, mouse individuals, cages, genotype results, matings, litters, and mouse event timelines.

It is designed as an independent tool. It should not hard-code PaperPipe integration. A future Research Assistant, API, or MCP server can call the same MouseDB service layer or stable CLI JSON output.

## Install

```powershell
python -m pip install -r requirements.txt
```

On this Windows workspace, the project-local virtual environment can be used directly:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m mousedb --help
```

## Database

By default MouseDB stores SQLite data at `data/mousedb.sqlite`.

Use a custom database path with either:

```powershell
$env:MOUSEDB_PATH = "C:\path\to\mousedb.sqlite"
```

or:

```powershell
python -m mousedb --db C:\path\to\mousedb.sqlite init
```

## Core Commands

```powershell
python -m mousedb init
python -m mousedb seed
python -m mousedb reset --yes

python -m mousedb strain add --name "PV-Cre" --background "C57BL/6J" --source "JAX"
python -m mousedb strain search "PV-Cre" --json
python -m mousedb strain show STR-0001 --json
python -m mousedb strain archive STR-0001 --json

python -m mousedb mouse add --display-id M0231 --strain STR-0001 --sex male --dob 2026-01-04 --cage C-014 --status available --use experimental --json
python -m mousedb mouse list --strain STR-0001 --json
python -m mousedb mouse show M-2026-0231 --json
python -m mousedb mouse timeline M-2026-0231 --json

python -m mousedb cage add --label C014 --location "Animal Room A" --rack R2 --shelf S3
python -m mousedb cage move-mouse --mouse M-2026-0231 --to C-014 --date 2026-03-12 --json

python -m mousedb genotype record --mouse M-2026-0231 --allele AL-0001 --result positive --zygosity heterozygous --date 2026-02-03 --json
python -m mousedb genotype list --mouse M-2026-0231 --json

python -m mousedb mating create --male M-2026-0101 --female M-2026-0102 --goal "PV-Cre" --start-date 2026-02-01 --status active --json
python -m mousedb litter create --mating MAT-2026-001 --birth-date 2026-03-01 --number-born 8 --json
python -m mousedb litter create-mice LIT-2026-001 --count 8 --strain STR-0001 --json
python -m mousedb litter wean LIT-2026-001 --date 2026-03-22 --json

python -m mousedb colony summary --json
python -m mousedb experiment-ready --strain STR-0001 --genotype "AL-0001:positive" --sex male --age-min-weeks 8 --json
```

Evidence and review commands:

```powershell
python -m mousedb source add --type manual_entry --label "Correction note" --raw-payload "M0232 sex female" --json
python -m mousedb review add --issue-type sex_uncertain --entity-type mouse --entity-id M-2026-0232 --source SRC-2026-0001 --raw-value unknown --suggested-value female --json
python -m mousedb correction apply --entity-type mouse --entity-id M-2026-0232 --field sex --value female --review REV-2026-0001 --source SRC-2026-0001 --reason "Reviewed cage card note" --json
python -m mousedb correction list --entity-type mouse --entity-id M-2026-0232 --json
```

## Demo Workflow

```powershell
python -m mousedb reset --yes --json
python -m mousedb seed --json
python -m mousedb strain search "PV-Cre" --json
python -m mousedb mouse add --display-id M0231 --strain STR-0001 --sex male --dob 2026-01-04 --cage C-014 --status available --use experimental --json
python -m mousedb genotype record --mouse M-2026-0231 --allele AL-0001 --result positive --zygosity heterozygous --date 2026-02-03 --json
python -m mousedb cage move-mouse --mouse M-2026-0231 --to C-014 --date 2026-03-12 --json
python -m mousedb mouse timeline M-2026-0231 --json
python -m mousedb experiment-ready --strain STR-0001 --genotype "AL-0001:positive" --sex male --age-min-weeks 8 --json
python -m mousedb colony summary --json
```

## Data Model Summary

Core canonical tables:

- `strain`
- `gene`
- `allele`
- `strain_allele`
- `mouse`
- `cage`
- `mating`
- `litter`
- `genotype_result`
- `mouse_event`
- `source_record`
- `review_item`
- `correction_log`

Mouse records stay lightweight and hold current state. Detailed history is stored in `mouse_event`. Genotype display summaries on Mouse are convenience values; structured `genotype_result` rows are the source of truth.

Corrections preserve before/after values in `correction_log`. When a correction changes a mouse record, MouseDB also writes a `correction_applied` event so the timeline remains auditable. Review resolution can include correction metadata so the resolved review, before/after values, and action log entry are recorded in one transaction.

Litter weaning updates generated offspring from `weaning_pending` to `alive` and writes a `weaned` event for each mouse, preserving the litter snapshot as the related entity.

## Integration Direction

MouseDB JSON output is an integration contract. Future PaperPipe or Research Assistant integration should call MouseDB as an independent tool through CLI, API, or MCP wrappers.

State-changing operations that update current mouse state also write event history in the same database transaction. Important records include traceability fields such as `source_type`, `source_ref`, `confidence`, and `reviewed_status`.

## Local Workbook Exports

The local FastAPI prototype exposes workbook-shaped previews and direct `.xlsx` downloads for the two current lab handoff formats:

- `GET /api/exports/separation.xlsx`: exports the current `분리 현황표` preview.
- `GET /api/exports/animal-sheet.xlsx`: exports the current `animal sheet` preview.

Both endpoints default to `require_ready=true`. Open review blockers return `409`, include a short blocker preview, and create a blocked export log entry instead of silently generating a risky file. Export preview also reports whether accepted data changed after the last generated export. After review blockers are resolved, downloads are generated from accepted structured state, not from Excel as the source of truth.

The browser UI has matching buttons: `Download Separation XLSX` and `Download Animal Sheet XLSX`.

## MVP Non-Goals

- No large web UI in this CLI package.
- No automatic genotype prediction.
- No breeding simulation.
- No barcode scanner integration.
- No hard-coded PaperPipe coupling.
- No destructive delete workflow for normal users; prefer archive/status changes.

## Test

```powershell
python -m pytest
```

The repository also keeps the browser prototype and local FastAPI scaffold checks wired through npm:

```powershell
npm test
npm run test:local
npm run test:mousedb
npm run verify
```

Use `npm run mousedb -- --help` as a convenient wrapper around `python -m mousedb`.
