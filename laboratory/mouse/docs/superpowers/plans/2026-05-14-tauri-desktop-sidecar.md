# Tauri Desktop Sidecar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Windows-friendly Tauri desktop path that bundles MouseDB's FastAPI app as a PyInstaller sidecar while keeping lab evidence and exports in runtime app data folders.

**Architecture:** Keep FastAPI and the existing static UI as the product surface. Add a Python sidecar entrypoint for desktop startup, environment-driven runtime paths, a Tauri v2 shell that supervises the sidecar, and verification scripts that can run before Rust is installed.

**Tech Stack:** Python, FastAPI, PyInstaller, Tauri v2, Rust, PowerShell, npm scripts, pytest.

---

### Task 1: Desktop Runtime Path Contract

**Files:**
- Modify: `app/db.py`
- Modify: `app/main.py`
- Create: `desktop/server.py`
- Test: `tests/test_desktop_packaging.py`

- [ ] **Step 1: Write failing tests**

Add tests that import the desktop server helpers, verify `MOUSEDB_DATA_DIR` controls `app.db.DATA_DIR`, verify `MOUSEDB_DB_PATH` controls `app.db.DB_PATH`, and verify `MOUSEDB_ARTIFACT_ROOT` controls `app.main.ARTIFACT_ROOT`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_desktop_packaging.py -q`

Expected: fail because `desktop.server` and env-driven app paths do not exist yet.

- [ ] **Step 3: Implement minimal path support**

Add environment-aware path initialization in `app/db.py`, environment-aware artifact root initialization in `app/main.py`, and a desktop sidecar helper in `desktop/server.py` that sets runtime env vars before importing `app.main`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_desktop_packaging.py -q`

Expected: pass.

### Task 2: Sidecar Build Scaffold

**Files:**
- Create: `desktop/pyinstaller/mousedb-server.spec`
- Create: `scripts/build-desktop-sidecar.ps1`
- Modify: `requirements.txt`
- Modify: `package.json`
- Test: `tests/test_desktop_packaging.py`

- [ ] **Step 1: Extend failing tests**

Add tests that require the PyInstaller spec, PowerShell build script, and npm scripts for `build:desktop-sidecar` and `test:desktop-config`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_desktop_packaging.py -q`

Expected: fail on missing build scaffold.

- [ ] **Step 3: Implement sidecar build scaffold**

Add the PyInstaller spec, add a PowerShell script that installs PyInstaller when needed and copies `mousedb-server.exe` to `src-tauri/binaries/mousedb-server-<target-triple>.exe`, add the package scripts, and add PyInstaller to the Python requirements.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_desktop_packaging.py -q`

Expected: pass.

### Task 3: Tauri Shell Scaffold

**Files:**
- Create: `src-tauri/Cargo.toml`
- Create: `src-tauri/build.rs`
- Create: `src-tauri/tauri.conf.json`
- Create: `src-tauri/capabilities/default.json`
- Create: `src-tauri/src/main.rs`
- Modify: `package.json`
- Test: `tests/test_desktop_packaging.py`

- [ ] **Step 1: Extend failing tests**

Add tests that require `bundle.externalBin` to include `binaries/mousedb-server`, require Tauri scripts in `package.json`, and inspect the Rust entrypoint for `sidecar("mousedb-server")`, `--data-dir`, and `/api/health`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_desktop_packaging.py -q`

Expected: fail on missing Tauri files.

- [ ] **Step 3: Implement Tauri scaffold**

Add the Tauri v2 Rust crate, configuration, shell capability, and startup logic that spawns the sidecar and waits for health readiness.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_desktop_packaging.py -q`

Expected: pass.

### Task 4: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/pilot_readiness_baseline_2026-05-13.md` only if needed for ignored runtime-artifact guidance.

- [ ] **Step 1: Document commands**

Document `npm run test:desktop-config`, `npm run build:desktop-sidecar`, `npm run tauri:dev`, and `npm run tauri:build`, including the Rust/Cargo prerequisite.

- [ ] **Step 2: Run focused verification**

Run: `python -m pytest tests/test_desktop_packaging.py -q`

Expected: pass.

Run: `npm run test:desktop-config`

Expected: pass.

Run: `npm run test:local`

Expected: pass.

- [ ] **Step 3: Re-check worktree**

Run: `git status --short`

Expected: only task source/docs are changed; generated artifacts such as `src-tauri/binaries/`, `build/`, and `dist/` stay untracked or ignored.
