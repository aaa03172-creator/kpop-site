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

python -m mousedb colony summary --json
python -m mousedb experiment-ready --strain STR-0001 --genotype "AL-0001:positive" --sex male --age-min-weeks 8 --json
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

Mouse records stay lightweight and hold current state. Detailed history is stored in `mouse_event`. Genotype display summaries on Mouse are convenience values; structured `genotype_result` rows are the source of truth.

## Integration Direction

MouseDB JSON output is an integration contract. Future PaperPipe or Research Assistant integration should call MouseDB as an independent tool through CLI, API, or MCP wrappers.

State-changing operations that update current mouse state also write event history in the same database transaction. Important records include traceability fields such as `source_type`, `source_ref`, `confidence`, and `reviewed_status`.

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
