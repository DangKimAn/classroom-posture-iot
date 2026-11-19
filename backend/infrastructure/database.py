"""PostgreSQL connection factory."""

import psycopg
from psycopg.rows import dict_row

from backend.config import database_settings

DEFAULT_DB_CONNECT_TIMEOUT = 5
MAX_DB_CONNECT_TIMEOUT = 30


def connect(
    db_url: str | None = None,
    *,
    connect_timeout: int = DEFAULT_DB_CONNECT_TIMEOUT,
) -> psycopg.Connection:
    """Open a PostgreSQL connection from a DSN or separate environment values."""
    if (
        isinstance(connect_timeout, bool)
        or not isinstance(connect_timeout, int)
        or not 1 <= connect_timeout <= MAX_DB_CONNECT_TIMEOUT
    ):
        raise ValueError(
            f"connect_timeout must be an integer between 1 and {MAX_DB_CONNECT_TIMEOUT} seconds"
        )
    settings = database_settings()
    url = db_url or settings.url
    if url:
        return psycopg.connect(
            url, row_factory=dict_row, connect_timeout=connect_timeout
        )

    components = (
        ("DB_HOST", settings.host), ("DB_PORT", settings.port), ("DB_NAME", settings.name),
        ("DB_USER", settings.user), ("DB_PASSWORD", settings.password),
    )
    missing = [env_name for env_name, value in components if not value]
    if missing:
        raise RuntimeError(
            "Database configuration is incomplete; set DB_URL or " + ", ".join(name for name, _ in components)
            + ". Missing: " + ", ".join(missing)
        )
    try:
        port = int(settings.port)
    except ValueError as exc:
        raise RuntimeError("DB_PORT must be an integer") from exc
    return psycopg.connect(
        host=settings.host,
        port=port,
        dbname=settings.name,
        user=settings.user,
        password=settings.password,
        row_factory=dict_row,
        connect_timeout=connect_timeout,
    )
