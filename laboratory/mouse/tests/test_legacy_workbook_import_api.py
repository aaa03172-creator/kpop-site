from __future__ import annotations

import json
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
        assert registry_reviews[0]["review_check_targets"] == [
            "Strain registry",
            "Raw strain/genotype",
            "Gene/allele link",
            "Workbook row evidence",
        ]
    finally:
        db.DB_PATH = old_db_path


def test_legacy_strain_registry_candidate_apply_requires_curated_values(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        client = TestClient(app)
        imported = client.post(
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
        assert imported.status_code == 200
        [registry_review] = [
            item
            for item in client.get("/api/review-items").json()
            if item["issue"] == "Legacy strain registry candidate requires review"
        ]

        response = client.post(
            f"/api/review-items/{registry_review['review_id']}/resolve",
            json={
                "resolution_note": "Reviewed legacy strain candidate.",
                "legacy_decision": "apply_strain_registry_candidate",
                "reviewed_strain_name": "ApoM Tg/Tg",
                "reviewed_gene_symbol": "ApoM",
            },
        )

        assert response.status_code == 400
        assert "allele name" in response.json()["detail"]
        still_open = [
            item
            for item in client.get("/api/review-items").json()
            if item["review_id"] == registry_review["review_id"]
        ][0]
        assert still_open["status"] == "open"
        assert client.get("/api/strains").json() == []
    finally:
        db.DB_PATH = old_db_path


def test_legacy_strain_registry_candidate_apply_requires_source_traceability(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO parse_result
                    (parse_id, photo_id, source_name, raw_payload, parsed_at, status, confidence, needs_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("parse_without_legacy_source", None, "test", "{}", "2026-05-09T00:00:00Z", "review", 0.8, 1),
            )
            conn.execute(
                """
                INSERT INTO review_queue
                    (review_id, parse_id, severity, issue, current_value, suggested_value,
                     review_reason, assigned_role, priority, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "review_missing_source_registry",
                    "parse_without_legacy_source",
                    "High",
                    "Legacy strain registry candidate requires review",
                    json.dumps({"strain_raw": "ApoM Tg/Tg"}),
                    "",
                    "Legacy candidate requires curated source-backed registry values.",
                    "Strain Curator",
                    "high",
                    "open",
                    "2026-05-09T00:00:00Z",
                ),
            )

        client = TestClient(app)
        response = client.post(
            "/api/review-items/review_missing_source_registry/resolve",
            json={
                "resolution_note": "Attempt source-less apply.",
                "legacy_decision": "apply_strain_registry_candidate",
                "reviewed_strain_name": "ApoM Tg/Tg",
                "reviewed_gene_symbol": "ApoM",
                "reviewed_allele_name": "Tg transgene",
            },
        )

        assert response.status_code == 400
        assert "source record" in response.json()["detail"]
        assert client.get("/api/strains").json() == []
        assert client.get("/api/genes").json() == []
        assert client.get("/api/alleles").json() == []
    finally:
        db.DB_PATH = old_db_path


def test_legacy_strain_registry_candidate_apply_requires_explicit_existing_strain_mapping(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        client = TestClient(app)
        imported = client.post(
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
        assert imported.status_code == 200
        with db.connection() as conn:
            conn.execute(
                """
                INSERT INTO strain_registry
                    (strain_id, strain_name, source, status, source_record_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "strain_existing_apom",
                    "ApoM Tg/Tg",
                    "manual",
                    "active",
                    imported.json()["source_record_id"],
                    "2026-05-09T00:00:00Z",
                    "2026-05-09T00:00:00Z",
                ),
            )
        [registry_review] = [
            item
            for item in client.get("/api/review-items").json()
            if item["issue"] == "Legacy strain registry candidate requires review"
        ]

        response = client.post(
            f"/api/review-items/{registry_review['review_id']}/resolve",
            json={
                "resolution_note": "Curated ApoM candidate but did not map the existing strain.",
                "legacy_decision": "apply_strain_registry_candidate",
                "reviewed_strain_name": "ApoM Tg/Tg",
                "reviewed_gene_symbol": "ApoM",
                "reviewed_allele_name": "Tg transgene",
            },
        )

        assert response.status_code == 400
        assert "canonical_entity_id" in response.json()["detail"]
        assert client.get("/api/genes").json() == []
        assert client.get("/api/alleles").json() == []
        with db.connection() as conn:
            relationships = conn.execute("SELECT * FROM strain_allele_relationship").fetchall()
        assert relationships == []
    finally:
        db.DB_PATH = old_db_path


def test_legacy_strain_registry_candidate_apply_creates_source_backed_registry_link(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        client = TestClient(app)
        imported = client.post(
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
        assert imported.status_code == 200
        source_record_id = imported.json()["source_record_id"]
        [registry_review] = [
            item
            for item in client.get("/api/review-items").json()
            if item["issue"] == "Legacy strain registry candidate requires review"
        ]

        response = client.post(
            f"/api/review-items/{registry_review['review_id']}/resolve",
            json={
                "resolution_note": "Curated ApoM legacy workbook candidate into registry.",
                "legacy_decision": "apply_strain_registry_candidate",
                "reviewed_strain_name": "ApoM Tg/Tg",
                "reviewed_gene_symbol": "ApoM",
                "reviewed_allele_name": "Tg transgene",
                "resolved_value": "ApoM / Tg transgene",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        applied = payload["strain_registry_apply"]
        assert applied["strain_name"] == "ApoM Tg/Tg"
        assert applied["gene_symbol"] == "ApoM"
        assert applied["allele_name"] == "Tg transgene"
        assert applied["source_record_id"] == source_record_id

        [strain] = client.get("/api/strains").json()
        [gene] = client.get("/api/genes").json()
        [allele] = client.get("/api/alleles").json()
        assert strain["strain_name"] == "ApoM Tg/Tg"
        assert strain["source_record_id"] == source_record_id
        assert strain["alleles"] == [
            {
                "allele_id": allele["allele_id"],
                "gene_id": gene["gene_id"],
                "gene_symbol": "ApoM",
                "allele_name": "Tg transgene",
                "default_zygosity": "",
                "note": "",
            }
        ]
        assert gene["source_record_id"] == source_record_id
        assert allele["source_record_id"] == source_record_id

        resolved = [
            item
            for item in client.get("/api/review-items").json()
            if item["review_id"] == registry_review["review_id"]
        ][0]
        assert resolved["status"] == "resolved"

        with db.connection() as conn:
            action = conn.execute(
                """
                SELECT before_value, after_value
                FROM action_log
                WHERE action_type = 'legacy_strain_registry_candidate_applied'
                """
            ).fetchone()
        assert action is not None
        before = json.loads(action["before_value"])
        after = json.loads(action["after_value"])
        assert before["candidate"]["strain_raw"] == "ApoM Tg/Tg"
        assert before["review_status"] == "open"
        assert after["strain_name"] == "ApoM Tg/Tg"
        assert after["allele_name"] == "Tg transgene"
        assert after["source_record_id"] == source_record_id
        assert after["boundary"] == "canonical structured state"
    finally:
        db.DB_PATH = old_db_path


def test_legacy_strain_registry_candidate_apply_reuses_existing_strain_without_overwriting_raw_fields(tmp_path: Path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        client = TestClient(app)
        existing = client.post(
            "/api/strains",
            json={
                "strain_name": "ApoM Tg/Tg",
                "gene": "ExistingGene",
                "allele": "ExistingAllele",
            },
        )
        assert existing.status_code == 200
        existing_strain_id = existing.json()["strain_id"]
        imported = client.post(
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
        assert imported.status_code == 200
        [registry_review] = [
            item
            for item in client.get("/api/review-items").json()
            if item["issue"] == "Legacy strain registry candidate requires review"
        ]

        response = client.post(
            f"/api/review-items/{registry_review['review_id']}/resolve",
            json={
                "resolution_note": "Link reviewed legacy candidate to existing strain.",
                "legacy_decision": "apply_strain_registry_candidate",
                "canonical_entity_type": "strain",
                "canonical_entity_id": existing_strain_id,
                "reviewed_strain_name": "ApoM Tg/Tg",
                "reviewed_gene_symbol": "ApoM",
                "reviewed_allele_name": "Tg transgene",
            },
        )

        assert response.status_code == 200
        assert response.json()["strain_registry_apply"]["created_strain"] is False
        strains = client.get("/api/strains").json()
        assert len(strains) == 1
        assert strains[0]["gene"] == "ExistingGene"
        assert strains[0]["allele"] == "ExistingAllele"
        assert any(link["gene_symbol"] == "ApoM" and link["allele_name"] == "Tg transgene" for link in strains[0]["alleles"])
    finally:
        db.DB_PATH = old_db_path
