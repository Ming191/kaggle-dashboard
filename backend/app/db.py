from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import AccountSnapshot


def _connect(database_path: str) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database_path: str) -> None:
    with _connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS account_snapshots (
                account_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                checked_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )


def upsert_snapshot(database_path: str, snapshot: AccountSnapshot) -> None:
    payload = snapshot.model_dump_json()
    with _connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO account_snapshots(account_id, name, status, error, checked_at, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET
                name = excluded.name,
                status = excluded.status,
                error = excluded.error,
                checked_at = excluded.checked_at,
                payload = excluded.payload
            """,
            (
                snapshot.account_id,
                snapshot.name,
                snapshot.status,
                snapshot.error,
                snapshot.checked_at.isoformat(),
                payload,
            ),
        )


def list_snapshots(database_path: str) -> list[dict]:
    with _connect(database_path) as connection:
        rows = connection.execute(
            "SELECT payload FROM account_snapshots ORDER BY name COLLATE NOCASE"
        ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def get_snapshot(database_path: str, account_id: str) -> dict | None:
    with _connect(database_path) as connection:
        row = connection.execute(
            "SELECT payload FROM account_snapshots WHERE account_id = ?",
            (account_id,),
        ).fetchone()
    return json.loads(row["payload"]) if row else None
