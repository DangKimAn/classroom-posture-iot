"""Điểm vào của MQTT subscriber: `python -m backend.mqtt_subscriber`.

Composition root: nạp cấu hình, áp dụng migration, rồi khởi động tầng interfaces.
Không đặt logic ở đây.
"""

from backend.config import load_dotenv, mqtt_settings
from backend.infrastructure.migrations import initialize
from backend.interfaces import mqtt_consumer


def main() -> None:
    load_dotenv()
    settings = mqtt_settings()
    initialize()
    mqtt_consumer.run(settings)


if __name__ == "__main__":
    main()
