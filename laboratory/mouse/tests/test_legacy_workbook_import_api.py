from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app import db
from app.main import app


def workbook_bytes() -> bytes:
    stream = BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = "animal sheet"
    ws.append(["Cage No.", "Strain", "Sex", "I.D", "Genotype", "DOB", "Mating Date", "Pubs"])
    ws.append(["86", "ApoM Tg/Tg", "male", "14", "Tg", "2026-01-21", "2026-02-18", ""])
    ws.append(["", "", "female", "15", "Tg", "2026-01-21", "", ""])
    wb.save(stream)
    wb.close()
    return stream.getvalue()


def test_legacy_workbook_import_surfaces_strain_registry_review_candidates(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        client = TestClient(app)

        response = client.post(
            "/api/legacy-workbook-imports",
            data={"kind": "animal"},
            files={
                "file": (
                    "animal-sheet.xlsx",
                    workbook_bytes(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        assert response.status_code == 200
        created = response.json()
        assert created["stored_rows"] == 2
        assert created["strain_registry_candidate_count"] == 1
        assert created["created_review_items"] == 3

        [legacy_import] = client.get("/api/legacy-workbook-imports").json()
        [candidate] = legacy_import["strain_registry_candidates"]
        assert candidate["candidate_type"] == "strain_registry_review"
        assert candidate["strain_raw"] == "ApoM Tg/Tg"
        assert candidate["normalized_candidate"]["gene_symbol"] == ""
        assert candidate["normalized_candidate"]["allele_name"] == ""

        reviews = client.get("/api/review-items").json()
        registry_reviews = [
            item
            for item in reviews
            if item["issue"] == "Legacy strain registry candidate requires review"
        ]
        assert len(registry_reviews) == 1
        assert registry_reviews[0]["assigned_role"] == "Strain Curator"
        assert "does not infer gene or allele" in registry_reviews[0]["review_reason"]
    finally:
        db.DB_PATH = old_db_path
