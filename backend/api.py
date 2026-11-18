"""Điểm vào của REST API: `python -m backend.api`.

Đây là composition root: nạp cấu hình, áp dụng migration, rồi khởi động tầng interfaces.
Chỉ file điểm vào được phép nối các tầng với nhau; không đặt logic ở đây.
"""

from backend.config import api_settings, load_dotenv
from backend.infrastructure.migrations import initialize
from backend.interfaces import http_api


def main() -> None:
    load_dotenv()
    settings = api_settings()
    initialize()
    http_api.serve(settings.host, settings.port, settings.db_connect_timeout)


if __name__ == "__main__":
    main()
