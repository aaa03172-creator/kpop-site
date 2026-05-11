from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from app import db
from app.main import (
    LitterWeanCreate,
    MouseCageMove,
    MouseEventCreate,
    create_mouse_event,
    create_source_record,
    move_mouse_to_cage,
    wean_litter,
)


def seed_mouse(conn) -> None:
    conn.execute(
        """
        INSERT INTO mouse_master
            (mouse_id, display_id, raw_strain_text, status, last_verified_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("mouse_event_evidence", "EV318", "ApoM Tg/Tg", "active", "2026-05-09T00:00:00Z"),
    )


def seed_photo_note_evidence(conn) -> None:
    conn.execute(
        """
        INSERT INTO photo_log
            (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "photo_domain_event",
            "domain-event-card.jpg",
            "data/photos/test/domain-event-card.jpg",
            "2026-05-09T01:00:00Z",
            "review_pending",
            "cage_card_photo",
        ),
    )
    conn.execute(
        """
        INSERT INTO parse_result
            (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "parse_domain_event",
            "photo_domain_event",
            "manual_photo_transcription",
            "{}",
            "2026-05-09T01:01:00Z",
            "review",
            92,
            1,
        ),
    )
    conn.execute(
        """
        INSERT INTO card_note_item_log
            (note_item_id, photo_id, parse_id, card_type, line_number, raw_line_text,
             parsed_type, interpreted_status, parsed_mouse_display_id, confidence, needs_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "note_domain_event",
            "photo_domain_event",
            "parse_domain_event",
            "Separated",
            1,
            "EV318 moved/weaned",
            "mouse_item",
            "active",
            "EV318",
            92,
            0,
        ),
    )
    conn.execute(
        """
        INSERT INTO photo_evidence_item
            (photo_evidence_id, source_photo_id, parse_id, note_item_id, evidence_kind,
             observed_raw_text, parsed_value, confidence, interpretation, needs_review,
             status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "pe_domain_event",
            "photo_domain_event",
            "parse_domain_event",
            "note_domain_event",
            "note_line",
            "EV318 moved/weaned",
            "domain_event",
            92,
            "Reviewed cage-card note supports the domain event.",
            0,
            "accepted",
            "2026-05-09T01:02:00Z",
            "2026-05-09T01:02:00Z",
        ),
    )


def seed_mismatched_photo_evidence(conn) -> None:
    conn.execute(
        """
        INSERT INTO photo_log
            (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "photo_other_event",
            "other-event-card.jpg",
            "data/photos/test/other-event-card.jpg",
            "2026-05-09T01:03:00Z",
            "review_pending",
            "cage_card_photo",
        ),
    )
    conn.execute(
        """
        INSERT INTO photo_evidence_item
            (photo_evidence_id, source_photo_id, evidence_kind, observed_raw_text,
             parsed_value, confidence, interpretation, needs_review, status,
             created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "pe_other_event",
            "photo_other_event",
            "note_line",
            "Different note",
            "different_event",
            91,
            "Different source photo evidence.",
            0,
            "accepted",
            "2026-05-09T01:04:00Z",
            "2026-05-09T01:04:00Z",
        ),
    )


def seed_cage_move_state(conn) -> None:
    seed_mouse(conn)
    conn.execute(
        """
        INSERT INTO cage_registry
            (cage_id, cage_label, created_at, updated_at)
        VALUES (?, ?, ?, ?), (?, ?, ?, ?)
        """,
        (
            "cage_old",
            "Old cage",
            "2026-05-09T00:00:00Z",
            "2026-05-09T00:00:00Z",
            "cage_new",
            "New cage",
            "2026-05-09T00:00:00Z",
            "2026-05-09T00:00:00Z",
        ),
    )
    conn.execute(
        """
        INSERT INTO mouse_cage_assignment
            (assignment_id, mouse_id, cage_id, status, assigned_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("assignment_old", "mouse_event_evidence", "cage_old", "active", "2026-05-09T00:00:00Z"),
    )


def seed_litter_wean_state(conn) -> None:
    seed_mouse(conn)
    conn.execute(
        """
        INSERT INTO mating_registry
            (mating_id, mating_label, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        ("mating_event_evidence", "Mating evidence", "2026-05-09T00:00:00Z", "2026-05-09T00:00:00Z"),
    )
    conn.execute(
        """
        INSERT INTO litter_registry
            (litter_id, litter_label, mating_id, birth_date, number_born,
             number_alive, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "litter_event_evidence",
            "Litter evidence",
            "mating_event_evidence",
            "2026-04-20",
            1,
            1,
            "pre_weaning",
            "2026-05-09T00:00:00Z",
            "2026-05-09T00:00:00Z",
        ),
    )
    conn.execute(
        """
        UPDATE mouse_master
        SET litter_id = ?, status = ?, next_action = ?
        WHERE mouse_id = ?
        """,
        ("litter_event_evidence", "weaning_pending", "weaning_due", "mouse_event_evidence"),
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


def test_cage_move_preserves_specific_photo_note_evidence_refs(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            seed_cage_move_state(conn)
            seed_photo_note_evidence(conn)

        result = move_mouse_to_cage(
            "mouse_event_evidence",
            MouseCageMove(
                cage_id="cage_new",
                note="Reviewed cage-card movement note.",
                moved_at="2026-05-09T02:00:00Z",
                source_photo_id="photo_domain_event",
                source_note_item_id="note_domain_event",
                photo_evidence_id="pe_domain_event",
            ),
        )

        with db.connection() as conn:
            event = conn.execute(
                """
                SELECT source_record_id, details
                FROM mouse_event
                WHERE event_type = 'moved'
                  AND mouse_id = ?
                """,
                ("mouse_event_evidence",),
            ).fetchone()

        details = json.loads(event["details"])
        assert result["source_record_id"] == event["source_record_id"]
        assert details["source_photo_id"] == "photo_domain_event"
        assert details["source_note_item_id"] == "note_domain_event"
        assert details["photo_evidence_id"] == "pe_domain_event"
    finally:
        db.DB_PATH = old_db_path


def test_cage_move_rejects_invalid_evidence_ref_before_partial_write(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            seed_cage_move_state(conn)

        with pytest.raises(HTTPException) as exc_info:
            move_mouse_to_cage(
                "mouse_event_evidence",
                MouseCageMove(
                    cage_id="cage_new",
                    note="Invalid evidence should block the move.",
                    source_photo_id="photo_missing",
                ),
            )

        assert exc_info.value.status_code == 400
        with db.connection() as conn:
            active_assignment = conn.execute(
                """
                SELECT cage_id
                FROM mouse_cage_assignment
                WHERE mouse_id = ?
                  AND status = 'active'
                """,
                ("mouse_event_evidence",),
            ).fetchone()
            event_count = conn.execute("SELECT COUNT(*) AS count FROM mouse_event").fetchone()["count"]
            source_count = conn.execute("SELECT COUNT(*) AS count FROM source_record").fetchone()["count"]

        assert active_assignment["cage_id"] == "cage_old"
        assert event_count == 0
        assert source_count == 0
    finally:
        db.DB_PATH = old_db_path


def test_domain_event_rejects_mismatched_photo_evidence_trace(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            seed_cage_move_state(conn)
            seed_photo_note_evidence(conn)
            seed_mismatched_photo_evidence(conn)

        with pytest.raises(HTTPException) as exc_info:
            move_mouse_to_cage(
                "mouse_event_evidence",
                MouseCageMove(
                    cage_id="cage_new",
                    source_photo_id="photo_domain_event",
                    source_note_item_id="note_domain_event",
                    photo_evidence_id="pe_other_event",
                ),
            )

        assert exc_info.value.status_code == 400
        assert "does not match" in str(exc_info.value.detail)
        with db.connection() as conn:
            event_count = conn.execute("SELECT COUNT(*) AS count FROM mouse_event").fetchone()["count"]
            active_assignment = conn.execute(
                """
                SELECT cage_id
                FROM mouse_cage_assignment
                WHERE mouse_id = ?
                  AND status = 'active'
                """,
                ("mouse_event_evidence",),
            ).fetchone()

        assert event_count == 0
        assert active_assignment["cage_id"] == "cage_old"
    finally:
        db.DB_PATH = old_db_path


def test_weaning_preserves_specific_photo_note_evidence_refs(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            seed_litter_wean_state(conn)
            seed_photo_note_evidence(conn)

        wean_litter(
            "litter_event_evidence",
            LitterWeanCreate(
                weaning_date="2026-05-09",
                number_weaned=1,
                note="Reviewed cage-card weaning note.",
                source_photo_id="photo_domain_event",
                source_note_item_id="note_domain_event",
                photo_evidence_id="pe_domain_event",
            ),
        )

        with db.connection() as conn:
            event = conn.execute(
                """
                SELECT details
                FROM mouse_event
                WHERE event_type = 'weaned'
                  AND related_entity_id = ?
                """,
                ("litter_event_evidence",),
            ).fetchone()

        details = json.loads(event["details"])
        assert details["source_photo_id"] == "photo_domain_event"
        assert details["source_note_item_id"] == "note_domain_event"
        assert details["photo_evidence_id"] == "pe_domain_event"
    finally:
        db.DB_PATH = old_db_path


def test_weaning_rejects_invalid_evidence_ref_before_partial_write(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            seed_litter_wean_state(conn)

        with pytest.raises(HTTPException) as exc_info:
            wean_litter(
                "litter_event_evidence",
                LitterWeanCreate(
                    weaning_date="2026-05-09",
                    number_weaned=1,
                    source_note_item_id="note_missing",
                ),
            )

        assert exc_info.value.status_code == 400
        with db.connection() as conn:
            litter = conn.execute(
                "SELECT status, number_weaned, weaning_date FROM litter_registry WHERE litter_id = ?",
                ("litter_event_evidence",),
            ).fetchone()
            mouse = conn.execute(
                "SELECT status, next_action FROM mouse_master WHERE mouse_id = ?",
                ("mouse_event_evidence",),
            ).fetchone()
            event_count = conn.execute("SELECT COUNT(*) AS count FROM mouse_event").fetchone()["count"]
            source_count = conn.execute("SELECT COUNT(*) AS count FROM source_record").fetchone()["count"]

        assert dict(litter) == {"status": "pre_weaning", "number_weaned": None, "weaning_date": ""}
        assert dict(mouse) == {"status": "weaning_pending", "next_action": "weaning_due"}
        assert event_count == 0
        assert source_count == 0
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
