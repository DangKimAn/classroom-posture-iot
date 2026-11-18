"""Command-line interface for dry-run-first event retention."""

import argparse
import logging
from typing import Sequence
from urllib.parse import parse_qs, unquote, urlsplit

from backend.config import database_settings, retention_days
from backend.services.retention_service import (
    apply_retention,
    preview_retention,
    retention_cutoff,
)


LOGGER = logging.getLogger("backend.retention")


def configured_database_name() -> str:
    """Return only the configured database name, never the DSN or its credentials."""
    settings = database_settings()
    if settings.url:
        try:
            parsed = urlsplit(settings.url)
            if parsed.scheme not in {"postgres", "postgresql"}:
                raise ValueError
            database_name = unquote(parsed.path.lstrip("/"))
            if not database_name:
                database_name = parse_qs(parsed.query).get("dbname", [None])[0]
        except (ValueError, UnicodeError):
            raise ValueError("Unable to determine database name from DB_URL") from None
    else:
        database_name = settings.name
    if not database_name:
        raise ValueError("Database name is not configured")
    return str(database_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or apply event retention using source event timestamps."
    )
    parser.add_argument("--days", type=int, help="Retention period (1-3650); overrides RETENTION_DAYS")
    parser.add_argument("--apply", action="store_true", help="Delete eligible rows in bounded batches")
    parser.add_argument(
        "--confirm-db",
        metavar="NAME",
        help="Required with --apply; must exactly match the configured database name",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        days = retention_days(args.days)
    except ValueError as error:
        parser.error(str(error))

    if args.apply:
        if not args.confirm_db:
            parser.error("--apply requires --confirm-db with the configured database name")
        try:
            actual_database_name = configured_database_name()
        except ValueError as error:
            parser.error(str(error))
        if args.confirm_db != actual_database_name:
            parser.error("--confirm-db does not match the configured database name")
    elif args.confirm_db:
        parser.error("--confirm-db is only valid with --apply")

    cutoff = retention_cutoff(days)
    if not args.apply:
        row_count = preview_retention(cutoff)
        print(
            f"DRY RUN: rows_to_delete={row_count}; source_field=ts; "
            f"cutoff_utc={cutoff.isoformat()}"
        )
        return 0

    deleted = apply_retention(cutoff)
    LOGGER.info(
        "retention applied deleted_rows=%d source_field=ts cutoff_utc=%s",
        deleted,
        cutoff.isoformat(),
    )
    print(f"APPLIED: deleted_rows={deleted}; source_field=ts cutoff_utc={cutoff.isoformat()}")
    return 0
