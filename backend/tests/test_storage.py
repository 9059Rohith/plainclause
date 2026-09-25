"""Regression checks for SQLite resource lifetime."""

import sqlite3

import pytest

from app.storage import Store


def test_store_closes_connection_after_transaction(tmp_path):
    database = tmp_path / "closed.db"
    store = Store(database)

    with store.connect() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")

    database.unlink()
