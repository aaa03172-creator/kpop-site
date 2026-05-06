from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi import HTTPException

from app import db
from app.main import ROOT, ai_transcription_image_content


def test_ai_image_content_does_not_send_unreadable_full_photo_fallback(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    photo_id = "corrupt_photo"
    photo_dir = ROOT / "data" / "photos" / "test_ai_payload_minimization"
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        photo_dir.mkdir(parents=True, exist_ok=True)
        photo_path = photo_dir / "corrupt-card.jpg"
        photo_path.write_bytes(b"not a readable image")
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    photo_id,
                    "corrupt-card.jpg",
                    str(photo_path.relative_to(ROOT)),
                    "2026-05-04T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )

        with pytest.raises(HTTPException) as error:
            ai_transcription_image_content(photo_id, photo_path, "image/jpeg", "low")

        assert error.value.status_code == 415
        assert "ROI crop generation is required" in str(error.value.detail)
    finally:
        db.DB_PATH = old_db_path
        shutil.rmtree(photo_dir, ignore_errors=True)
