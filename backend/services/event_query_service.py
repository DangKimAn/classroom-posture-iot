"""Truy vấn event cho dashboard.

Hiện mỏng. Đây là chỗ đặt logic thống kê sau này (timeline, latency, trạng thái ghế),
để tầng HTTP chỉ lo nhận/trả dữ liệu.
"""

from typing import Any

from backend.domain.query import EventQuery
from backend.repositories import event_repository


def get_latest_events(connect_timeout: int) -> list[dict[str, Any]]:
    """Latest stored event for each seat."""
    return event_repository.latest_events(connect_timeout=connect_timeout)


def search_events(query: EventQuery, connect_timeout: int) -> list[dict[str, Any]]:
    """Filtered event history for a validated query."""
    return event_repository.query_events(
        query.start,
        query.end,
        query.seat_id,
        query.limit,
        connect_timeout=connect_timeout,
    )
