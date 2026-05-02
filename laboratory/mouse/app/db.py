from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "mouse_lims.sqlite"


EAR_LABEL_MASTER_SEEDS = [
    ("R_PRIME", "R'", "right ear prime mark"),
    ("L_PRIME", "L'", "left ear prime mark"),
    ("R_CIRCLE", "R\u00b0", "right ear circle mark"),
    ("L_CIRCLE", "L\u00b0", "left ear circle mark"),
    ("R_PRIME_L_PRIME", "R'L'", "right prime + left prime"),
    ("R_CIRCLE_L_CIRCLE", "R\u00b0L\u00b0", "right circle + left circle"),
    ("R_PRIME_L_CIRCLE", "R'L\u00b0", "right prime + left circle"),
    ("R_CIRCLE_L_PRIME", "R\u00b0L'", "right circle + left prime"),
    ("NONE", "N", "no ear label / no mark"),
]


EAR_LABEL_ALIAS_SEEDS = [
    ("ear_alias_r_prime_ascii", "R'", "R_PRIME", 1.0, 1),
    ("ear_alias_r_prime_unicode", "R\u2032", "R_PRIME", 0.98, 1),
    ("ear_alias_r_prime_curly", "R\u2019", "R_PRIME", 0.98, 1),
    ("ear_alias_l_prime_ascii", "L'", "L_PRIME", 1.0, 1),
    ("ear_alias_l_prime_unicode", "L\u2032", "L_PRIME", 0.98, 1),
    ("ear_alias_l_prime_curly", "L\u2019", "L_PRIME", 0.98, 1),
    ("ear_alias_r_circle_degree", "R\u00b0", "R_CIRCLE", 1.0, 1),
    ("ear_alias_r_circle_ordinal", "R\u00ba", "R_CIRCLE", 0.92, 1),
    ("ear_alias_r_circle_ring", "R\u02da", "R_CIRCLE", 0.92, 1),
    ("ear_alias_l_circle_degree", "L\u00b0", "L_CIRCLE", 1.0, 1),
    ("ear_alias_l_circle_ordinal", "L\u00ba", "L_CIRCLE", 0.92, 1),
    ("ear_alias_l_circle_ring", "L\u02da", "L_CIRCLE", 0.92, 1),
    ("ear_alias_none_n", "N", "NONE", 1.0, 1),
    ("ear_alias_r_circle_zero", "R0", "R_CIRCLE", 0.65, 0),
    ("ear_alias_r_circle_o", "Ro", "R_CIRCLE", 0.65, 0),
    ("ear_alias_l_circle_zero", "L0", "L_CIRCLE", 0.65, 0),
    ("ear_alias_l_circle_o", "Lo", "L_CIRCLE", 0.65, 0),
]


