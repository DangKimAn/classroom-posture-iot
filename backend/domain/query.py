"""Kiểm tra tham số truy vấn của `GET /api/events` thành một đối tượng `EventQuery` đã hợp lệ."""

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from backend.domain.contract import DEFAULT_LIMIT, MAX_LIMIT, MAX_SEAT_ID_LENGTH
from backend.domain.timeutil import is_utc, parse_iso8601

ALLOWED_PARAMS = frozenset({"from", "to", "seat_id", "limit"})


@dataclass(frozen=True)
class EventQuery:
    start: datetime | None
    end: datetime | None
    seat_id: str | None
    limit: int


def parse_utc_timestamp(value: str, name: str) -> datetime:
    """Parse a UTC query-string timestamp; raises ValueError with a safe message."""
    try:
        parsed = parse_iso8601(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid ISO-8601 timestamp") from exc
    if not is_utc(parsed):
        raise ValueError(f"{name} must use the UTC timezone")
    return parsed


def parse_event_query(params: Mapping[str, Sequence[str]]) -> EventQuery:
    """Validate raw query parameters (name -> list of values). Raises ValueError when invalid."""
    if params.keys() - ALLOWED_PARAMS or any(len(values) != 1 for values in params.values()):
        raise ValueError("Unsupported query parameter")
    start = parse_utc_timestamp(params["from"][0], "from") if "from" in params else None
    end = parse_utc_timestamp(params["to"][0], "to") if "to" in params else None
    if start and end and start > end:
        raise ValueError("from must not be later than to")
    seat = params.get("seat_id", [None])[0]
    if seat is not None and (not seat or len(seat) > MAX_SEAT_ID_LENGTH):
        raise ValueError(f"seat_id must be 1-{MAX_SEAT_ID_LENGTH} characters")
    limit = int(params.get("limit", [str(DEFAULT_LIMIT)])[0])
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    return EventQuery(start=start, end=end, seat_id=seat, limit=limit)
