from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_python_snippet(code: str, env: dict[str, str]) -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={**os.environ, **env},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_desktop_server_resolves_runtime_paths(tmp_path: Path) -> None:
    from desktop.server import resolve_runtime_paths

    paths = resolve_runtime_paths(tmp_path / "MouseDB")

    assert paths.app_home == tmp_path / "MouseDB"
    assert paths.data_dir == tmp_path / "MouseDB" / "data"
    assert paths.db_path == tmp_path / "MouseDB" / "data" / "mouse_lims.sqlite"
    assert paths.artifact_root == tmp_path / "MouseDB" / "mousedb_artifacts"


def test_desktop_server_script_keeps_repo_root_importable() -> None:
    payload = run_python_snippet(
        """
import importlib.util
import json
import sys
from pathlib import Path

script = Path("desktop/server.py").resolve()
repo_root = Path.cwd().resolve()
sys.path = [str(script.parent)] + [
    item for item in sys.path if item not in ("", str(repo_root))
]

spec = importlib.util.spec_from_file_location("desktop_server_entrypoint", script)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)

import app.main as app_main

print(json.dumps({
    "root_on_path": str(repo_root) in sys.path,
    "has_fastapi_app": hasattr(app_main, "app"),
}))
""",
        {},
    )

    assert payload == {"root_on_path": True, "has_fastapi_app": True}


def test_fastapi_app_uses_desktop_runtime_paths_from_environment(tmp_path: Path) -> None:
    app_home = tmp_path / "MouseDB"
    payload = run_python_snippet(
        """
import json
from app import db
import app.main as app_main
print(json.dumps({
    "data_dir": str(db.DATA_DIR),
    "db_path": str(db.DB_PATH),
    "artifact_root": str(app_main.ARTIFACT_ROOT),
}))
""",
        {
            "MOUSEDB_DATA_DIR": str(app_home / "data"),
            "MOUSEDB_DB_PATH": str(app_home / "data" / "mouse_lims.sqlite"),
            "MOUSEDB_ARTIFACT_ROOT": str(app_home / "mousedb_artifacts"),
        },
    )

    assert Path(payload["data_dir"]) == app_home / "data"
    assert Path(payload["db_path"]) == app_home / "data" / "mouse_lims.sqlite"
    assert Path(payload["artifact_root"]) == app_home / "mousedb_artifacts"


def test_desktop_runtime_data_dirs_cover_raw_sources_and_exports(tmp_path: Path) -> None:
    payload = run_python_snippet(
        """
import json
from pathlib import Path
from app import db

db.ensure_data_dirs()
print(json.dumps({
    "db_parent": Path(db.DB_PATH).parent.exists(),
    "photos": (db.DATA_DIR / "photos").is_dir(),
    "legacy_workbooks": (db.DATA_DIR / "legacy_workbooks").is_dir(),
    "exports": (db.DATA_DIR / "exports").is_dir(),
    "roi": (db.DATA_DIR / "roi").is_dir(),
}))
""",
        {
            "MOUSEDB_DATA_DIR": str(tmp_path / "MouseDB" / "data"),
            "MOUSEDB_DB_PATH": str(tmp_path / "MouseDB" / "custom-db" / "mouse_lims.sqlite"),
        },
    )

    assert payload == {
        "db_parent": True,
        "photos": True,
        "legacy_workbooks": True,
        "exports": True,
        "roi": True,
    }


def test_tauri_sidecar_configuration_is_present() -> None:
    tauri_config_path = ROOT / "src-tauri" / "tauri.conf.json"
    cargo_manifest_path = ROOT / "src-tauri" / "Cargo.toml"
    rust_entrypoint_path = ROOT / "src-tauri" / "src" / "main.rs"
    capability_path = ROOT / "src-tauri" / "capabilities" / "default.json"

    assert tauri_config_path.exists()
    assert cargo_manifest_path.exists()
    assert rust_entrypoint_path.exists()
    assert capability_path.exists()

    config = json.loads(tauri_config_path.read_text(encoding="utf-8"))
    assert config["build"]["frontendDist"] == "http://127.0.0.1:8765"
    assert config["build"]["devUrl"] == "http://127.0.0.1:8765"
    assert "binaries/mousedb-server" in config["bundle"]["externalBin"]

    rust_entrypoint = rust_entrypoint_path.read_text(encoding="utf-8")
    assert 'sidecar("mousedb-server")' in rust_entrypoint
    assert "--data-dir" in rust_entrypoint
    assert "/api/health" in rust_entrypoint

    capability = json.loads(capability_path.read_text(encoding="utf-8"))
    assert "core:default" in capability["permissions"]


def test_desktop_build_scripts_are_registered() -> None:
    package_json = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package_json["scripts"]

    assert scripts["test:desktop-config"] == "python -m pytest tests/test_desktop_packaging.py -q"
    assert scripts["build:desktop-sidecar"] == "powershell -ExecutionPolicy Bypass -File scripts/build-desktop-sidecar.ps1"
    assert scripts["tauri:dev"] == "tauri dev"
    assert scripts["tauri:build"] == "npm run build:desktop-sidecar && tauri build"

    build_script = ROOT / "scripts" / "build-desktop-sidecar.ps1"
    pyinstaller_spec = ROOT / "desktop" / "pyinstaller" / "mousedb-server.spec"
    assert build_script.exists()
    assert pyinstaller_spec.exists()

    build_text = build_script.read_text(encoding="utf-8")
    assert "rustc --print host-tuple" in build_text
    assert "mousedb-server-" in build_text
    assert "src-tauri" in build_text


def test_desktop_server_uses_console_safe_uvicorn_logging() -> None:
    server_text = (ROOT / "desktop" / "server.py").read_text(encoding="utf-8")

    assert "log_config=None" in server_text
