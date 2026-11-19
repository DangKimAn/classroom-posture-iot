"""Backward-compatible database facade for existing Python callers.

New application code should import migrations from ``infrastructure`` and SQL
operations from ``repositories``.
"""

import os

import psycopg

from backend.infrastructure import database as _database
from backend.infrastructure.migrations import initialize
from backend.repositories.event_repository import (
    insert_event,
    latest_events,
    query_events,
)

DEFAULT_DB_URL = os.getenv("DB_URL")


def connect(db_url: str | None = None) -> psycopg.Connection:
    """Open a connection using the legacy facade's optional DSN override."""
    url = db_url or os.getenv("DB_URL") or DEFAULT_DB_URL
    return _database.connect(url)


__all__ = [
    "DEFAULT_DB_URL",
    "connect",
    "initialize",
    "insert_event",
    "latest_events",
    "query_events",
]
