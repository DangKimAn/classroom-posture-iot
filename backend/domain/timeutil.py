"""Phân tích timestamp ISO-8601 UTC dùng chung cho payload MQTT và tham số API."""

from datetime import datetime


def parse_iso8601(value: str) -> datetime:
    """Parse ISO-8601, accepting a trailing ``Z``. Raises ValueError when malformed."""
    return datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)


def is_utc(moment: datetime) -> bool:
    """True when ``moment`` is timezone-aware with a zero UTC offset."""
    return moment.tzinfo is not None and moment.utcoffset().total_seconds() == 0
