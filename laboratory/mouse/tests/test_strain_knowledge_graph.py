from __future__ import annotations

from fastapi.testclient import TestClient

from app import db
from app.main import app


def test_strain_creation_populates_normalized_gene_allele_registry(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        client = TestClient(app)

        response = client.post(
            "/api/strains",
            json={
                "strain_name": "PV-Cre",
                "common_name": "PV-Cre line",
                "gene": "Pvalb",
                "allele": "Pvalb-IRES-Cre",
                "background": "C57BL/6J",
                "source": "manual",
                "status": "active",
            },
        )

        assert response.status_code == 200
        strain_id = response.json()["strain_id"]

        genes = client.get("/api/genes").json()
        alleles = client.get("/api/alleles").json()
        strains = client.get("/api/strains").json()

        assert genes == [
            {
                "gene_id": genes[0]["gene_id"],
                "gene_symbol": "Pvalb",
                "full_name": "",
                "organism": "mouse",
                "description": "",
                "external_reference": "",
                "source_record_id": response.json()["source_record_id"],
                "created_at": genes[0]["created_at"],
                "updated_at": genes[0]["updated_at"],
            }
        ]
        assert alleles == [
            {
                "allele_id": alleles[0]["allele_id"],
                "gene_id": genes[0]["gene_id"],
                "gene_symbol": "Pvalb",
                "allele_name": "Pvalb-IRES-Cre",
                "allele_type": "",
                "description": "",
                "inheritance": "",
                "zygosity_options": "",
                "genotyping_protocol": "",
                "source_record_id": response.json()["source_record_id"],
                "created_at": alleles[0]["created_at"],
                "updated_at": alleles[0]["updated_at"],
            }
        ]
        assert strains[0]["strain_id"] == strain_id
        assert strains[0]["gene"] == "Pvalb"
        assert strains[0]["allele"] == "Pvalb-IRES-Cre"
        assert strains[0]["alleles"] == [
            {
                "allele_id": alleles[0]["allele_id"],
                "gene_id": genes[0]["gene_id"],
                "gene_symbol": "Pvalb",
                "allele_name": "Pvalb-IRES-Cre",
                "default_zygosity": "",
                "note": "",
            }
        ]
    finally:
        db.DB_PATH = old_db_path


def test_strain_creation_reuses_gene_and_allele_records_case_insensitively(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        client = TestClient(app)

        first = client.post(
            "/api/strains",
            json={"strain_name": "PV-Cre", "gene": "Pvalb", "allele": "Pvalb-IRES-Cre"},
        )
        second = client.post(
            "/api/strains",
            json={"strain_name": "PV-Cre backup", "gene": "pvalb", "allele": "pvalb-ires-cre"},
        )

        assert first.status_code == 200
        assert second.status_code == 200
        genes = client.get("/api/genes").json()
        alleles = client.get("/api/alleles").json()
        strains = client.get("/api/strains").json()

        assert len(genes) == 1
        assert genes[0]["gene_symbol"] == "Pvalb"
        assert len(alleles) == 1
        assert alleles[0]["allele_name"] == "Pvalb-IRES-Cre"
        assert len(strains) == 2
        assert all(row["alleles"][0]["allele_id"] == alleles[0]["allele_id"] for row in strains)
    finally:
        db.DB_PATH = old_db_path


def test_gene_and_allele_metadata_updates_preserve_raw_symbols_and_source(tmp_path) -> None:
    old_db_path = db.DB_PATH
    db.DB_PATH = tmp_path / "mouse_lims.sqlite"
    try:
        db.init_db()
        client = TestClient(app)

        created = client.post(
            "/api/strains",
            json={"strain_name": "PV-Cre", "gene": "Pvalb", "allele": "Pvalb-IRES-Cre"},
        )
        assert created.status_code == 200
        source_record_id = created.json()["source_record_id"]
        gene = client.get("/api/genes").json()[0]
        allele = client.get("/api/alleles").json()[0]

        gene_update = client.patch(
            f"/api/genes/{gene['gene_id']}",
            json={"full_name": "Parvalbumin", "description": "Curated display metadata."},
        )
        allele_update = client.patch(
            f"/api/alleles/{allele['allele_id']}",
            json={"description": "IRES-Cre driver allele", "allele_type": "transgene"},
        )

        assert gene_update.status_code == 200
        assert allele_update.status_code == 200
        updated_gene = client.get("/api/genes").json()[0]
        updated_allele = client.get("/api/alleles").json()[0]
        strain = client.get("/api/strains").json()[0]

        assert updated_gene["gene_symbol"] == "Pvalb"
        assert updated_gene["full_name"] == "Parvalbumin"
        assert updated_gene["description"] == "Curated display metadata."
        assert updated_gene["source_record_id"] == source_record_id
        assert updated_allele["allele_name"] == "Pvalb-IRES-Cre"
        assert updated_allele["description"] == "IRES-Cre driver allele"
        assert updated_allele["allele_type"] == "transgene"
        assert updated_allele["source_record_id"] == source_record_id
        assert strain["gene"] == "Pvalb"
        assert strain["allele"] == "Pvalb-IRES-Cre"
        assert strain["alleles"][0]["gene_symbol"] == "Pvalb"
        assert strain["alleles"][0]["allele_name"] == "Pvalb-IRES-Cre"
    finally:
        db.DB_PATH = old_db_path
