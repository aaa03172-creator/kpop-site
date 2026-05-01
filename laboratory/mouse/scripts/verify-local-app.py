from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except (ModuleNotFoundError, RuntimeError):
    TestClient = None


ROOT = Path(__file__).resolve().parents[1]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    for path in [
        ROOT / "app" / "main.py",
        ROOT / "app" / "db.py",
        ROOT / "app" / "storage.py",
        ROOT / "static" / "index.html",
        ROOT / "requirements.txt",
        ROOT / "start.bat",
    ]:
        assert_true(path.exists(), f"Missing required local app file: {path}")

    fixture = json.loads((ROOT / "fixtures" / "sample_parse_results.json").read_text(encoding="utf-8"))
    assert_true(fixture.get("layer") == "parsed or intermediate result", "Fixture must stay non-canonical.")
    assert_true(len(fixture.get("records", [])) >= 3, "Fixture should contain parse records.")

    sys.path.insert(0, str(ROOT))
    from app import db
    app = None
    if TestClient is not None:
        from app.main import app

    with tempfile.TemporaryDirectory() as temp_dir:
        db.DATA_DIR = Path(temp_dir)
        db.DB_PATH = Path(temp_dir) / "mouse_lims.sqlite"
        db.init_db()
        conn = sqlite3.connect(db.DB_PATH)
        try:
            tables = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
        finally:
            conn.close()
        assert_true(
            {
                "photo_log",
                "parse_result",
                "review_queue",
                "action_log",
                "my_assigned_strain",
                "distribution_import",
                "distribution_assignment_row",
                "ear_label_master",
                "ear_label_alias",
                "mouse_master",
                "card_note_item_log",
            }.issubset(tables),
            "Local SQLite schema is incomplete.",
        )
        conn = sqlite3.connect(db.DB_PATH)
        try:
            master_rows = dict(
                conn.execute("SELECT ear_label_code, display_text FROM ear_label_master").fetchall()
            )
            ambiguous_alias = conn.execute(
                """
                SELECT confirmed
                FROM ear_label_alias
                WHERE raw_text = ? AND ear_label_code = ?
                """,
                ("R0", "R_CIRCLE"),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO card_note_item_log
                    (note_item_id, line_number, raw_line_text, parsed_type, strike_status,
                     interpreted_status, parsed_mouse_display_id, parsed_ear_label_raw,
                     parsed_ear_label_code, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "note_test_319",
                    1,
                    "319 L'",
                    "mouse_item",
                    "none",
                    "active",
                    "319",
                    "L'",
                    "L_PRIME",
                    0.98,
                ),
            )
            conn.execute(
                """
                INSERT INTO mouse_master
                    (mouse_id, display_id, raw_strain_text, dob_raw, dob_start, dob_end,
                     ear_label_raw, ear_label_code, source_note_item_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "mouse_test_319_a",
                    "319",
                    "ApoM Tg/Tg",
                    "25.10.20-28",
                    "2025-10-20",
                    "2025-10-28",
                    "L'",
                    "L_PRIME",
                    "note_test_319",
                ),
            )
            conn.execute(
                """
                INSERT INTO mouse_master
                    (mouse_id, display_id, raw_strain_text, dob_start, ear_label_code)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("mouse_test_319_b", "319", "Different strain candidate", "2026-01-01", "R_PRIME"),
            )
            mouse_defaults = conn.execute(
                """
                SELECT genotyping_status, next_action, status
                FROM mouse_master
                WHERE mouse_id = ?
                """,
                ("mouse_test_319_a",),
            ).fetchone()
            same_display_count = conn.execute(
                "SELECT COUNT(*) FROM mouse_master WHERE display_id = ?",
                ("319",),
            ).fetchone()[0]
            conn.commit()
        finally:
            conn.close()
        assert_true(master_rows.get("R_CIRCLE") == "R\u00b0", "R_CIRCLE must use degree-sign display text.")
        assert_true(master_rows.get("L_CIRCLE") == "L\u00b0", "L_CIRCLE must use degree-sign display text.")
        assert_true(ambiguous_alias is not None, "Ambiguous R0 alias should be seeded for review.")
        assert_true(ambiguous_alias[0] == 0, "Ambiguous R0 alias must not be auto-confirmed.")
        assert_true(
            tuple(mouse_defaults) == ("not_sampled", "sample_needed", "active"),
            "Mouse workflow defaults are wrong.",
        )
        assert_true(same_display_count == 2, "Mouse display IDs must remain non-unique identity candidates.")

        if TestClient is None:
            with db.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO my_assigned_strain
                        (assigned_strain_id, display_name, aliases_json, source_type, assigned_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("assigned_strain_test", "ApoM Tg/Tg", '["ApoMtg/tg"]', "manual", "test"),
                )
                count = conn.execute("SELECT COUNT(*) AS count FROM my_assigned_strain").fetchone()["count"]
            assert_true(count == 1, "Assigned strain scope table did not accept a row.")
        else:
            with TestClient(app) as client:
                index_html = client.get("/").text
                assert_true("Colony Records" in index_html, "Local UI should expose mouse records.")
                assert_true("Parsed Note Evidence" in index_html, "Local UI should expose parsed note evidence.")
                assert_true("Deactivate" in index_html, "Local UI should expose assigned strain deactivation.")
                assert_true("Distribution Assignment Import" in index_html, "Local UI should expose distribution import.")
                assert_true(client.get("/api/assigned-strains").json() == [], "Assigned strain scope should start empty.")
                distribution = client.post(
                    "/api/distribution-imports",
                    json={
                        "layer": "parsed or intermediate result",
                        "source_file_name": "distribution_test.xlsx",
                        "sheet_name": "Mating",
                        "rows": [
                            {
                                "institution_or_group": "Vet Med",
                                "responsible_person_raw": "Jang S.",
                                "mating_type_raw": "ApoMtg/tg",
                                "cage_count_raw": "6",
                                "source_row_number": 35,
                                "source_cells": {"mating_type": "B35"},
                                "review_status": "candidate",
                            }
                        ],
                    },
                )
                assert_true(distribution.status_code == 200, "Could not store distribution import JSON.")
                distribution_payload = distribution.json()
                assert_true(distribution_payload["stored_rows"] == 1, "Distribution import row count is wrong.")
                distribution_imports = client.get("/api/distribution-imports").json()
                stored_distribution = next(
                    (
                        item
                        for item in distribution_imports
                        if item["distribution_import_id"] == distribution_payload["distribution_import_id"]
                    ),
                    None,
                )
                assert_true(stored_distribution is not None, "Distribution import list should include the stored import.")
                assert_true(
                    stored_distribution["rows"][0]["traceability"]["source_cells"]["mating_type"] == "B35",
                    "Distribution import should preserve source cell traceability.",
                )
                created = client.post(
                    "/api/assigned-strains",
                    json={
                        "display_name": "ApoM Tg/Tg",
                        "aliases": ["ApoMtg/tg", "ApoM"],
                        "source_type": "manual",
                    },
                )
                assert_true(created.status_code == 200, "Could not create assigned strain scope.")
                payload = created.json()
                assert_true(payload["active"] is True, "Created assigned strain should be active.")
                assert_true("ApoMtg/tg" in payload["aliases"], "Assigned strain aliases were not preserved.")

                rows = client.get("/api/assigned-strains").json()
                assert_true(len(rows) == 1, "Assigned strain list did not return the created scope.")
                assert_true(rows[0]["display_name"] == "ApoM Tg/Tg", "Assigned strain display name changed.")

                deactivated = client.post(f"/api/assigned-strains/{payload['assigned_strain_id']}/deactivate")
                assert_true(deactivated.status_code == 200, "Could not deactivate assigned strain scope.")
                rows = client.get("/api/assigned-strains").json()
                assert_true(rows[0]["active"] is False, "Deactivated assigned strain stayed active.")

                mice_before_distribution = client.get("/api/mice").json()
                distribution_fixture = json.loads(
                    (ROOT / "fixtures" / "sample_distribution_import.json").read_text(encoding="utf-8")
                )
                distribution_import = client.post("/api/distribution-imports", json=distribution_fixture)
                assert_true(distribution_import.status_code == 200, "Could not import distribution assignment JSON.")
                distribution_payload = distribution_import.json()
                assert_true(
                    distribution_payload["boundary"] == "parsed or intermediate result",
                    "Distribution import should stay non-canonical.",
                )
                assert_true(distribution_payload["stored_rows"] >= 3, "Distribution import stored too few rows.")
                imports = client.get("/api/distribution-imports").json()
                imported_fixture = next(
                    (
                        item
                        for item in imports
                        if item["distribution_import_id"] == distribution_payload["distribution_import_id"]
                    ),
                    None,
                )
                assert_true(imported_fixture is not None, f"Distribution import list did not return the new import: {imports!r}")
                assert_true(
                    any(row["mating_type_raw"] == "GFAP Cre; S1PR1 fl/fl" for row in imported_fixture["rows"]),
                    "Distribution assignment rows did not preserve candidate mating type.",
                )
                assert_true(
                    client.get("/api/mice").json() == mice_before_distribution,
                    "Distribution import must not create canonical mouse records.",
                )

                with db.connection() as conn:
                    action_count = conn.execute(
                        "SELECT COUNT(*) AS count FROM action_log WHERE target_id = ?",
                        (payload["assigned_strain_id"],),
                    ).fetchone()["count"]
                assert_true(action_count == 2, "Assigned strain changes should be logged.")

                client.post(
                    "/api/assigned-strains",
                    json={
                        "display_name": "ApoM Tg/Tg",
                        "aliases": ["ApoMtg/tg", "ApoM"],
                        "source_type": "manual",
                    },
                )
                imported = client.post("/api/fixtures/import-sample")
                assert_true(imported.status_code == 200, "Could not import sample fixture through local API.")
                imported_payload = imported.json()
                assert_true(
                    imported_payload["created_or_updated_note_items"] >= 10,
                    "Fixture import should persist parsed note item evidence.",
                )
                assert_true(
                    imported_payload["created_or_updated_mouse_candidates"] >= 3,
                    "Fixture import should create safe mouse candidates from accepted separated rows.",
                )
                review_items = client.get("/api/review-items").json()
                assert_true(len(review_items) >= 4, "Fixture import should create review and validation items.")
                assert_true(
                    not any(item["issue"] == "Outside assigned strain scope" for item in review_items),
                    "Assigned ApoM scope should prevent ApoM fixture rows from being marked outside scope.",
                )
                assert_true(
                    any(item["parse_id"] == "FIXTURE-COUNT-MISMATCH" and item["issue"] == "Count mismatch" for item in review_items),
                    "Count mismatch fixture should create a backend review item.",
                )
                assert_true(
                    any(item["parse_id"] == "FIXTURE-DUPLICATE-ACTIVE" and item["issue"] == "Duplicate active mouse" for item in review_items),
                    "Duplicate active fixture should create a backend review item.",
                )
                note_items = client.get("/api/note-items").json()
                mice = client.get("/api/mice").json()
                assert_true(
                    any(item["raw_line_text"] == "MT321 R'" and item["parsed_ear_label_code"] == "R_PRIME" for item in note_items),
                    "Note item API should expose parsed ear label evidence.",
                )
                assert_true(
                    any(mouse["display_id"] == "MT323" and mouse["status"] == "moved" for mouse in mice),
                    "Mouse API should expose moved candidate from single-struck note line.",
                )
                with db.connection() as conn:
                    note_count = conn.execute(
                        "SELECT COUNT(*) AS count FROM card_note_item_log"
                    ).fetchone()["count"]
                    mouse_count = conn.execute("SELECT COUNT(*) AS count FROM mouse_master").fetchone()["count"]
                    moved_count = conn.execute(
                        "SELECT COUNT(*) AS count FROM mouse_master WHERE status = 'moved'"
                    ).fetchone()["count"]
                    duplicate_leak_count = conn.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM mouse_master
                        WHERE source_note_item_id LIKE ?
                        """,
                        ("note_FIXTURE-DUPLICATE-ACTIVE_%",),
                    ).fetchone()["count"]
                assert_true(note_count >= 10, "Persisted note item evidence count is too low.")
                assert_true(mouse_count >= 3, "Persisted mouse candidate count is too low.")
                assert_true(moved_count >= 1, "Single-struck mouse note should create a moved candidate.")
                assert_true(duplicate_leak_count == 0, "Duplicate active fixture should not create mouse candidates.")

    print("Local app scaffold verification passed.")


if __name__ == "__main__":
    main()
