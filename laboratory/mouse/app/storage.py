from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from .db import DATA_DIR, ensure_data_dirs


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix and len(suffix) <= 10:
        return suffix
    return ".bin"


def save_upload(file: UploadFile, photo_id: str) -> Path:
    ensure_data_dirs()
    day = datetime.now().strftime("%Y%m%d")
    target_dir = DATA_DIR / "photos" / day
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{photo_id}{safe_suffix(file.filename or '')}"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return target
