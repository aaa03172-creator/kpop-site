from __future__ import annotations

from pathlib import Path

import pytest

from app import db
from app.main import rebuild_search_index, search_index_available, search_index_hits


def test_search_index_finds_review_and_note_evidence(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            if not search_index_available(conn):
                pytest.skip("SQLite FTS5 is not available in this Python build.")
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("parse_test", None, "unit_fixture", "{}", "2026-05-04T00:00:00Z", "review", 0.7, 1),
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value,
                     suggested_value, review_reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_test",
                    "parse_test",
                    "Medium",
                    "Assigned strain fuzzy match needs review",
                    "GFAP Cre S1PR1 flox",
                    "Review suggested assigned strain: GFAP Cre; S1PR1 fl/fl",
                    "RapidFuzz suggestion should stay reviewable.",
                    "open",
                    "2026-05-04T00:00:01Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO card_note_item_log
                    (note_item_id, parse_id, raw_line_text, parsed_type,
                     interpreted_status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("note_test", "parse_test", "MT321 R0 ambiguous ear label", "mouse_item", "active", 0.6, 1),
            )

            assert rebuild_search_index(conn) is True
            review_hits = search_index_hits(conn, "RapidFuzz")
            note_hits = search_index_hits(conn, "R0 ambiguous")

        assert any(hit["entity_type"] == "review" and hit["entity_id"] == "review_test" for hit in review_hits)
        assert any(hit["entity_type"] == "note_line" and hit["entity_id"] == "note_test" for hit in note_hits)
    finally:
        db.DB_PATH = old_db_path
