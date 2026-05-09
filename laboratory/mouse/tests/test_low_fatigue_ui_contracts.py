from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app import db
from app.main import app, create_card_snapshot, write_note_items_and_mouse_candidates


def seed_focus_review_card(tmp_path: Path) -> None:
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    db.init_db()
    photo_id = "photo_focus_review"
    parse_id = "parse_focus_review"
    created_at = "2026-05-09T10:17:00Z"
    record = {
        "type": "Separated",
        "rawStrain": "C57BL/6J",
        "matchedStrain": "C57BL/6J",
        "sexRaw": "mixed",
        "dobRaw": "2025-02-10",
        "mouseCount": "3 total",
        "confidence": 82,
        "notes": [
            {"raw": "MT318 R'", "strike": "none"},
            {"raw": "MT319 L'", "strike": "none"},
            {"raw": "MT320", "strike": "none"},
        ],
    }
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO photo_log
                (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                photo_id,
                "focus-review-card.jpg",
                "data/photos/test/focus-review-card.jpg",
                "2026-05-09T10:15:30Z",
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
                parse_id,
                photo_id,
                "manual_photo_transcription",
                json.dumps(record, ensure_ascii=False),
                created_at,
                "review",
                82,
                1,
            ),
        )
        snapshot_id = create_card_snapshot(conn, parse_id, photo_id, record, created_at)
        write_note_items_and_mouse_candidates(conn, parse_id, {**record, "cardSnapshotId": snapshot_id}, "review")
        conn.execute(
            """
            INSERT INTO review_queue
                (review_id, parse_id, severity, issue, current_value,
                 suggested_value, review_reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "review_duplicate_mt319",
                parse_id,
                "High",
                "Duplicate active mouse",
                "MT319 active in two card snapshots",
                "Resolve duplicate active mouse before export.",
                "MT319 appears to duplicate an existing active mouse. Review before canonical apply.",
                "open",
                "2026-05-09T10:18:00Z",
            ),
        )
        conn.execute(
            """
            INSERT INTO review_queue
                (review_id, parse_id, severity, issue, current_value,
                 suggested_value, review_reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "review_unlabeled_numeric_parse_focus_review",
                parse_id,
                "Medium",
                "Unlabeled numeric note needs review",
                "MT320",
                "Confirm note-line interpretation.",
                "Needs quick confirmation from source photo.",
                "open",
                "2026-05-09T10:19:00Z",
            ),
        )


