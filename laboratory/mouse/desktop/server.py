from __future__ import annotations

import argparse
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import uvicorn


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class RuntimePaths:
    app_home: Path
    data_dir: Path
    db_path: Path
    artifact_root: Path


def default_app_home() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "MouseDB"
    return Path.home() / "AppData" / "Local" / "MouseDB"


def resolve_runtime_paths(
    app_home: Path | str | None = None,
    data_dir: Path | str | None = None,
    db_path: Path | str | None = None,
    artifact_root: Path | str | None = None,
) -> RuntimePaths:
    resolved_home = Path(app_home).expanduser().resolve() if app_home else default_app_home().resolve()
    resolved_data_dir = Path(data_dir).expanduser().resolve() if data_dir else resolved_home / "data"
    resolved_db_path = Path(db_path).expanduser().resolve() if db_path else resolved_data_dir / "mouse_lims.sqlite"
    resolved_artifact_root = (
        Path(artifact_root).expanduser().resolve() if artifact_root else resolved_home / "mousedb_artifacts"
    )
    return RuntimePaths(
        app_home=resolved_home,
        data_dir=resolved_data_dir,
        db_path=resolved_db_path,
        artifact_root=resolved_artifact_root,
    )


def configure_environment(paths: RuntimePaths) -> None:
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.artifact_root.mkdir(parents=True, exist_ok=True)
    os.environ["MOUSEDB_DATA_DIR"] = str(paths.data_dir)
    os.environ["MOUSEDB_DB_PATH"] = str(paths.db_path)
    os.environ["MOUSEDB_ARTIFACT_ROOT"] = str(paths.artifact_root)


def write_startup_log(paths: RuntimePaths, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log_path = paths.artifact_root / "desktop-startup.log"
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} {message}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MouseDB FastAPI app as a desktop sidecar.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--app-home", default="")
    parser.add_argument("--data-dir", default="")
    parser.add_argument("--db-path", default="")
    parser.add_argument("--artifact-root", default="")
    parser.add_argument("--log-level", default="warning")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = resolve_runtime_paths(
        app_home=args.app_home or None,
        data_dir=args.data_dir or None,
        db_path=args.db_path or None,
        artifact_root=args.artifact_root or None,
    )
    configure_environment(paths)
    write_startup_log(paths, f"configured data_dir={paths.data_dir} artifact_root={paths.artifact_root}")

    try:
        write_startup_log(paths, "importing FastAPI app")
        from app.main import app

        write_startup_log(paths, f"starting uvicorn host={args.host} port={args.port}")
    except Exception:
        write_startup_log(paths, traceback.format_exc())
        raise

    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level, log_config=None)
        write_startup_log(paths, "uvicorn stopped")
    except BaseException:
        write_startup_log(paths, traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
