from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "mousedb.sqlite"


def db_path() -> Path:
    configured = os.environ.get("MOUSEDB_PATH")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB_PATH


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS id_sequence (
                entity TEXT NOT NULL,
                year TEXT NOT NULL DEFAULT '',
                next_value INTEGER NOT NULL,
                PRIMARY KEY (entity, year)
            );

            CREATE TABLE IF NOT EXISTS strain (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strain_id TEXT NOT NULL UNIQUE,
                strain_name TEXT NOT NULL,
                common_name TEXT NOT NULL DEFAULT '',
                official_name TEXT NOT NULL DEFAULT '',
                strain_type TEXT NOT NULL DEFAULT '',
                background TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                source_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                description TEXT NOT NULL DEFAULT '',
                breeding_difficulty TEXT NOT NULL DEFAULT '',
                genotyping_complexity TEXT NOT NULL DEFAULT '',
                phenotype_summary TEXT NOT NULL DEFAULT '',
                special_handling_note TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT '',
                date_acquired TEXT,
                date_archived TEXT,
                source_type TEXT NOT NULL DEFAULT 'manual_entry',
                source_ref TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                reviewed_status TEXT NOT NULL DEFAULT 'accepted',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS gene (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gene_id TEXT NOT NULL UNIQUE,
                gene_symbol TEXT NOT NULL,
                full_name TEXT NOT NULL DEFAULT '',
                organism TEXT NOT NULL DEFAULT 'mouse',
                description TEXT NOT NULL DEFAULT '',
                external_reference TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS allele (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                allele_id TEXT NOT NULL UNIQUE,
                gene_id TEXT,
                allele_name TEXT NOT NULL,
                allele_type TEXT NOT NULL DEFAULT 'other',
                description TEXT NOT NULL DEFAULT '',
                inheritance TEXT NOT NULL DEFAULT '',
                zygosity_options TEXT NOT NULL DEFAULT '',
                genotyping_protocol TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (gene_id) REFERENCES gene(gene_id)
            );

            CREATE TABLE IF NOT EXISTS strain_allele (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strain_allele_id TEXT NOT NULL UNIQUE,
                strain_id TEXT NOT NULL,
                allele_id TEXT NOT NULL,
                default_zygosity TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (strain_id) REFERENCES strain(strain_id),
                FOREIGN KEY (allele_id) REFERENCES allele(allele_id)
            );

            CREATE TABLE IF NOT EXISTS cage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cage_id TEXT NOT NULL UNIQUE,
                cage_label TEXT NOT NULL UNIQUE,
                location TEXT NOT NULL DEFAULT '',
                rack TEXT NOT NULL DEFAULT '',
                shelf TEXT NOT NULL DEFAULT '',
                cage_type TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                note TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'manual_entry',
                source_ref TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                reviewed_status TEXT NOT NULL DEFAULT 'accepted',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS litter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                litter_id TEXT NOT NULL UNIQUE,
                litter_label TEXT NOT NULL DEFAULT '',
                mating_id TEXT,
                birth_date TEXT,
                number_born INTEGER NOT NULL DEFAULT 0,
                number_alive INTEGER NOT NULL DEFAULT 0,
                number_weaned INTEGER NOT NULL DEFAULT 0,
                weaning_date TEXT,
                status TEXT NOT NULL DEFAULT 'born',
                note TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'manual_entry',
                source_ref TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                reviewed_status TEXT NOT NULL DEFAULT 'accepted',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS mouse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mouse_id TEXT NOT NULL UNIQUE,
                display_id TEXT NOT NULL,
                strain_id TEXT,
                sex TEXT NOT NULL DEFAULT 'unknown',
                date_of_birth TEXT,
                father_id TEXT,
                mother_id TEXT,
                litter_id TEXT,
                current_cage_id TEXT,
                current_status TEXT NOT NULL DEFAULT 'alive',
                current_use TEXT NOT NULL DEFAULT 'unknown',
                current_genotype_summary TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'manual_entry',
                source_ref TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                reviewed_status TEXT NOT NULL DEFAULT 'accepted',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strain_id) REFERENCES strain(strain_id),
                FOREIGN KEY (father_id) REFERENCES mouse(mouse_id),
                FOREIGN KEY (mother_id) REFERENCES mouse(mouse_id),
                FOREIGN KEY (litter_id) REFERENCES litter(litter_id),
                FOREIGN KEY (current_cage_id) REFERENCES cage(cage_id)
            );

            CREATE TABLE IF NOT EXISTS mating (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mating_id TEXT NOT NULL UNIQUE,
                mating_label TEXT NOT NULL DEFAULT '',
                male_mouse_id TEXT,
                female_mouse_id TEXT,
                second_female_mouse_id TEXT,
                strain_goal TEXT NOT NULL DEFAULT '',
                expected_genotype TEXT NOT NULL DEFAULT '',
                start_date TEXT,
                end_date TEXT,
                status TEXT NOT NULL DEFAULT 'planned',
                purpose TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'manual_entry',
                source_ref TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                reviewed_status TEXT NOT NULL DEFAULT 'accepted',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (male_mouse_id) REFERENCES mouse(mouse_id),
                FOREIGN KEY (female_mouse_id) REFERENCES mouse(mouse_id),
                FOREIGN KEY (second_female_mouse_id) REFERENCES mouse(mouse_id)
            );

            CREATE TABLE IF NOT EXISTS genotype_result (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                genotype_result_id TEXT NOT NULL UNIQUE,
                mouse_id TEXT NOT NULL,
                allele_id TEXT,
                sample_id TEXT NOT NULL DEFAULT '',
                test_date TEXT,
                result TEXT NOT NULL DEFAULT 'unknown',
                zygosity TEXT NOT NULL DEFAULT '',
                method TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'accepted',
                performed_by TEXT NOT NULL DEFAULT '',
                confirmed_by TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'manual_entry',
                source_ref TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                reviewed_status TEXT NOT NULL DEFAULT 'accepted',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mouse_id) REFERENCES mouse(mouse_id),
                FOREIGN KEY (allele_id) REFERENCES allele(allele_id)
            );

            CREATE TABLE IF NOT EXISTS mouse_event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                mouse_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_date TEXT NOT NULL,
                related_entity_type TEXT NOT NULL DEFAULT '',
                related_entity_id TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                previous_value TEXT,
                new_value TEXT,
                source_type TEXT NOT NULL DEFAULT 'manual_entry',
                source_ref TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                reviewed_status TEXT NOT NULL DEFAULT 'accepted',
                created_by TEXT NOT NULL DEFAULT 'local_user',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mouse_id) REFERENCES mouse(mouse_id)
            );

            CREATE INDEX IF NOT EXISTS idx_mouse_strain ON mouse(strain_id);
            CREATE INDEX IF NOT EXISTS idx_mouse_status ON mouse(current_status);
            CREATE INDEX IF NOT EXISTS idx_mouse_cage ON mouse(current_cage_id);
            CREATE INDEX IF NOT EXISTS idx_mouse_event_mouse ON mouse_event(mouse_id, event_date);
            CREATE INDEX IF NOT EXISTS idx_genotype_mouse ON genotype_result(mouse_id);
            CREATE INDEX IF NOT EXISTS idx_mating_status ON mating(status);
            CREATE INDEX IF NOT EXISTS idx_litter_status ON litter(status);
            """
        )