def test_focus_review_groups_db_backed_review_items_by_photo_card(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        seed_focus_review_card(tmp_path)
        client = TestClient(app)

        response = client.get("/api/ui/focus-review")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_layer"] == "export or view"
        assert payload["workload_summary"]["must_review"] == 1
        assert payload["workload_summary"]["quick_check"] >= 1
        assert payload["empty_state"]["fabricated_records"] is False
        [card] = payload["cards"]
        assert card["source_photo"]["photo_id"] == "photo_focus_review"
        assert card["source_photo"]["source_photo_role"] == "primary_evidence"
        assert card["source_photo"]["open_source_photo_label"] == "Open source photo"
        assert card["card_snapshot"]["card_type"] == "Separated"
        assert card["review_count"] >= 2
        review_ids = {item["review_id"] for item in card["review_items"]}
        assert {"review_duplicate_mt319", "review_unlabeled_numeric_parse_focus_review"}.issubset(review_ids)
        assert any(item["attention_level"] == "must_review" for item in card["review_items"])
        assert any(item["attention_level"] == "quick_check" for item in card["review_items"])
        duplicate_item = next(item for item in card["review_items"] if item["review_id"] == "review_duplicate_mt319")
        quick_item = next(item for item in card["review_items"] if item["review_id"] == "review_unlabeled_numeric_parse_focus_review")
        assert duplicate_item["action_hint"] == {
            "source_layer": "export or view",
            "mode": "manual_review_required",
            "primary_label": "Inspect source evidence",
            "requires_note": True,
            "requires_source_photo": True,
            "safe_quick_resolve": False,
        }
        assert quick_item["action_hint"]["mode"] == "manual_review_required"
        assert quick_item["action_hint"]["safe_quick_resolve"] is False
        assert quick_item["action_hint"]["requires_note"] is True
        assert [row["mouse_id"] for row in card["mouse_rows"]] == ["MT318", "MT319"]
        assert card["collapsed_sections"]["note_lines"] == 2
        assert card["collapsed_sections"]["evidence"] >= 1
        assert card["actions"] == ["Apply confirmed rows only", "Hold card", "Open source photo"]
    finally:
        db.DB_PATH = old_db_path


def test_focus_review_empty_state_does_not_fabricate_colony_data(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()
        client = TestClient(app)

        response = client.get("/api/ui/focus-review")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_layer"] == "export or view"
        assert payload["workload_summary"] == {"must_review": 0, "quick_check": 0}
        assert payload["cards"] == []
        assert payload["empty_state"] == {
            "message": "No Focus Review items are currently open.",
            "fabricated_records": False,
        }
    finally:
        db.DB_PATH = old_db_path


def test_focus_review_excludes_hidden_default_fixture_reviews(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "parse_fixture_hidden",
                    None,
                    "fixtures/sample_parse_results.json",
                    json.dumps({"confidence": 95, "rawStrain": "Fixture", "sexRaw": "female"}, ensure_ascii=False),
                    "2026-05-09T10:20:00Z",
                    "review",
                    95,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value,
                     suggested_value, review_reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_fixture_hidden",
                    "parse_fixture_hidden",
                    "Low",
                    "Fixture review",
                    "fixture",
                    "fixture",
                    "Fixture/sample records should stay out of default Focus Review workload.",
                    "open",
                    "2026-05-09T10:21:00Z",
                ),
            )
        client = TestClient(app)

        response = client.get("/api/ui/focus-review")

        assert response.status_code == 200
        payload = response.json()
        assert payload["workload_summary"] == {"must_review": 0, "quick_check": 0}
        assert payload["cards"] == []
    finally:
        db.DB_PATH = old_db_path


def test_focus_review_action_hint_does_not_mark_unknown_quick_check_safe(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "parse_unknown_quick",
                    None,
                    "manual_fixture",
                    json.dumps({"confidence": 90, "rawStrain": "B6J"}, ensure_ascii=False),
                    "2026-05-09T10:30:00Z",
                    "review",
                    90,
                    1,
                ),
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value,
                     suggested_value, review_reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_unknown_quick",
                    "parse_unknown_quick",
                    "Medium",
                    "New workflow review type",
                    "unknown",
                    "unknown",
                    "Unknown issue types should stay manual until explicitly whitelisted.",
                    "open",
                    "2026-05-09T10:31:00Z",
                ),
            )
        client = TestClient(app)

        response = client.get("/api/ui/focus-review")

        assert response.status_code == 200
        [card] = response.json()["cards"]
        [item] = card["review_items"]
        assert item["attention_level"] == "quick_check"
        assert item["action_hint"] == {
            "source_layer": "export or view",
            "mode": "manual_review_required",
            "primary_label": "Inspect source evidence",
            "requires_note": True,
            "requires_source_photo": False,
            "safe_quick_resolve": False,
        }
    finally:
        db.DB_PATH = old_db_path


