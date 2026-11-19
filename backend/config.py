"""Tầng cấu hình: đọc `.env` và biến môi trường thành các settings có kiểu rõ ràng.

Chỉ tầng này (và các điểm vào `api.py`, `mqtt_subscriber.py`) được biết tên biến
môi trường. Mọi tầng khác nhận giá trị qua settings hoặc tham số hàm.
Giá trị được đọc tại thời điểm gọi hàm, không chụp lại lúc import.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path

DEFAULT_MQTT_TOPIC = "classroom/posture/events"
DEFAULT_API_DB_CONNECT_TIMEOUT = 2
MAX_API_DB_CONNECT_TIMEOUT = 30
MIN_RETENTION_DAYS = 1
MAX_RETENTION_DAYS = 3650


def load_dotenv() -> None:
    """Load optional project-root .env values without overriding the process environment."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("\"'")
        if key and key.replace("_", "").isalnum():
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class DatabaseSettings:
    """Raw database values; `url` (DB_URL) overrides the component values."""

    url: str | None
    host: str | None
    port: str | None
    name: str | None
    user: str | None
    password: str | None


@dataclass(frozen=True)
class MqttSettings:
    host: str
    port: int
    topic: str
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class ApiSettings:
    host: str
    port: int
    db_connect_timeout: int


def _positive_int_setting(name: str, default: int, maximum: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError:
        raise ValueError(f"{name} must be an integer between 1 and {maximum}") from None
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer between 1 and {maximum}")
    return value


def database_settings() -> DatabaseSettings:
    return DatabaseSettings(
        url=os.getenv("DB_URL"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        name=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def mqtt_settings() -> MqttSettings:
    return MqttSettings(
        host=os.getenv("MQTT_HOST", "localhost"),
        port=int(os.getenv("MQTT_PORT", "1883")),
        topic=os.getenv("MQTT_TOPIC", DEFAULT_MQTT_TOPIC),
        username=os.getenv("MQTT_USERNAME", ""),
        password=os.getenv("MQTT_PASSWORD", ""),
    )


def api_settings() -> ApiSettings:
    return ApiSettings(
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        db_connect_timeout=_positive_int_setting(
            "API_DB_CONNECT_TIMEOUT",
            DEFAULT_API_DB_CONNECT_TIMEOUT,
            MAX_API_DB_CONNECT_TIMEOUT,
        ),
    )


def retention_days(override: int | None = None) -> int:
    """Resolve an explicit retention period; a CLI value takes precedence over the environment."""
    if override is None:
        raw_value = os.getenv("RETENTION_DAYS")
        if raw_value is None:
            raise ValueError("Set --days or RETENTION_DAYS; retention period has no implicit default")
        try:
            days = int(raw_value)
        except ValueError:
            raise ValueError("RETENTION_DAYS must be an integer between 1 and 3650") from None
    else:
        if isinstance(override, bool) or not isinstance(override, int):
            raise ValueError("--days must be an integer between 1 and 3650")
        days = override
    if not MIN_RETENTION_DAYS <= days <= MAX_RETENTION_DAYS:
        source = "--days" if override is not None else "RETENTION_DAYS"
        raise ValueError(f"{source} must be an integer between 1 and 3650")
    return days
