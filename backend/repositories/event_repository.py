"""SQL access for the ``posture_events`` table."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import psycopg

from backend.domain.errors import StorageRejectedError, StorageUnavailableError
from backend.infrastructure import database

_COLUMNS = "event_id, ts, seat_id, label, trunk_angle, confidence, model_version"


@contextmanager
def _connection(
    db_url: str | None,
    connect_timeout: int = database.DEFAULT_DB_CONNECT_TIMEOUT,
) -> Iterator[psycopg.Connection]:
    """Open a repository connection and translate database failures to domain errors."""
    try:
        with database.connect(db_url, connect_timeout=connect_timeout) as conn:
            yield conn
    except (psycopg.DataError, psycopg.IntegrityError) as exc:
        raise StorageRejectedError(type(exc).__name__) from exc
    except (psycopg.Error, OSError) as exc:
        raise StorageUnavailableError(type(exc).__name__) from exc


def insert_event(event: dict[str, Any], db_url: str | None = None) -> bool:
    """Insert one event; return False when event_id was already stored.

    Raises StorageRejectedError for data the database will never accept and
    StorageUnavailableError for failures that may succeed on retry.
    """
    with _connection(db_url) as conn:
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


def latest_events(
    db_url: str | None = None,
    *,
    connect_timeout: int = database.DEFAULT_DB_CONNECT_TIMEOUT,
) -> list[dict[str, Any]]:
    """Latest stored event of each seat (at most 500 seats).

    Cách làm: nhảy qua từng seat_id khác nhau bằng index (recursive CTE), rồi với mỗi
    seat lấy dòng mới nhất bằng LATERAL ... LIMIT 1. Chi phí tỉ lệ với số seat, không
    còn quét và sort toàn bảng. Cần index idx_posture_events_seat_ts_id (migration 002).
    Kết quả giữ nguyên: cùng cột, sắp theo seat_id, tie-break ts DESC, id DESC.
    """
    with _connection(db_url, connect_timeout) as conn:
        rows = conn.execute(
            f"""WITH RECURSIVE seats(sid) AS (
                    (SELECT seat_id FROM posture_events ORDER BY seat_id LIMIT 1)
                    UNION ALL
                    SELECT (SELECT pe.seat_id FROM posture_events AS pe
                            WHERE pe.seat_id > seats.sid
                            ORDER BY pe.seat_id LIMIT 1)
                    FROM seats
                    WHERE seats.sid IS NOT NULL
                )
                SELECT latest.*
                FROM (SELECT sid FROM seats WHERE sid IS NOT NULL LIMIT 500) AS s
                CROSS JOIN LATERAL (
                    SELECT {_COLUMNS}
                    FROM posture_events AS pe
                    WHERE pe.seat_id = s.sid
                    ORDER BY pe.ts DESC, pe.id DESC
                    LIMIT 1
                ) AS latest
                ORDER BY latest.seat_id"""
        ).fetchall()
    return rows


def query_events(start=None, end=None, seat_id: str | None = None, limit: int = 100,
                 db_url: str | None = None,
                 *, connect_timeout: int = database.DEFAULT_DB_CONNECT_TIMEOUT) -> list[dict[str, Any]]:
    """History filtered by optional time range and seat, newest first."""
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
    with _connection(db_url, connect_timeout) as conn:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM posture_events" + where + " ORDER BY ts DESC LIMIT %s",
            (*values, limit),
        ).fetchall()
    return rows


def count_events_before(cutoff: datetime, db_url: str | None = None) -> int:
    """Count rows whose source event timestamp is older than ``cutoff``."""
    with _connection(db_url) as conn:
        row = conn.execute(
            "SELECT count(*) AS row_count FROM posture_events WHERE ts < %s",
            (cutoff,),
        ).fetchone()
    return int(row["row_count"])


def delete_events_before(
    cutoff: datetime,
    limit: int,
    db_url: str | None = None,
) -> int:
    """Delete at most ``limit`` old rows in one transaction without returning payloads."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    with _connection(db_url) as conn:
        cursor = conn.execute(
            """WITH batch AS (
                   SELECT id FROM posture_events
                   WHERE ts < %s
                   ORDER BY ts, id
                   LIMIT %s
                   FOR UPDATE
               )
               DELETE FROM posture_events AS event
               USING batch
               WHERE event.id = batch.id""",
            (cutoff, limit),
        )
        return cursor.rowcount