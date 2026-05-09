from __future__ import annotations

import sqlite3

import pytest

from app import db


class FakeConnection:
    def __init__(self) -> None:
        self.row_factory = None
        self.executed: list[str] = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, sql: str):
        self.executed.append(sql)
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_connection_rolls_back_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeConnection()
    monkeypatch.setattr(db.sqlite3, "connect", lambda _: fake)

    with pytest.raises(RuntimeError):
        with db.connection():
            raise RuntimeError("forced write failure")

    assert fake.rolled_back is True
    assert fake.committed is False
    assert fake.closed is True


def test_connection_commits_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeConnection()
    monkeypatch.setattr(db.sqlite3, "connect", lambda _: fake)

    with db.connection():
        pass

    assert fake.committed is True
    assert fake.rolled_back is False
    assert fake.closed is True


def test_init_db_migrates_non_empty_legacy_tables_with_timestamp_columns(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "mouse_lims.sqlite")

    legacy_conn = sqlite3.connect(db.DB_PATH)
    try:
        legacy_conn.executescript(
            """
            CREATE TABLE mouse_master (
                mouse_id TEXT PRIMARY KEY,
                display_id TEXT NOT NULL
            );
            INSERT INTO mouse_master (mouse_id, display_id)
            VALUES ('legacy_mouse_001', 'LM001');

            CREATE TABLE card_note_item_log (
                note_item_id TEXT PRIMARY KEY,
                raw_line_text TEXT NOT NULL
            );
            INSERT INTO card_note_item_log (note_item_id, raw_line_text)
            VALUES ('legacy_note_001', '1 R''');

            CREATE TABLE genotyping_record (
                genotyping_id TEXT PRIMARY KEY,
                mouse_id TEXT,
                sample_id TEXT,
                sample_date TEXT,
                result_date TEXT,
                created_at TEXT
            );
            INSERT INTO genotyping_record (
                genotyping_id,
                mouse_id,
                sample_id,
                sample_date,
                result_date,
                created_at
            )
            VALUES ('legacy_genotype_001', 'legacy_mouse_001', 'LM001', '', '', '');
            """
        )
        legacy_conn.commit()
    finally:
        legacy_conn.close()

    db.init_db()

    migrated_conn = sqlite3.connect(db.DB_PATH)
    migrated_conn.row_factory = sqlite3.Row
    try:
        mouse_row = migrated_conn.execute(
            """
            SELECT created_at, updated_at
            FROM mouse_master
            WHERE mouse_id = 'legacy_mouse_001'
            """
        ).fetchone()
        note_row = migrated_conn.execute(
            """
            SELECT created_at
            FROM card_note_item_log
            WHERE note_item_id = 'legacy_note_001'
            """
        ).fetchone()
        genotype_row = migrated_conn.execute(
            """
            SELECT updated_at
            FROM genotyping_record
            WHERE genotyping_id = 'legacy_genotype_001'
            """
        ).fetchone()
    finally:
        migrated_conn.close()

    assert mouse_row["created_at"]
    assert mouse_row["updated_at"]
    assert note_row["created_at"]
    assert genotype_row["updated_at"]
