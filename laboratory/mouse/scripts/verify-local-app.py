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
            {"photo_log", "parse_result", "review_queue", "action_log", "my_assigned_strain"}.issubset(tables),
            "Local SQLite schema is incomplete.",
        )

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
                assert_true(client.get("/api/assigned-strains").json() == [], "Assigned strain scope should start empty.")
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
                review_items = client.get("/api/review-items").json()
                assert_true(len(review_items) >= 2, "Fixture import should create review items.")
                assert_true(
                    not any(item["issue"] == "Outside assigned strain scope" for item in review_items),
                    "Assigned ApoM scope should prevent ApoM fixture rows from being marked outside scope.",
                )

    print("Local app scaffold verification passed.")


if __name__ == "__main__":
    main()
