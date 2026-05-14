# Tauri Desktop Sidecar Design

Layer classification: adopted documentation.

Canonical: false. This document defines the desktop packaging path, not colony state, review records, raw source records, or export contents.

## Goal

Convert the local MouseDB FastAPI/static web app into a Windows-friendly Tauri desktop path for an internal installable MVP. The desktop app should start the existing FastAPI app as a bundled Python sidecar, open the existing UI in a native Tauri window, and keep raw photos, workbook imports, SQLite data, exports, and generated artifacts outside the application bundle.

## Architecture

MouseDB remains a FastAPI application that serves `static/index.html` and all existing `/api/*` routes. Tauri is a desktop shell and process supervisor. It starts a PyInstaller-built sidecar named `mousedb-server`, passes a localhost host/port and desktop data directory, waits for `/api/health`, and loads `http://127.0.0.1:8765`.

The sidecar owns no canonical logic beyond startup. Existing review gates, raw/parsed/canonical boundaries, evidence traceability, and Excel export blockers remain in the FastAPI service layer and committed tests.

## Data Boundaries

Desktop runtime files are stored under an app data root, not inside `src-tauri`, the installer, or the PyInstaller unpack directory.

| Artifact | Layer | Desktop location rule |
| --- | --- | --- |
| Uploaded cage-card photos | raw source | `data/photos/` below the app data root |
| Uploaded legacy workbooks | raw source / export or view input | `data/legacy_workbooks/` below the app data root |
| SQLite database | canonical structured state plus review/export records | `data/mouse_lims.sqlite` below the app data root |
| ROI crops | cache | `data/roi/` below the app data root |
| Generated Excel files | export or view | `data/exports/` below the app data root |
| Proposed changesets, validation reports, export manifests | export or view | `mousedb_artifacts/` below the app data root |

## Packaging

PyInstaller builds `desktop/server.py` into a Windows console-free sidecar executable. The build script copies it to `src-tauri/binaries/mousedb-server-<target-triple>.exe`, matching Tauri's external binary naming rule.

Tauri v2 uses `src-tauri/tauri.conf.json` with `bundle.externalBin` set to `binaries/mousedb-server`. The Rust entrypoint uses `tauri-plugin-shell` to spawn the sidecar with explicit arguments. The sidecar sets `MOUSEDB_DATA_DIR` and `MOUSEDB_ARTIFACT_ROOT` before importing the FastAPI app.

## Error Handling

If the sidecar cannot start or `/api/health` does not become ready, the Tauri app exits with a clear startup error in logs rather than writing partial desktop state. The sidecar reuses FastAPI database transactions, so existing partial-write and review-gate protections remain authoritative.

Port `8765` is the first internal MVP port because `start.bat` already uses it. If a later pilot needs concurrent local app instances, the next slice should add dynamic port selection and programmatic window creation.

## Verification

Desktop-specific verification checks:

- `tests/test_desktop_packaging.py` confirms environment-driven data/artifact paths and Tauri sidecar configuration.
- `npm run test:desktop-config` validates the Tauri/PyInstaller scaffold without requiring Rust.
- `npm run build:desktop-sidecar` builds the sidecar when PyInstaller is installed.
- `npm run tauri:build` builds the Windows installer when Rust/Cargo and the Tauri prerequisites are installed.

Existing safety verification remains required before treating the desktop MVP as pilot-ready:

- `npm run test:local`
- `npm run test:browser-photo-export-e2e`
- `npm run test:synthetic-draft-extraction`
- `npm run test:cage-card-skill-gym`
- `python -m pytest tests`

## Current Environment Note

This workspace currently has Node/npm but not Rust/Cargo or PyInstaller on PATH. The implementation can add and verify the desktop scaffold, sidecar entrypoint, path behavior, and configuration tests here. Producing the final Windows installer requires installing Rust and PyInstaller dependencies.
