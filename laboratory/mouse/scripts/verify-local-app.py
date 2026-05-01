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

    with tempfile.TemporaryDirectory() as old_schema_dir:
        db.DATA_DIR = Path(old_schema_dir)
        db.DB_PATH = Path(old_schema_dir) / "mouse_lims.sqlite"
        legacy_conn = sqlite3.connect(db.DB_PATH)
        try:
            legacy_conn.executescript(
                """
                CREATE TABLE mouse_master (
                    mouse_id TEXT PRIMARY KEY,
                    display_id TEXT NOT NULL
                );
                CREATE TABLE card_note_item_log (
                    note_item_id TEXT PRIMARY KEY,
                    raw_line_text TEXT NOT NULL
                );
                CREATE TABLE genotyping_record (
                    genotyping_id TEXT PRIMARY KEY,
                    mouse_id TEXT,
                    sample_id TEXT,
                    sample_date TEXT,
                    result_date TEXT,
                    created_at TEXT
                );
                """
            )
            legacy_conn.commit()
        finally:
            legacy_conn.close()
        db.init_db()
        migrated_conn = sqlite3.connect(db.DB_PATH)
        try:
            mouse_columns = {
                row[1]
                for row in migrated_conn.execute("PRAGMA table_info(mouse_master)").fetchall()
            }
            note_columns = {
                row[1]
                for row in migrated_conn.execute("PRAGMA table_info(card_note_item_log)").fetchall()
            }
            genotype_columns = {
                row[1]
                for row in migrated_conn.execute("PRAGMA table_info(genotyping_record)").fetchall()
            }
        finally:
            migrated_conn.close()
        assert_true(
            {"target_match_status", "use_category", "next_action", "sample_id"}.issubset(mouse_columns),
            "Existing mouse_master tables should migrate to the genotyping workflow schema.",
        )
        assert_true(
            {"parsed_ear_label_code", "strike_status", "needs_review"}.issubset(note_columns),
            "Existing card_note_item_log tables should migrate to the note parsing schema.",
        )
        assert_true(
            {"target_name", "normalized_result", "result_status", "updated_at"}.issubset(genotype_columns),
            "Existing genotyping_record tables should migrate to the result tracking schema.",
        )

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
                "source_record",
                "strain_registry",
                "correction_log",
                "export_log",
                "mouse_event",
                "genotyping_record",
                "strain_target_genotype",
                "cage_registry",
                "mouse_cage_assignment",
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
                assert_true("Strain Registry" in index_html, "Local UI should expose strain registry.")
                assert_true("Source Evidence" in index_html, "Local UI should expose source evidence.")
                assert_true("Mouse Events" in index_html, "Local UI should expose mouse events.")
                assert_true("Correction Log" in index_html, "Local UI should expose correction history.")
                assert_true("Search & CSV Export" in index_html, "Local UI should expose search and CSV export.")
                assert_true("Download Genotyping Worklist" in index_html, "Local UI should expose genotyping worklist export.")
                assert_true("Download Ready CSV" in index_html, "Local UI should expose gated final CSV export.")
                assert_true("Cage View" in index_html, "Local UI should expose cage management.")
                assert_true("Target genotype" in index_html, "Local UI should expose configurable target genotype rules.")
                assert_true("genotypingDashboard" in index_html, "Local UI should expose genotyping dashboard cards.")
                assert_true("exportRows" in index_html, "Local UI should expose export preview rows.")
                assert_true("exportBlockerRows" in index_html, "Local UI should expose export blockers.")
                assert_true("exportLogRows" in index_html, "Local UI should expose export history.")
                assert_true("Deactivate" in index_html, "Local UI should expose assigned strain deactivation.")
                assert_true("Distribution Assignment Import" in index_html, "Local UI should expose distribution import.")
                assert_true("/[^a-z0-9가-힣]/g" in index_html, "Local UI strain matching key should preserve Korean strain text.")
                assert_true(client.get("/api/assigned-strains").json() == [], "Assigned strain scope should start empty.")
                assert_true(client.get("/api/source-records").json() == [], "Source evidence should start empty.")
                assert_true(client.get("/api/strains").json() == [], "Strain registry should start empty.")
                strain = client.post(
                    "/api/strains",
                    json={
                        "strain_name": "PV-Cre",
                        "gene": "Pvalb",
                        "allele": "Pvalb-IRES-Cre",
                        "background": "C57BL/6J",
                        "source": "manual",
                        "status": "active",
                    },
                )
                assert_true(strain.status_code == 200, "Could not create strain registry entry.")
                strain_payload = strain.json()
                assert_true(strain_payload["source_record_id"], "Strain entry should create source evidence.")
                strains = client.get("/api/strains").json()
                assert_true(strains[0]["strain_name"] == "PV-Cre", "Strain registry did not persist entry.")
                source_records = client.get("/api/source-records").json()
                assert_true(
                    any(item["source_type"] == "manual_entry" for item in source_records),
                    "Manual strain creation should leave source evidence.",
                )
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
                assert_true(distribution_payload["source_record_id"], "Distribution import should create source evidence.")
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

                outside_import = client.post("/api/fixtures/import-sample")
                assert_true(outside_import.status_code == 200, "Could not import fixture without active assigned scope.")
                outside_reviews = client.get("/api/review-items").json()
                assert_true(
                    any(item["issue"] == "Outside assigned strain scope" for item in outside_reviews),
                    "Fixture import without active scope should create outside-scope review items.",
                )

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
                mouse_events = client.get("/api/mouse-events").json()
                assert_true(len(mouse_events) >= 3, "Mouse candidates should create mouse event history.")
                assert_true(
                    any(event["event_type"] == "note_added" for event in mouse_events),
                    "Mouse event history should include source-backed note events.",
                )
                review_items = client.get("/api/review-items").json()
                assert_true(len(review_items) >= 4, "Fixture import should create review and validation items.")
                assert_true(
                    not any(item["issue"] == "Outside assigned strain scope" for item in review_items),
                    "Assigned ApoM scope should clear stale outside-scope review items for now-accepted rows.",
                )
                assert_true(
                    any(item["parse_id"] == "FIXTURE-COUNT-MISMATCH" and item["issue"] == "Count mismatch" for item in review_items),
                    "Count mismatch fixture should create a backend review item.",
                )
                assert_true(
                    any(item["parse_id"] == "FIXTURE-DUPLICATE-ACTIVE" and item["issue"] == "Duplicate active mouse" for item in review_items),
                    "Duplicate active fixture should create a backend review item.",
                )
                assert_true(
                    any(item["parse_id"] == "FIXTURE-EAR-LABEL-CHECK" and item["issue"] == "Ear label needs review" for item in review_items),
                    "Ambiguous ear label fixture should create a note-level review item.",
                )
                count_review = next(item for item in review_items if item["parse_id"] == "FIXTURE-COUNT-MISMATCH")
                resolved = client.post(
                    f"/api/review-items/{count_review['review_id']}/resolve",
                    json={"resolution_note": "Reviewed count mismatch in source note lines."},
                )
                assert_true(resolved.status_code == 200, "Could not resolve review item.")
                resolved_items = client.get("/api/review-items").json()
                resolved_count_review = next(item for item in resolved_items if item["review_id"] == count_review["review_id"])
                assert_true(resolved_count_review["status"] == "resolved", "Resolved review item stayed open.")
                with db.connection() as conn:
                    review_action_count = conn.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM action_log
                        WHERE action_type = 'review_resolved' AND target_id = ?
                        """,
                        (count_review["review_id"],),
                    ).fetchone()["count"]
                assert_true(review_action_count == 1, "Review resolution should create an action log entry.")
                note_items = client.get("/api/note-items").json()
                mice = client.get("/api/mice").json()
                assert_true(
                    any(item["raw_line_text"] == "MT321 R'" and item["parsed_ear_label_code"] == "R_PRIME" for item in note_items),
                    "Note item API should expose parsed ear label evidence.",
                )
                assert_true(
                    any(
                        item["raw_line_text"] == "MT399 R0"
                        and item["parsed_ear_label_code"] == "R_CIRCLE"
                        and item["parsed_ear_label_review_status"] == "check"
                        and item["needs_review"] == 1
                        for item in note_items
                    ),
                    "Ambiguous ear label note should stay reviewable with raw evidence.",
                )
                assert_true(
                    any(
                        mouse["display_id"] == "MT399"
                        and mouse["ear_label_raw"] == "R0"
                        and mouse["ear_label_code"] is None
                        and mouse["ear_label_review_status"] == "check"
                        for mouse in mice
                    ),
                    "Mouse candidate should not accept an uncertain normalized ear label.",
                )
                assert_true(
                    any(mouse["display_id"] == "MT323" and mouse["status"] == "moved" for mouse in mice),
                    "Mouse API should expose moved candidate from single-struck note line.",
                )
                cage = client.post(
                    "/api/cages",
                    json={"cage_label": "C-014", "location": "Room A / Rack 2", "cage_type": "holding"},
                )
                assert_true(cage.status_code == 200, "Could not create cage registry entry.")
                cage_payload = cage.json()
                assert_true(cage_payload["source_record_id"], "Cage creation should create source evidence.")
                moved_mouse = next(mouse for mouse in mice if mouse["display_id"] == "MT321")
                moved_to_cage = client.post(
                    f"/api/mice/{moved_mouse['mouse_id']}/move-cage",
                    json={"cage_id": cage_payload["cage_id"], "note": "Verified cage movement flow."},
                )
                assert_true(moved_to_cage.status_code == 200, "Could not move mouse to cage.")
                moved_payload = moved_to_cage.json()
                assert_true(moved_payload["event_id"], "Cage move should create a mouse event.")
                cage_rows = client.get("/api/cages").json()
                assert_true(
                    any(row["cage_label"] == "C-014" and row["active_mouse_count"] == 1 for row in cage_rows),
                    "Cage list should show active mouse count after assignment.",
                )
                mice_after_cage = client.get("/api/mice", params={"query": "C-014"}).json()
                assert_true(
                    any(mouse["display_id"] == "MT321" and mouse["current_cage_label"] == "C-014" for mouse in mice_after_cage),
                    "Mouse search should find current cage assignment.",
                )
                cage_events = client.get("/api/mouse-events").json()
                assert_true(
                    any(event["event_type"] == "moved" and event["related_entity_id"] == cage_payload["cage_id"] for event in cage_events),
                    "Cage movement should be present in mouse event history.",
                )
                filtered_mice = client.get("/api/mice", params={"query": "MT321"}).json()
                assert_true(
                    filtered_mice and all("MT321" in mouse["display_id"] for mouse in filtered_mice),
                    "Mouse search filter should narrow candidate records by display ID.",
                )
                search_payload = client.get("/api/search", params={"query": "PV-Cre"}).json()
                assert_true(search_payload["query"] == "PV-Cre", "Search endpoint should echo the active query.")
                assert_true(
                    any(strain["strain_name"] == "PV-Cre" for strain in search_payload["strains"]),
                    "Search endpoint should include strain registry matches.",
                )
                csv_response = client.get("/api/exports/mice.csv", params={"query": "MT321"})
                assert_true(csv_response.status_code == 200, "Mouse CSV export endpoint failed.")
                assert_true(
                    csv_response.headers["content-type"].startswith("text/csv"),
                    "Mouse CSV export should return CSV content.",
                )
                csv_text = csv_response.text
                assert_true("display_id" in csv_text and "MT321" in csv_text, "Mouse CSV export is missing expected rows.")
                assert_true("MT323" not in csv_text, "Filtered mouse CSV export should exclude non-matching mice.")
                export_log = client.get("/api/export-log").json()
                assert_true(export_log, "CSV generation should create an export log entry.")
                assert_true(export_log[0]["export_type"] == "mouse_csv", "Export log should record CSV export type.")
                assert_true(export_log[0]["filename"] == "mouse_records_filtered.csv", "Export log should preserve generated filename.")
                assert_true(export_log[0]["query"] == "MT321", "Export log should preserve the export filter.")
                assert_true(export_log[0]["row_count"] == len(filtered_mice), "Export log should preserve exported row count.")
                assert_true(export_log[0]["source_layer"] == "export or view", "Export log should stay in the export/view layer.")
                blocked_export = client.get("/api/exports/mice.csv", params={"query": "MT321", "require_ready": "true"})
                assert_true(blocked_export.status_code == 409, "Final CSV export should be blocked by open review items.")
                blocked_payload = blocked_export.json()["detail"]
                assert_true(
                    blocked_payload["source_layer"] == "export or view" and blocked_payload["blocked_review_count"] > 0,
                    "Blocked final export should report export/view layer and blocker count.",
                )
                blocked_log = client.get("/api/export-log").json()[0]
                assert_true(blocked_log["status"] == "blocked", "Blocked final export should create a blocked export log entry.")
                assert_true(blocked_log["filename"] == "mouse_records_filtered.csv", "Blocked export log should preserve intended filename.")
                export_preview = client.get("/api/export-preview").json()
                assert_true(export_preview["source_layer"] == "export or view", "Export preview should stay an export/view layer.")
                assert_true(export_preview["export_type"] == "separation_preview", "Export preview should identify its workbook-like shape.")
                assert_true(export_preview["preview_row_count"] >= 3, "Export preview should include mouse candidate rows.")
                assert_true(
                    any(row["display_id"] == "MT321" and row["source_note_item_id"] for row in export_preview["preview_rows"]),
                    "Export preview rows should preserve source note traceability.",
                )
                assert_true(
                    export_preview["blocked_review_items"] >= len(export_preview["review_blockers"]),
                    "Export preview should expose review blocker details up to its display limit.",
                )
                assert_true(export_preview["ready"] is False, "Open review blockers should keep export preview blocked.")
                dashboard_before = client.get("/api/genotyping-dashboard")
                assert_true(dashboard_before.status_code == 200, "Genotyping dashboard endpoint failed.")
                dashboard_before_rows = {card["key"]: card["count"] for card in dashboard_before.json()}
                assert_true(
                    dashboard_before_rows.get("not_sampled", 0) >= 1,
                    "Genotyping dashboard should count newly separated mice that need sampling.",
                )
                genotyping_target = next(mouse for mouse in mice if mouse["display_id"] == "MT321")
                target_rule = client.post(
                    "/api/strain-target-genotypes",
                    json={
                        "strain_text": genotyping_target["raw_strain_text"],
                        "target_genotype": "Tg/Tg",
                        "purpose": "mating_candidate",
                    },
                )
                assert_true(target_rule.status_code == 200, "Could not create configurable target genotype rule.")
                target_rules = client.get("/api/strain-target-genotypes").json()
                assert_true(
                    any(
                        rule["strain_text"] == genotyping_target["raw_strain_text"]
                        and rule["target_genotype"] == "Tg/Tg"
                        and rule["purpose"] == "mating_candidate"
                        for rule in target_rules
                    ),
                    "Target genotype rule API should preserve configured rule values.",
                )
                cage = client.post(
                    "/api/cages",
                    json={
                        "cage_label": "A-101",
                        "location": "Room A",
                        "rack": "R1",
                        "shelf": "S2",
                        "cage_type": "holding",
                        "note": "Verification cage.",
                    },
                )
                assert_true(cage.status_code == 200, "Could not create cage registry entry.")
                cage_payload = cage.json()
                assert_true(cage_payload["source_record_id"], "Cage creation should leave source evidence.")
                duplicate_cage = client.post("/api/cages", json={"cage_label": "a-101"})
                assert_true(duplicate_cage.status_code == 409, "Duplicate cage labels should be rejected case-insensitively.")
                cage_move = client.post(
                    f"/api/mice/{genotyping_target['mouse_id']}/move-cage",
                    json={"cage_id": cage_payload["cage_id"], "note": "Moved for verification."},
                )
                assert_true(cage_move.status_code == 200, "Could not assign mouse to cage.")
                cages = client.get("/api/cages").json()
                assert_true(
                    any(item["cage_label"] == "A-101" and item["active_mouse_count"] == 1 for item in cages),
                    "Cage list should include active assignment counts.",
                )
                genotyping_update = client.post(
                    "/api/genotyping/update",
                    json={
                        "mouse_id": genotyping_target["mouse_id"],
                        "sample_id": "MT321",
                        "raw_result": "Tg/Tg",
                        "normalized_result": "Tg/Tg",
                    },
                )
                assert_true(genotyping_update.status_code == 200, "Could not update genotyping workflow state.")
                genotyping_payload = genotyping_update.json()
                assert_true(genotyping_payload["genotyping_status"] == "resulted", "Genotyping result should mark mouse resulted.")
                assert_true(genotyping_payload["target_match_status"] == "matches_target", "Genotyping result should use configured target matching.")
                assert_true(genotyping_payload["next_action"] == "consider_for_mating", "Matching target genotype should suggest a mating review action.")
                dashboard_after = {card["key"]: card["count"] for card in client.get("/api/genotyping-dashboard").json()}
                assert_true(
                    dashboard_after.get("target_confirmed", 0) >= 1,
                    "Genotyping dashboard should count mice with confirmed target genotypes.",
                )
                genotyping_records = client.get("/api/genotyping-records").json()
                assert_true(
                    any(record["mouse_id"] == genotyping_target["mouse_id"] and record["normalized_result"] == "Tg/Tg" for record in genotyping_records),
                    "Genotyping record history should preserve the entered result.",
                )
                genotyping_export = client.get("/api/exports/genotyping-worklist.csv", params={"query": "MT321"})
                assert_true(genotyping_export.status_code == 200, "Genotyping worklist CSV export endpoint failed.")
                assert_true(
                    "genotyping_worklist_filtered.csv" in genotyping_export.headers.get("content-disposition", ""),
                    "Filtered genotyping worklist should use the filtered filename.",
                )
                assert_true(
                    "target_match_status" in genotyping_export.text
                    and "matches_target" in genotyping_export.text
                    and "consider_for_mating" in genotyping_export.text,
                    "Genotyping worklist export should include target match and next action fields.",
                )
                genotyping_export_log = client.get("/api/export-log").json()
                assert_true(
                    genotyping_export_log[0]["export_type"] == "genotyping_worklist_csv",
                    "Export log should record companion genotyping worklist exports.",
                )
                filtered_mice = client.get("/api/mice", params={"query": "MT321"}).json()
                assert_true(
                    filtered_mice and all("MT321" in mouse["display_id"] for mouse in filtered_mice),
                    "Mouse API query should filter mouse records.",
                )
                search = client.get("/api/search", params={"query": "Tg/Tg"}).json()
                assert_true(
                    any(mouse["display_id"] == "MT321" for mouse in search["mice"]),
                    "Search API should include matching genotyping mouse records.",
                )
                csv_export = client.get("/api/exports/mice.csv", params={"query": "MT321"})
                assert_true(csv_export.status_code == 200, "Mouse CSV export endpoint failed.")
                assert_true(
                    "mouse_records_filtered.csv" in csv_export.headers.get("content-disposition", ""),
                    "Filtered CSV export should use the filtered filename.",
                )
                assert_true(
                    "display_id" in csv_export.text and "MT321" in csv_export.text,
                    "Mouse CSV export should include headers and filtered mouse rows.",
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
                    genotyping_action_count = conn.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM action_log
                        WHERE action_type = 'genotyping_resulted' AND target_id = ?
                        """,
                        (genotyping_target["mouse_id"],),
                    ).fetchone()["count"]
                    cage_move_action_count = conn.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM action_log
                        WHERE action_type = 'mouse_cage_moved' AND target_id = ?
                        """,
                        (genotyping_target["mouse_id"],),
                    ).fetchone()["count"]
                    cage_move_event_count = conn.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM mouse_event
                        WHERE event_type = 'moved' AND related_entity_type = 'cage'
                        """
                    ).fetchone()["count"]
                    active_cage_assignment_count = conn.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM mouse_cage_assignment
                        WHERE mouse_id = ? AND status = 'active'
                        """,
                        (genotyping_target["mouse_id"],),
                    ).fetchone()["count"]
                    ended_cage_assignment_count = conn.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM mouse_cage_assignment
                        WHERE mouse_id = ? AND status = 'ended'
                        """,
                        (genotyping_target["mouse_id"],),
                    ).fetchone()["count"]
                assert_true(note_count >= 10, "Persisted note item evidence count is too low.")
                assert_true(mouse_count >= 3, "Persisted mouse candidate count is too low.")
                assert_true(moved_count >= 1, "Single-struck mouse note should create a moved candidate.")
                assert_true(duplicate_leak_count == 0, "Duplicate active fixture should not create mouse candidates.")
                assert_true(genotyping_action_count == 1, "Genotyping update should create an action log entry.")
                assert_true(cage_move_action_count >= 2, "Each cage move should create an action log entry.")
                assert_true(cage_move_event_count >= 1, "Cage move should create a mouse event.")
                assert_true(active_cage_assignment_count == 1, "Cage moves should leave only one active assignment per mouse.")
                assert_true(ended_cage_assignment_count >= 1, "Cage moves should close the previous active assignment.")
                correction = client.post(
                    "/api/corrections",
                    json={
                        "entity_type": "strain",
                        "entity_id": strain_payload["strain_id"],
                        "field_name": "common_name",
                        "before_value": "",
                        "after_value": "PV-Cre line",
                        "reason": "Verified local correction workflow.",
                        "source_record_id": strain_payload["source_record_id"],
                    },
                )
                assert_true(correction.status_code == 200, "Could not create correction log entry.")
                corrections = client.get("/api/corrections").json()
                assert_true(
                    corrections[0]["before_value"] == "" and corrections[0]["after_value"] == "PV-Cre line",
                    "Correction log should preserve before and after values.",
                )
                remaining_reviews = [
                    item for item in client.get("/api/review-items").json() if item["status"] == "open"
                ]
                assert_true(remaining_reviews, "Fixture should still have open review blockers before final release.")
                for item in remaining_reviews:
                    release_review = client.post(
                        f"/api/review-items/{item['review_id']}/resolve",
                        json={
                            "resolution_note": "Verified blocker before releasing ready CSV export.",
                            "resolved_value": item.get("suggested_value") or item.get("current_value") or "",
                        },
                    )
                    assert_true(release_review.status_code == 200, "Could not resolve remaining review blocker.")
                ready_preview = client.get("/api/export-preview").json()
                assert_true(ready_preview["ready"] is True, "Resolved review blockers should make export preview ready.")
                assert_true(ready_preview["blocked_review_items"] == 0, "Ready export preview should have no blockers.")
                ready_export = client.get("/api/exports/mice.csv", params={"query": "MT321", "require_ready": "true"})
                assert_true(ready_export.status_code == 200, "Ready CSV export should succeed after review resolution.")
                assert_true("MT321" in ready_export.text, "Ready CSV export should include the filtered mouse row.")
                ready_export_log = client.get("/api/export-log").json()[0]
                assert_true(ready_export_log["status"] == "generated", "Ready export should create a generated export log entry.")
                assert_true(
                    ready_export_log["blocked_review_count"] == 0,
                    "Ready export log should record zero review blockers after resolution.",
                )

    print("Local app scaffold verification passed.")


if __name__ == "__main__":
    main()
