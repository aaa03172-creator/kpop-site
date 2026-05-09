from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from app import db
from app.main import MouseEventCreate, create_mouse_event, create_source_record


def seed_mouse(conn) -> None:
    conn.execute(
        """
        INSERT INTO mouse_master
            (mouse_id, display_id, raw_strain_text, status, last_verified_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("mouse_event_evidence", "EV318", "ApoM Tg/Tg", "active", "2026-05-09T00:00:00Z"),
    )


def test_high_risk_mouse_event_requires_evidence_before_canonical_commit(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            seed_mouse(conn)

        with pytest.raises(HTTPException) as exc_info:
            create_mouse_event(
                MouseEventCreate(
                    mouse_id="mouse_event_evidence",
                    event_type="death",
                    event_date="2026-05-09",
                    details={"observed_status": "found dead"},
                )
            )

        assert exc_info.value.status_code == 409
        assert "evidence" in str(exc_info.value.detail).lower()
        with db.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM mouse_event").fetchone()

        assert row["count"] == 0
    finally:
        db.DB_PATH = old_db_path


def test_high_risk_mouse_event_accepts_source_record_evidence(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            seed_mouse(conn)
            source_record_id = create_source_record(
                conn,
                source_type="manual_observation",
                source_label="Cage card death note",
                raw_payload="EV318 found dead on 2026-05-09",
            )

        result = create_mouse_event(
            MouseEventCreate(
                mouse_id="mouse_event_evidence",
                event_type="death",
                event_date="2026-05-09",
                source_record_id=source_record_id,
                details={"observed_status": "found dead"},
            )
        )

        with db.connection() as conn:
            row = conn.execute(
                "SELECT event_type, source_record_id, details FROM mouse_event WHERE event_id = ?",
                (result["event_id"],),
            ).fetchone()

        assert row["event_type"] == "death"
        assert row["source_record_id"] == source_record_id
        assert json.loads(row["details"])["observed_status"] == "found dead"
    finally:
        db.DB_PATH = old_db_path


def test_high_risk_mouse_event_accepts_photo_evidence_in_details(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            seed_mouse(conn)
            conn.execute(
                """
                INSERT INTO photo_log
                    (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "photo_event_evidence",
                    "death-card.jpg",
                    "data/photos/test/death-card.jpg",
                    "2026-05-09T01:00:00Z",
                    "review_pending",
                    "cage_card",
                ),
            )
            conn.execute(
                """
                INSERT INTO photo_evidence_item
                    (photo_evidence_id, source_photo_id, evidence_kind, observed_raw_text,
                     parsed_value, confidence, interpretation, needs_review, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evidence_death_note",
                    "photo_event_evidence",
                    "note_line",
                    "EV318 dead",
                    "death",
                    92,
                    "Death note visible on cage card",
                    0,
                    "approved",
                    "2026-05-09T01:05:00Z",
                    "2026-05-09T01:05:00Z",
                ),
            )

        result = create_mouse_event(
            MouseEventCreate(
                mouse_id="mouse_event_evidence",
                event_type="death",
                event_date="2026-05-09",
                details={
                    "source_photo_id": "photo_event_evidence",
                    "photo_evidence_id": "evidence_death_note",
                    "observed_status": "found dead",
                },
            )
        )

        with db.connection() as conn:
            row = conn.execute(
                "SELECT source_record_id, details FROM mouse_event WHERE event_id = ?",
                (result["event_id"],),
            ).fetchone()

        details = json.loads(row["details"])
        assert row["source_record_id"] is None
        assert details["source_photo_id"] == "photo_event_evidence"
        assert details["photo_evidence_id"] == "evidence_death_note"
    finally:
        db.DB_PATH = old_db_path
