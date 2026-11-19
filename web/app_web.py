"""Serve the static dashboard and proxy its same-origin API requests."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen


WEB_ROOT = Path(__file__).resolve().parent
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class DashboardHandler(BaseHTTPRequestHandler):
    """Handle static GETs locally and forward `/api/` GETs to the backend."""

    server_version = "ClassroomDashboard/1.0"
    sys_version = ""

    def do_GET(self) -> None:
        request_path = urlsplit(self.path)
        if request_path.path == "/api" or request_path.path.startswith("/api/"):
            self._proxy_api(request_path.path, request_path.query)
            return
        self._serve_static(request_path.path)

    def do_HEAD(self) -> None:
        request_path = urlsplit(self.path)
        if request_path.path == "/api" or request_path.path.startswith("/api/"):
            self._proxy_api(request_path.path, request_path.query, send_body=False)
            return
        self._serve_static(request_path.path, send_body=False)

    def _serve_static(self, request_path: str, *, send_body: bool = True) -> None:
        """Serve a file only when its resolved path stays inside WEB_ROOT."""
        decoded_path = unquote(request_path)
        if "\\" in decoded_path or "\x00" in decoded_path:
            self.send_error(400, "Invalid file path")
            return

        relative_path = decoded_path.lstrip("/") or "index.html"
        if relative_path.endswith("/"):
            relative_path += "index.html"
        try:
            file_path = (WEB_ROOT / relative_path).resolve(strict=True)
            file_path.relative_to(WEB_ROOT)
        except (OSError, RuntimeError, ValueError):
            self.send_error(404, "File not found")
            return

        if (
            not file_path.is_file()
            or file_path.name in {"app_web.py", "Dockerfile", "nginx.conf"}
            or any(part.startswith(".") for part in file_path.relative_to(WEB_ROOT).parts)
        ):
            self.send_error(404, "File not found")
            return

        try:
            body = file_path.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return

        content_type, _ = mimetypes.guess_type(file_path.name)
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def _proxy_api(
        self,
        request_path: str,
        query: str,
        *,
        send_body: bool = True,
    ) -> None:
        """Forward a GET/HEAD request and preserve the backend response."""
        backend_url = os.environ.get("BACKEND_URL", "http://api:8000").rstrip("/")
        parsed_backend = urlsplit(backend_url)
        if parsed_backend.scheme not in {"http", "https"} or not parsed_backend.netloc:
            self.send_error(502, "Invalid backend URL configuration")
            return

        target = f"{backend_url}{request_path}"
        if query:
            target = f"{target}?{query}"
        request = Request(target, method=self.command)
        try:
            upstream = urlopen(request, timeout=10)
        except HTTPError as error:
            upstream = error
        except (URLError, TimeoutError, OSError, ValueError):
            self.send_error(502, "Backend is unavailable")
            return

        with upstream:
            body = upstream.read()
            self.send_response(upstream.status)
            for name, value in upstream.headers.items():
                if name.lower() not in HOP_BY_HOP_HEADERS | {"content-length"}:
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if send_body:
                self.wfile.write(body)

    def log_message(self, format_string: str, *args: object) -> None:
        """Omit query values from access logs."""
        request_path = urlsplit(self.path).path
        status = args[1] if len(args) > 1 else "-"
        print(
            f"{self.log_date_time_string()} {self.client_address[0]} "
            f"{self.command} {request_path} {status}"
        )


def main() -> None:
    """Start the dashboard HTTP server."""
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("WEB_PORT", os.environ.get("PORT", "8080")))
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Dashboard server listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