def seed_colony_state_records(tmp_path: Path) -> None:
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    db.init_db()
    photo_id = "photo_colony_state"
    parse_id = "parse_colony_state"
    created_at = "2026-05-09T11:07:00Z"
    record = {
        "type": "Separated",
        "cardIdRaw": "C-12",
        "rawStrain": "B6J",
        "matchedStrain": "C57BL/6J",
        "sexRaw": "female",
        "dobRaw": "2026-04-01",
        "mouseCount": "2 total",
        "confidence": 91,
        "notes": [
            {"raw": "MT401 R'", "strike": "none"},
            {"raw": "MT402 L'", "strike": "none"},
        ],
    }
    with db.connection() as conn:
        conn.execute(
            """
            INSERT INTO photo_log
                (photo_id, original_filename, stored_path, uploaded_at, status, raw_source_kind)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                photo_id,
                "colony-state-card.jpg",
                "data/photos/test/colony-state-card.jpg",
                "2026-05-09T11:05:00Z",
                "accepted",
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
                parse_id,
                photo_id,
                "manual_photo_transcription",
                json.dumps(record, ensure_ascii=False),
                created_at,
                "accepted",
                91,
                0,
            ),
        )
        snapshot_id = create_card_snapshot(conn, parse_id, photo_id, record, created_at)
        conn.execute(
            "UPDATE card_snapshot SET status = ?, source_layer = ? WHERE card_snapshot_id = ?",
            ("accepted", "canonical structured state", snapshot_id),
        )
        write_note_items_and_mouse_candidates(conn, parse_id, {**record, "cardSnapshotId": snapshot_id}, "accepted")
        conn.executemany(
            """
            INSERT INTO mouse_master
                (mouse_id, display_id, raw_strain_text, sex, dob_raw, dob_start,
                 current_card_snapshot_id, status, source_photo_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "MT401",
                    "MT401",
                    "C57BL/6J",
                    "female",
                    "2026-04-01",
                    "2026-04-01",
                    snapshot_id,
                    "active",
                    photo_id,
                    "2026-05-09T11:08:00Z",
                    "2026-05-09T11:08:00Z",
                ),
                (
                    "MT402",
                    "MT402",
                    "C57BL/6J",
                    "female",
                    "2026-04-01",
                    "2026-04-01",
                    snapshot_id,
                    "active",
                    photo_id,
                    "2026-05-09T11:08:00Z",
                    "2026-05-09T11:08:00Z",
                ),
                (
                    "MT999",
                    "MT999",
                    "C57BL/6J",
                    "female",
                    "2026-03-01",
                    "2026-03-01",
                    snapshot_id,
                    "dead",
                    photo_id,
                    "2026-05-09T11:08:00Z",
                    "2026-05-09T11:08:00Z",
                ),
            ],
        )
        conn.execute(
            """
            INSERT INTO review_queue
                (review_id, parse_id, severity, issue, current_value,
                 suggested_value, review_reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "review_colony_state_blocker",
                parse_id,
                "High",
                "Duplicate active mouse",
                "MT402 active in two card snapshots",
                "Resolve in Focus Review.",
                "Open blocker should be summarized, not duplicated, on Colony State.",
                "open",
                "2026-05-09T11:09:00Z",
            ),
        )
        conn.execute(
            """
            INSERT INTO source_record
                (source_record_id, source_type, source_uri, source_label,
                 raw_payload, checksum, imported_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "source_mating_colony_state",
                "manual_review",
                "review://mating/cage-12",
                "Reviewed mating cage C-12",
                json.dumps({"mating_label": "C-12 breeding pair"}, ensure_ascii=False),
                "checksum_mating_colony_state",
                "2026-05-09T11:10:00Z",
                "Source-backed mating state fixture.",
            ),
        )
        conn.execute(
            """
            INSERT INTO mating_registry
                (mating_id, mating_label, strain_goal, expected_genotype,
                 start_date, status, purpose, note, source_record_id,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mating_colony_state",
                "C-12 breeding pair",
                "C57BL/6J",
                "",
                "2026-04-15",
                "active",
                "breeding",
                "Accepted reviewed mating.",
                "source_mating_colony_state",
                "2026-05-09T11:11:00Z",
                "2026-05-09T11:11:00Z",
            ),
        )
        conn.executemany(
            """
            INSERT INTO mating_mouse
                (mating_mouse_id, mating_id, mouse_id, role, joined_date,
                 removed_date, note, source_record_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "mating_mouse_colony_state_female",
                    "mating_colony_state",
                    "MT401",
                    "female",
                    "2026-04-15",
                    None,
                    "Active dam.",
                    "source_mating_colony_state",
                    "2026-05-09T11:11:00Z",
                ),
                (
                    "mating_mouse_colony_state_male",
                    "mating_colony_state",
                    "MT402",
                    "male",
                    "2026-04-15",
                    None,
                    "Active sire.",
                    "source_mating_colony_state",
                    "2026-05-09T11:11:00Z",
                ),
            ],
        )
        conn.execute(
            """
            INSERT INTO litter_registry
                (litter_id, litter_label, mating_id, birth_date, number_born,
                 number_alive, number_weaned, weaning_date, status, note,
                 source_record_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "litter_colony_state",
                "F1",
                "mating_colony_state",
                "2026-05-01",
                6,
                5,
                None,
                "",
                "born",
                "Accepted active litter.",
                "source_mating_colony_state",
                "2026-05-09T11:12:00Z",
                "2026-05-09T11:12:00Z",
            ),
        )


def test_colony_state_uses_only_db_backed_current_records(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        seed_colony_state_records(tmp_path)
        client = TestClient(app)

        response = client.get("/api/ui/colony-state?as_of=2026-05-09")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_layer"] == "export or view"
        assert payload["page_question"] == "What is active now?"
        assert payload["summary"] == {
            "active_mice": 2,
            "active_card_snapshots": 1,
            "active_matings": 1,
            "active_litters": 1,
            "must_review": 1,
            "quick_check": 0,
        }
        [card] = payload["active_card_snapshots"]
        assert card["card_snapshot_id"].startswith("card_")
        assert card["source_layer"] == "canonical structured state"
        assert card["source_photo"]["photo_id"] == "photo_colony_state"
        assert card["source_photo"]["source_photo_role"] == "primary_evidence"
        assert card["mouse_count"] == 2
        assert card["collapsed_sections"] == {
            "mice": 2,
            "note_lines": 2,
            "review_blockers": 1,
            "source_evidence": 1,
        }
        assert payload["strain_summary"] == [{"strain": "C57BL/6J", "active_mice": 2}]
        assert payload["status_summary"] == [{"status": "active", "mouse_count": 2}]
        assert payload["active_matings"] == [
            {
                "mating_id": "mating_colony_state",
                "mating_label": "C-12 breeding pair",
                "strain_goal": "C57BL/6J",
                "expected_genotype": "",
                "start_date": "2026-04-15",
                "status": "active",
                "purpose": "breeding",
                "source_record_id": "source_mating_colony_state",
                "parent_count": 2,
                "active_litter_count": 1,
                "source_layer": "canonical structured state",
                "collapsed_sections": {
                    "parents": 2,
                    "active_litters": 1,
                    "source_evidence": 1,
                },
            }
        ]
        assert payload["active_litters"] == [
            {
                "litter_id": "litter_colony_state",
                "litter_label": "F1",
                "mating_id": "mating_colony_state",
                "mating_label": "C-12 breeding pair",
                "birth_date": "2026-05-01",
                "number_born": 6,
                "number_alive": 5,
                "number_weaned": None,
                "weaning_date": "",
                "status": "born",
                "source_record_id": "source_mating_colony_state",
                "source_layer": "canonical structured state",
                "collapsed_sections": {
                    "pups_alive": 5,
                    "source_evidence": 1,
                },
                "action_hint": {
                    "mode": "upcoming",
                    "label": "Separation review upcoming",
                    "priority": "low",
                    "age_days": 8,
                    "threshold_days": 30,
                    "automation": "manual_review_only",
                    "suggested_actions": ["watch_litter", "review_at_threshold"],
                },
            }
        ]
        assert payload["attention_links"] == [
            {
                "label": "Focus Review",
                "target_path": "/api/ui/focus-review",
                "must_review": 1,
                "quick_check": 0,
            }
        ]
        assert "review_items" not in card
        assert payload["empty_state"]["fabricated_records"] is False
    finally:
        db.DB_PATH = old_db_path


def test_colony_state_empty_state_does_not_fabricate_records(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()
        client = TestClient(app)

        response = client.get(f"/api/ui/colony-state?as_of={date.today().isoformat()}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_layer"] == "export or view"
        assert payload["summary"] == {
            "active_mice": 0,
            "active_card_snapshots": 0,
            "active_matings": 0,
            "active_litters": 0,
            "must_review": 0,
            "quick_check": 0,
        }
        assert payload["active_card_snapshots"] == []
        assert payload["active_matings"] == []
        assert payload["active_litters"] == []
        assert payload["strain_summary"] == []
        assert payload["status_summary"] == []
        assert payload["attention_links"] == []
        assert payload["empty_state"] == {
            "message": "No accepted active colony records are available yet.",
            "fabricated_records": False,
        }
    finally:
        db.DB_PATH = old_db_path


def test_colony_state_litter_action_hints_are_read_only_and_threshold_backed(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        seed_colony_state_records(tmp_path)
        due_birth_date = (date.today() - timedelta(days=35)).isoformat()
        overdue_birth_date = (date.today() - timedelta(days=50)).isoformat()
        high_overdue_birth_date = (date.today() - timedelta(days=65)).isoformat()
        with db.connection() as conn:
            conn.executemany(
                """
                INSERT INTO litter_registry
                    (litter_id, litter_label, mating_id, birth_date, number_born,
                     number_alive, number_weaned, weaning_date, status, note,
                     source_record_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "litter_due_review",
                        "F2",
                        "mating_colony_state",
                        due_birth_date,
                        7,
                        7,
                        None,
                        "",
                        "born",
                        "Due for separation review.",
                        "source_mating_colony_state",
                        "2026-05-09T11:13:00Z",
                        "2026-05-09T11:13:00Z",
                    ),
                    (
                        "litter_overdue_review",
                        "F3",
                        "mating_colony_state",
                        overdue_birth_date,
                        4,
                        4,
                        None,
                        "",
                        "born",
                        "Overdue for separation review.",
                        "source_mating_colony_state",
                        "2026-05-09T11:14:00Z",
                        "2026-05-09T11:14:00Z",
                    ),
                    (
                        "litter_high_overdue_review",
                        "F4",
                        "mating_colony_state",
                        high_overdue_birth_date,
                        3,
                        3,
                        None,
                        "",
                        "born",
                        "High-overdue separation review.",
                        "source_mating_colony_state",
                        "2026-05-09T11:15:00Z",
                        "2026-05-09T11:15:00Z",
                    ),
                ],
            )
        client = TestClient(app)

        response = client.get("/api/ui/colony-state")

        assert response.status_code == 200
        payload = response.json()
        hints = {item["litter_id"]: item["action_hint"] for item in payload["active_litters"]}
        assert hints["litter_colony_state"] == {
            "mode": "upcoming",
            "label": "Separation review upcoming",
            "priority": "low",
            "age_days": (date.today() - date.fromisoformat("2026-05-01")).days,
            "threshold_days": 30,
            "automation": "manual_review_only",
            "suggested_actions": ["watch_litter", "review_at_threshold"],
        }
        assert hints["litter_due_review"]["mode"] == "review_due"
        assert hints["litter_due_review"]["priority"] == "medium"
        assert hints["litter_due_review"]["threshold_days"] == 30
        assert hints["litter_overdue_review"]["mode"] == "overdue_review"
        assert hints["litter_overdue_review"]["priority"] == "medium"
        assert hints["litter_high_overdue_review"]["mode"] == "urgent_review"
        assert hints["litter_high_overdue_review"]["priority"] == "high"
        assert all(hint["automation"] == "manual_review_only" for hint in hints.values())
        with db.connection() as conn:
            statuses = {
                row["litter_id"]: row["status"]
                for row in conn.execute(
                    "SELECT litter_id, status FROM litter_registry WHERE litter_id LIKE 'litter_%review' OR litter_id = 'litter_colony_state'"
                ).fetchall()
            }
            event_count = conn.execute("SELECT COUNT(*) FROM mouse_event").fetchone()[0]
        assert statuses["litter_due_review"] == "born"
        assert statuses["litter_overdue_review"] == "born"
        assert statuses["litter_high_overdue_review"] == "born"
        assert event_count == 0
    finally:
        db.DB_PATH = old_db_path