def ensure_data_dirs() -> None:
    (DATA_DIR / "photos").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "exports").mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    ensure_data_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_columns(conn: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, definition in columns.items():
        if column_name not in existing:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def ensure_schema_compatibility(conn: sqlite3.Connection) -> None:
    ensure_columns(
        conn,
        "mouse_master",
        {
            "id_prefix": "TEXT NOT NULL DEFAULT ''",
            "strain_id": "TEXT",
            "raw_strain_text": "TEXT NOT NULL DEFAULT ''",
            "sex": "TEXT",
            "genotype": "TEXT",
            "genotype_status": "TEXT NOT NULL DEFAULT 'unknown'",
            "dob_raw": "TEXT",
            "dob_start": "TEXT",
            "dob_end": "TEXT",
            "ear_label_raw": "TEXT",
            "ear_label_code": "TEXT",
            "ear_label_confidence": "REAL",
            "ear_label_review_status": "TEXT NOT NULL DEFAULT 'auto_filled'",
            "sample_id": "TEXT",
            "sample_date": "TEXT",
            "genotyping_status": "TEXT NOT NULL DEFAULT 'not_sampled'",
            "genotype_result": "TEXT",
            "genotype_result_date": "TEXT",
            "target_match_status": "TEXT NOT NULL DEFAULT 'unknown'",
            "use_category": "TEXT NOT NULL DEFAULT 'unknown'",
            "next_action": "TEXT NOT NULL DEFAULT 'sample_needed'",
            "source_note_item_id": "TEXT",
            "current_card_snapshot_id": "TEXT",
            "status": "TEXT NOT NULL DEFAULT 'active'",
            "source_photo_id": "TEXT",
            "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )
    ensure_columns(
        conn,
        "card_note_item_log",
        {
            "photo_id": "TEXT",
            "parse_id": "TEXT",
            "card_snapshot_id": "TEXT",
            "card_type": "TEXT NOT NULL DEFAULT 'unknown'",
            "line_number": "INTEGER",
            "raw_line_text": "TEXT NOT NULL DEFAULT ''",
            "strike_status": "TEXT NOT NULL DEFAULT 'none'",
            "parsed_type": "TEXT NOT NULL DEFAULT 'unknown'",
            "interpreted_status": "TEXT NOT NULL DEFAULT 'unknown'",
            "parsed_mouse_display_id": "TEXT",
            "parsed_ear_label_raw": "TEXT",
            "parsed_ear_label_code": "TEXT",
            "parsed_ear_label_confidence": "REAL",
            "parsed_ear_label_review_status": "TEXT NOT NULL DEFAULT 'auto_filled'",
            "parsed_event_date": "TEXT",
            "parsed_count": "INTEGER",
            "confidence": "REAL NOT NULL DEFAULT 0",
            "needs_review": "INTEGER NOT NULL DEFAULT 0",
            "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )
    ensure_columns(
        conn,
        "genotyping_record",
        {
            "submitted_date": "TEXT",
            "target_name": "TEXT",
            "raw_result": "TEXT",
            "normalized_result": "TEXT",
            "result_status": "TEXT NOT NULL DEFAULT 'pending'",
            "source_photo_id": "TEXT",
            "confidence": "REAL NOT NULL DEFAULT 0",
            "notes": "TEXT",
            "updated_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        },
    )


def init_db() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS photo_log (
                photo_id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                status TEXT NOT NULL,
                raw_source_kind TEXT NOT NULL DEFAULT 'cage_card_photo'
            );

            CREATE TABLE IF NOT EXISTS parse_result (
                parse_id TEXT PRIMARY KEY,
                photo_id TEXT,
                source_name TEXT NOT NULL,
                raw_payload TEXT NOT NULL,
                parsed_at TEXT NOT NULL,
                status TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0,
                needs_review INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (photo_id) REFERENCES photo_log(photo_id)
            );

            CREATE TABLE IF NOT EXISTS review_queue (
                review_id TEXT PRIMARY KEY,
                parse_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                issue TEXT NOT NULL,
                current_value TEXT NOT NULL DEFAULT '',
                suggested_value TEXT NOT NULL DEFAULT '',
                review_reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                resolution_note TEXT,
                FOREIGN KEY (parse_id) REFERENCES parse_result(parse_id)
            );

            CREATE TABLE IF NOT EXISTS action_log (
                action_id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                before_value TEXT,
                after_value TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS source_record (
                source_record_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_uri TEXT NOT NULL DEFAULT '',
                source_label TEXT NOT NULL DEFAULT '',
                raw_payload TEXT NOT NULL DEFAULT '',
                imported_at TEXT NOT NULL,
                checksum TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS strain_registry (
                strain_id TEXT PRIMARY KEY,
                strain_name TEXT NOT NULL,
                common_name TEXT NOT NULL DEFAULT '',
                official_name TEXT NOT NULL DEFAULT '',
                gene TEXT NOT NULL DEFAULT '',
                allele TEXT NOT NULL DEFAULT '',
                background TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                breeding_note TEXT NOT NULL DEFAULT '',
                genotyping_note TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT '',
                source_record_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id)
            );

            CREATE TABLE IF NOT EXISTS correction_log (
                correction_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                before_value TEXT NOT NULL DEFAULT '',
                after_value TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                source_record_id TEXT,
                review_id TEXT,
                corrected_at TEXT NOT NULL,
                FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id),
                FOREIGN KEY (review_id) REFERENCES review_queue(review_id)
            );

            CREATE TABLE IF NOT EXISTS export_log (
                export_id TEXT PRIMARY KEY,
                export_type TEXT NOT NULL,
                filename TEXT NOT NULL,
                query TEXT NOT NULL DEFAULT '',
                row_count INTEGER NOT NULL DEFAULT 0,
                blocked_review_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'generated',
                exported_at TEXT NOT NULL,
                source_layer TEXT NOT NULL DEFAULT 'export or view',
                note TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS mouse_event (
                event_id TEXT PRIMARY KEY,
                mouse_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_date TEXT NOT NULL,
                related_entity_type TEXT NOT NULL DEFAULT '',
                related_entity_id TEXT NOT NULL DEFAULT '',
                source_record_id TEXT,
                details TEXT NOT NULL DEFAULT '{}',
                created_by TEXT NOT NULL DEFAULT 'local_user',
                created_at TEXT NOT NULL,
                FOREIGN KEY (mouse_id) REFERENCES mouse_master(mouse_id),
                FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id)
            );

            CREATE TABLE IF NOT EXISTS genotyping_record (
                genotyping_id TEXT PRIMARY KEY,
                mouse_id TEXT,
                sample_id TEXT NOT NULL DEFAULT '',
                sample_date TEXT,
                submitted_date TEXT,
                result_date TEXT,
                target_name TEXT NOT NULL DEFAULT '',
                raw_result TEXT NOT NULL DEFAULT '',
                normalized_result TEXT NOT NULL DEFAULT '',
                result_status TEXT NOT NULL DEFAULT 'pending',
                source_photo_id TEXT,
                confidence REAL NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (mouse_id) REFERENCES mouse_master(mouse_id),
                FOREIGN KEY (source_photo_id) REFERENCES photo_log(photo_id)
            );

            CREATE TABLE IF NOT EXISTS strain_target_genotype (
                target_id TEXT PRIMARY KEY,
                strain_text TEXT NOT NULL,
                target_genotype TEXT NOT NULL,
                purpose TEXT NOT NULL DEFAULT 'unknown',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE (strain_text, target_genotype, purpose)
            );

            CREATE TABLE IF NOT EXISTS cage_registry (
                cage_id TEXT PRIMARY KEY,
                cage_label TEXT NOT NULL UNIQUE,
                location TEXT NOT NULL DEFAULT '',
                rack TEXT NOT NULL DEFAULT '',
                shelf TEXT NOT NULL DEFAULT '',
                cage_type TEXT NOT NULL DEFAULT 'holding',
                status TEXT NOT NULL DEFAULT 'active',
                note TEXT NOT NULL DEFAULT '',
                source_record_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id)
            );

            CREATE TABLE IF NOT EXISTS mouse_cage_assignment (
                assignment_id TEXT PRIMARY KEY,
                mouse_id TEXT NOT NULL,
                cage_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                assigned_at TEXT NOT NULL,
                ended_at TEXT,
                source_record_id TEXT,
                note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (mouse_id) REFERENCES mouse_master(mouse_id),
                FOREIGN KEY (cage_id) REFERENCES cage_registry(cage_id),
                FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id)
            );

            CREATE TABLE IF NOT EXISTS mating_registry (
                mating_id TEXT PRIMARY KEY,
                mating_label TEXT NOT NULL,
                strain_goal TEXT NOT NULL DEFAULT '',
                expected_genotype TEXT NOT NULL DEFAULT '',
                start_date TEXT NOT NULL DEFAULT '',
                end_date TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                purpose TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                source_record_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id)
            );

            CREATE TABLE IF NOT EXISTS mating_mouse (
                mating_mouse_id TEXT PRIMARY KEY,
                mating_id TEXT NOT NULL,
                mouse_id TEXT NOT NULL,
                role TEXT NOT NULL,
                joined_date TEXT NOT NULL DEFAULT '',
                removed_date TEXT,
                note TEXT NOT NULL DEFAULT '',
                source_record_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (mating_id) REFERENCES mating_registry(mating_id),
                FOREIGN KEY (mouse_id) REFERENCES mouse_master(mouse_id),
                FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id)
            );

            CREATE TABLE IF NOT EXISTS litter_registry (
                litter_id TEXT PRIMARY KEY,
                litter_label TEXT NOT NULL,
                mating_id TEXT NOT NULL,
                birth_date TEXT NOT NULL DEFAULT '',
                number_born INTEGER,
                number_alive INTEGER,
                number_weaned INTEGER,
                weaning_date TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'born',
                note TEXT NOT NULL DEFAULT '',
                source_record_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (mating_id) REFERENCES mating_registry(mating_id),
                FOREIGN KEY (source_record_id) REFERENCES source_record(source_record_id)
            );

            CREATE TABLE IF NOT EXISTS my_assigned_strain (
                assigned_strain_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                aliases_json TEXT NOT NULL DEFAULT '[]',
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_reference TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                assigned_at TEXT NOT NULL,
                removed_at TEXT,
                notes TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS distribution_import (
                distribution_import_id TEXT PRIMARY KEY,
                source_file_name TEXT NOT NULL,
                source_file_path TEXT NOT NULL DEFAULT '',
                received_date TEXT NOT NULL DEFAULT '',
                sheet_name TEXT NOT NULL DEFAULT '',
                imported_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'parsed',
                notes TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS distribution_assignment_row (
                assignment_row_id TEXT PRIMARY KEY,
                distribution_import_id TEXT NOT NULL,
                source_sheet TEXT NOT NULL DEFAULT '',
                source_row_number INTEGER,
                institution_or_group TEXT NOT NULL DEFAULT '',
                responsible_person_raw TEXT NOT NULL DEFAULT '',
                mating_type_raw TEXT NOT NULL DEFAULT '',
                matched_strain_id TEXT,
                cage_count_raw TEXT NOT NULL DEFAULT '',
                mating_cage_count_raw TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0,
                review_status TEXT NOT NULL DEFAULT 'candidate',
                traceability TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (distribution_import_id) REFERENCES distribution_import(distribution_import_id)
            );

            CREATE TABLE IF NOT EXISTS ear_label_master (
                ear_label_code TEXT PRIMARY KEY,
                display_text TEXT NOT NULL,
                meaning TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ear_label_alias (
                alias_id TEXT PRIMARY KEY,
                raw_text TEXT NOT NULL,
                ear_label_code TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0,
                confirmed INTEGER NOT NULL DEFAULT 0,
                hit_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ear_label_code) REFERENCES ear_label_master(ear_label_code),
                UNIQUE (raw_text, ear_label_code)
            );

            CREATE TABLE IF NOT EXISTS card_note_item_log (
                note_item_id TEXT PRIMARY KEY,
                photo_id TEXT,
                parse_id TEXT,
                card_snapshot_id TEXT,
                card_type TEXT NOT NULL DEFAULT 'unknown',
                line_number INTEGER,
                raw_line_text TEXT NOT NULL,
                strike_status TEXT NOT NULL DEFAULT 'none',
                parsed_type TEXT NOT NULL DEFAULT 'unknown',
                interpreted_status TEXT NOT NULL DEFAULT 'unknown',
                parsed_mouse_display_id TEXT,
                parsed_ear_label_raw TEXT,
                parsed_ear_label_code TEXT,
                parsed_ear_label_confidence REAL,
                parsed_ear_label_review_status TEXT NOT NULL DEFAULT 'auto_filled',
                parsed_event_date TEXT,
                parsed_count INTEGER,
                confidence REAL NOT NULL DEFAULT 0,
                needs_review INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photo_log(photo_id),
                FOREIGN KEY (parse_id) REFERENCES parse_result(parse_id),
                FOREIGN KEY (parsed_ear_label_code) REFERENCES ear_label_master(ear_label_code)
            );

            CREATE TABLE IF NOT EXISTS mouse_master (
                mouse_id TEXT PRIMARY KEY,
                display_id TEXT NOT NULL,
                id_prefix TEXT NOT NULL DEFAULT '',
                strain_id TEXT,
                raw_strain_text TEXT NOT NULL DEFAULT '',
                sex TEXT,
                genotype TEXT,
                genotype_status TEXT NOT NULL DEFAULT 'unknown',
                dob_raw TEXT,
                dob_start TEXT,
                dob_end TEXT,
                ear_label_raw TEXT,
                ear_label_code TEXT,
                ear_label_confidence REAL,
                ear_label_review_status TEXT NOT NULL DEFAULT 'auto_filled',
                sample_id TEXT,
                sample_date TEXT,
                genotyping_status TEXT NOT NULL DEFAULT 'not_sampled',
                genotype_result TEXT,
                genotype_result_date TEXT,
                target_match_status TEXT NOT NULL DEFAULT 'unknown',
                use_category TEXT NOT NULL DEFAULT 'unknown',
                next_action TEXT NOT NULL DEFAULT 'sample_needed',
                source_note_item_id TEXT,
                current_card_snapshot_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                source_photo_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ear_label_code) REFERENCES ear_label_master(ear_label_code),
                FOREIGN KEY (source_photo_id) REFERENCES photo_log(photo_id)
            );
            """
        )
        ensure_schema_compatibility(conn)
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_card_note_item_log_photo_line
                ON card_note_item_log(photo_id, line_number);
            CREATE INDEX IF NOT EXISTS idx_card_note_item_log_mouse
                ON card_note_item_log(parsed_mouse_display_id);
            CREATE INDEX IF NOT EXISTS idx_mouse_master_display
                ON mouse_master(display_id);
            CREATE INDEX IF NOT EXISTS idx_mouse_master_identity_candidate
                ON mouse_master(display_id, raw_strain_text, dob_start, dob_end, ear_label_code);
            CREATE INDEX IF NOT EXISTS idx_mouse_master_sample
                ON mouse_master(sample_id);
            CREATE INDEX IF NOT EXISTS idx_distribution_assignment_import
                ON distribution_assignment_row(distribution_import_id, source_row_number);
            CREATE INDEX IF NOT EXISTS idx_strain_registry_name
                ON strain_registry(strain_name COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_source_record_type
                ON source_record(source_type, imported_at);
            CREATE INDEX IF NOT EXISTS idx_correction_log_entity
                ON correction_log(entity_type, entity_id, corrected_at);
            CREATE INDEX IF NOT EXISTS idx_export_log_type_time
                ON export_log(export_type, exported_at);
            CREATE INDEX IF NOT EXISTS idx_mouse_event_mouse
                ON mouse_event(mouse_id, event_date);
            CREATE INDEX IF NOT EXISTS idx_genotyping_record_mouse
                ON genotyping_record(mouse_id, sample_id);
            CREATE INDEX IF NOT EXISTS idx_strain_target_genotype_strain
                ON strain_target_genotype(strain_text, active);
            CREATE INDEX IF NOT EXISTS idx_cage_registry_label
                ON cage_registry(cage_label COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_mouse_cage_assignment_active
                ON mouse_cage_assignment(mouse_id, status, assigned_at);
            CREATE INDEX IF NOT EXISTS idx_mating_registry_status
                ON mating_registry(status, start_date);
            CREATE INDEX IF NOT EXISTS idx_mating_mouse_mating
                ON mating_mouse(mating_id, role);
            CREATE INDEX IF NOT EXISTS idx_mating_mouse_mouse
                ON mating_mouse(mouse_id, joined_date);
            CREATE INDEX IF NOT EXISTS idx_litter_registry_mating
                ON litter_registry(mating_id, birth_date);
            """
        )
        conn.executemany(
            """
            INSERT OR IGNORE INTO ear_label_master
                (ear_label_code, display_text, meaning)
            VALUES (?, ?, ?)
            """,
            EAR_LABEL_MASTER_SEEDS,
        )
        conn.executemany(
            """
            INSERT OR IGNORE INTO ear_label_alias
                (alias_id, raw_text, ear_label_code, confidence, confirmed)
            VALUES (?, ?, ?, ?, ?)
            """,
            EAR_LABEL_ALIAS_SEEDS,
        )
