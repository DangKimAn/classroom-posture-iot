"""PostgreSQL persistence for posture events."""

import os
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

DEFAULT_DB_URL = os.getenv("DB_URL")


def connect(db_url: str | None = None) -> psycopg.Connection:
    """Open a PostgreSQL connection from a DSN or separate environment values."""
    url = db_url or os.getenv("DB_URL") or DEFAULT_DB_URL
    if url:
        return psycopg.connect(url, row_factory=dict_row, connect_timeout=5)

    names = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Database configuration is incomplete; set DB_URL or " + ", ".join(names)
            + ". Missing: " + ", ".join(missing)
        )
    try:
        port = int(os.environ["DB_PORT"])
    except ValueError as exc:
        raise RuntimeError("DB_PORT must be an integer") from exc
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=port,
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        row_factory=dict_row,
        connect_timeout=5,
    )


def initialize(db_url: str | None = None) -> None:
    """Apply all idempotent SQL migrations in filename order."""
    migrations = sorted(Path(__file__).with_name("migrations").glob("*.sql"))
    with connect(db_url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(782630194)")
        for migration in migrations:
            for statement in migration.read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    conn.execute(statement)


def insert_event(event: dict[str, Any], db_url: str | None = None) -> bool:
    """Insert one event; return False when event_id was already stored."""
    with connect(db_url) as conn:
        row = conn.execute(
            """INSERT INTO posture_events
               (event_id, ts, seat_id, label, trunk_angle, confidence, model_version)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (event_id) DO NOTHING
               RETURNING event_id""",
            (event["event_id"], event["ts"], event["seat_id"], event["label"],
             event["angles"].get("trunk"), event["confidence"], event["model"]),
        ).fetchone()
        return row is not None


def latest_events(db_url: str | None = None) -> list[dict[str, Any]]:
    with connect(db_url) as conn:
        rows = conn.execute(
            """SELECT DISTINCT ON (seat_id)
                      event_id, ts, seat_id, label, trunk_angle, confidence, model_version
               FROM posture_events
               ORDER BY seat_id, ts DESC, id DESC
               LIMIT 500"""
        ).fetchall()
    return rows


def query_events(start: str | None = None, end: str | None = None,
                 seat_id: str | None = None, limit: int = 100,
                 db_url: str | None = None) -> list[dict[str, Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if start:
        clauses.append("ts >= %s")
        values.append(start)
    if end:
        clauses.append("ts <= %s")
        values.append(end)
    if seat_id:
        clauses.append("seat_id = %s")
        values.append(seat_id)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect(db_url) as conn:
        rows = conn.execute(
            "SELECT event_id, ts, seat_id, label, trunk_angle, confidence, model_version FROM posture_events"
            + where + " ORDER BY ts DESC LIMIT %s", (*values, limit)
        ).fetchall()
    return rows
