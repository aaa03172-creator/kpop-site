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