def test_colony_schedule_derives_tasks_from_accepted_litter_and_rules(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        seed_colony_state_records(tmp_path)
        client = TestClient(app)

        response = client.get("/api/ui/colony-schedule?as_of=2026-05-09")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_layer"] == "export or view"
        assert payload["page_question"] == "What needs doing next?"
        assert payload["rule_set"] == {
            "rule_set_id": "breeding_rule_default_20260509",
            "display_name": "Default breeding operation review rules",
            "source_layer": "parsed or intermediate result",
        }
        assert payload["summary"] == {
            "due_now": 0,
            "due_soon": 1,
            "later": 0,
            "blocked_by_review": 1,
            "completed": 0,
        }
        [group] = payload["task_groups"]
        assert group["group"] == "due_soon"
        [task] = group["tasks"]
        assert task == {
            "task_id": "schedule_litter_separation_litter_colony_state",
            "task_type": "litter_separation",
            "label": "Separate/wean litter F1",
            "status": "blocked_by_review",
            "recorded_date": "2026-05-01",
            "due_date": "2026-05-31",
            "days_until_due": 22,
            "source_layer": "export or view",
            "source_entity": {
                "entity_type": "litter",
                "entity_id": "litter_colony_state",
                "label": "F1",
            },
            "source_evidence": {
                "source_record_id": "source_mating_colony_state",
                "mating_id": "mating_colony_state",
                "mating_label": "C-12 breeding pair",
            },
            "due_date_rule": {
                "rule_set_id": "breeding_rule_default_20260509",
                "rule_key": "litter_separation_due_after_days",
                "value_days": 30,
            },
            "attention_link": {
                "label": "Open Focus Review",
                "target_path": "/api/ui/focus-review",
                "must_review": 1,
                "quick_check": 0,
            },
        }
        assert payload["calendar_mirror"] == {
            "status": "not_configured",
            "canonical_source": "MouseDB internal schedule",
            "note": "External calendar sync can mirror accepted schedule tasks later; it is not canonical.",
        }
        assert payload["empty_state"]["fabricated_records"] is False
    finally:
        db.DB_PATH = old_db_path


def test_colony_schedule_empty_state_does_not_fabricate_tasks(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        db.DB_PATH = tmp_path / "mouse_lims.sqlite"
        db.init_db()
        client = TestClient(app)

        response = client.get("/api/ui/colony-schedule?as_of=2026-05-09")

        assert response.status_code == 200
        payload = response.json()
        assert payload["source_layer"] == "export or view"
        assert payload["summary"] == {
            "due_now": 0,
            "due_soon": 0,
            "later": 0,
            "blocked_by_review": 0,
            "completed": 0,
        }
        assert payload["task_groups"] == []
        assert payload["empty_state"] == {
            "message": "No accepted schedule tasks are available yet.",
            "fabricated_records": False,
        }
    finally:
        db.DB_PATH = old_db_path


def test_colony_state_excludes_noncanonical_card_snapshots(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    try:
        seed_colony_state_records(tmp_path)
        with db.connection() as conn:
            conn.execute(
                """
                UPDATE card_snapshot
                SET source_layer = ?
                WHERE parse_id = ?
                """,
                ("parsed or intermediate result", "parse_colony_state"),
            )
        client = TestClient(app)

        response = client.get("/api/ui/colony-state")

        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["active_mice"] == 2
        assert payload["summary"]["active_card_snapshots"] == 0
        assert payload["active_card_snapshots"] == []
        assert payload["empty_state"]["fabricated_records"] is False
    finally:
        db.DB_PATH = old_db_path
