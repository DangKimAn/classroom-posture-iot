"""Small standard-library HTTP API for the posture dashboard."""

from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from urllib.parse import parse_qs, urlsplit

try:
    from .config import load_dotenv
except ImportError:  # Direct execution from the backend directory.
    from config import load_dotenv

load_dotenv()

try:
    from .database import initialize, latest_events, query_events
except ImportError:  # Direct execution from the backend directory.
    from database import initialize, latest_events, query_events

MAX_LIMIT = 500


def _utc_param(value: str, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name} must use the UTC timezone")
    return parsed


def _json_value(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


class ApiHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, data: object) -> None:
        body = json.dumps(data, ensure_ascii=False, default=_json_value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

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
            allowed = {"from", "to", "seat_id", "limit"}
            if params.keys() - allowed or any(len(values) != 1 for values in params.values()):
                raise ValueError("Unsupported query parameter")
            start = _utc_param(params["from"][0], "from") if "from" in params else None
            end = _utc_param(params["to"][0], "to") if "to" in params else None
            if start and end and start > end:
                raise ValueError("from must not be later than to")
            seat = params.get("seat_id", [None])[0]
            if seat is not None and (not seat or len(seat) > 32):
                raise ValueError("seat_id must be 1-32 characters")
            limit = int(params.get("limit", ["100"])[0])
            if not 1 <= limit <= MAX_LIMIT:
                raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
            self._send(200, query_events(start, end, seat, limit))
        except (ValueError, IndexError):
            self._send(400, {"error": "Invalid query parameters"})
        except Exception as exc:
            print(f"[api] request failed: {type(exc).__name__}")
            self._send(503, {"error": "Service temporarily unavailable"})

    def log_message(self, fmt: str, *args: object) -> None:
        # Avoid logging query values that could contain identifying data.
        print(f"[api] {self.address_string()} {self.command} {urlsplit(self.path).path}")


def main() -> None:
    initialize()
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"[api] listening on {host}:{port}; database=PostgreSQL")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
