from __future__ import annotations

from pathlib import Path

import pytest

from app import db
from app import main as app_main
from app.main import PhotoManualTranscriptionCreate


def table_count(table_name: str) -> int:
    with db.connection() as conn:
        return int(conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()["count"])


def test_manual_transcription_failure_rolls_back_partial_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_txn",
                    "txn-card.jpg",
                    "data/photos/test/txn-card.jpg",
                    "2026-05-04T00:00:00Z",
                    "review_pending",
                    "cage_card_photo",
                ),
            )

        def fail_after_snapshot(*args, **kwargs):
            raise RuntimeError("forced note write failure")

        monkeypatch.setattr(app_main, "write_note_items_and_mouse_candidates", fail_after_snapshot)

        with pytest.raises(RuntimeError):
            app_main.create_photo_manual_transcription(
                "photo_txn",
                PhotoManualTranscriptionCreate(
                    card_type="Separated",
                    raw_strain="ApoM Tg/Tg",
                    sex_raw="F",
                    mouse_count="2 total",
                    notes=[{"raw": "MT401 R'", "meaning": "mouse", "strike": "none"}],
                ),
            )

        assert table_count("photo_log") == 1
        assert table_count("parse_result") == 0
        assert table_count("card_snapshot") == 0
        assert table_count("card_note_item_log") == 0
        assert table_count("review_queue") == 0
        assert table_count("action_log") == 0
    finally:
        db.DB_PATH = old_db_path
