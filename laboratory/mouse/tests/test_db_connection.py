from __future__ import annotations

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
