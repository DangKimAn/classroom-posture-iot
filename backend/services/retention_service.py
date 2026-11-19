"""Retention operations over the event repository."""

from datetime import datetime, timedelta, timezone
import logging

from backend.repositories import event_repository


LOGGER = logging.getLogger(__name__)
DEFAULT_BATCH_SIZE = 1000


def retention_cutoff(days: int, now: datetime | None = None) -> datetime:
    """Return a UTC cutoff based on the database event's source ``ts`` field."""
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 3650:
        raise ValueError("days must be an integer between 1 and 3650")
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    return current_time.astimezone(timezone.utc) - timedelta(days=days)


def preview_retention(cutoff: datetime) -> int:
    """Return the number of rows eligible for deletion without modifying the database."""
    return event_repository.count_events_before(cutoff)


def apply_retention(cutoff: datetime, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    """Delete rows before ``cutoff`` in bounded batches and log only aggregate counts."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    total_deleted = 0
    while True:
        deleted = event_repository.delete_events_before(cutoff, batch_size)
        if deleted == 0:
            break
        total_deleted += deleted
        LOGGER.info(
            "retention batch deleted_rows=%d total_deleted_rows=%d",
            deleted,
            total_deleted,
        )
    return total_deleted
