"""Điểm vào REST API với facade tương thích cho callers Python cũ.

Đây là composition root: nạp cấu hình, áp dụng migration, rồi khởi động tầng interfaces.
Chỉ file điểm vào được phép nối các tầng với nhau; runtime HTTP dùng interface mới.
"""

from urllib.parse import parse_qs, urlsplit

from backend.config import api_settings, load_dotenv
from backend.domain.query import parse_event_query, parse_utc_timestamp
from backend.infrastructure.migrations import initialize
from backend.interfaces import http_api
from backend.repositories.event_repository import latest_events, query_events


_utc_param = parse_utc_timestamp


class ApiHandler(http_api.ApiHandler):
    """Deprecated handler facade retained for existing importers and tests."""

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        params = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=False)
        try:
            if parsed.path == "/api/events/latest":
                self._send(200, latest_events())
                return
            if parsed.path != "/api/events":
                self._send(404, {"error": "Not found"})
                return
            query = parse_event_query(params)
            rows = query_events(query.start, query.end, query.seat_id, query.limit)
            self._send(200, rows)
        except (ValueError, IndexError):
            self._send(400, {"error": "Invalid query parameters"})
        except Exception as exc:
            print(f"[api] request failed: {type(exc).__name__}")
            self._send(503, {"error": "Service temporarily unavailable"})


def main() -> None:
    load_dotenv()
    settings = api_settings()
    initialize()
    http_api.serve(settings.host, settings.port, settings.db_connect_timeout)


if __name__ == "__main__":
    main()
