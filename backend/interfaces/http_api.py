"""HTTP API (thư viện chuẩn): định tuyến, đọc tham số, trả JSON và mã lỗi.

Thêm endpoint mới: viết một hàm route nhận `params` và trả dữ liệu JSON-able,
rồi đăng ký vào `ROUTES`. Hàm route chỉ gọi domain (kiểm tra tham số) và service.
"""

from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import parse_qs, urlsplit

from backend.config import DEFAULT_API_DB_CONNECT_TIMEOUT
from backend.domain.query import parse_event_query
from backend.services import event_query_service

Params = Mapping[str, Sequence[str]]


def _json_value(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def route_latest_events(
    _params: Params, connect_timeout: int = DEFAULT_API_DB_CONNECT_TIMEOUT
) -> Any:
    return event_query_service.get_latest_events(connect_timeout)


def route_events(
    params: Params, connect_timeout: int = DEFAULT_API_DB_CONNECT_TIMEOUT
) -> Any:
    return event_query_service.search_events(parse_event_query(params), connect_timeout)


ROUTES: dict[str, Callable[[Params, int], Any]] = {
    "/api/events/latest": route_latest_events,
    "/api/events": route_events,
}


class ApiHandler(BaseHTTPRequestHandler):
    def _send(
        self,
        status: int,
        data: object,
        extra_headers: Mapping[str, str] | None = None,
    ) -> None:
        body = json.dumps(data, ensure_ascii=False, default=_json_value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _handle_unsupported_method(self) -> None:
        path = urlsplit(self.path).path
        if path not in ROUTES:
            self._send(404, {"error": "Not found"})
            return
        self._send(
            405,
            {"error": "Method not allowed"},
            {"Allow": "GET"},
        )

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        params = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=False)
        try:
            route = ROUTES.get(parsed.path)
            if route is None:
                self._send(404, {"error": "Not found"})
                return
            connect_timeout = getattr(
                self.server, "db_connect_timeout", DEFAULT_API_DB_CONNECT_TIMEOUT
            )
            self._send(200, route(params, connect_timeout))
        except (ValueError, IndexError):
            self._send(400, {"error": "Invalid query parameters"})
        except Exception as exc:
            print(f"[api] request failed: {type(exc).__name__}")
            self._send(503, {"error": "Service temporarily unavailable"})

    def do_POST(self) -> None:
        self._handle_unsupported_method()

    def do_PUT(self) -> None:
        self._handle_unsupported_method()

    def do_PATCH(self) -> None:
        self._handle_unsupported_method()

    def do_DELETE(self) -> None:
        self._handle_unsupported_method()

    def do_OPTIONS(self) -> None:
        self._handle_unsupported_method()

    def log_message(self, fmt: str, *args: object) -> None:
        # Avoid logging query values that could contain identifying data.
        print(f"[api] {self.address_string()} {self.command} {urlsplit(self.path).path}")


def serve(
    host: str,
    port: int,
    db_connect_timeout: int = DEFAULT_API_DB_CONNECT_TIMEOUT,
) -> None:
    """Serve the API until interrupted."""
    server = ThreadingHTTPServer((host, port), ApiHandler)
    server.db_connect_timeout = db_connect_timeout
    print(f"[api] listening on {host}:{port}; database=PostgreSQL")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
