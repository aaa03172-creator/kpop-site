from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "mouse_lims.sqlite"


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
            """
        )
