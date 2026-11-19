"""Điểm vào của MQTT subscriber: `python -m backend.mqtt_subscriber`.

Composition root: nạp cấu hình, áp dụng migration, rồi khởi động tầng interfaces.
Không đặt logic ở đây.
"""

from collections import Counter
from typing import Callable

import psycopg

from backend.config import load_dotenv, mqtt_settings
from backend.domain.errors import StorageRejectedError, StorageUnavailableError
from backend.infrastructure.migrations import initialize
from backend.interfaces import mqtt_consumer
from backend.interfaces.mqtt_consumer import process_message as _process_message
from backend.services.ingest_service import Outcome, ProcessResult

# Compatibility exports for callers migrating from the former single-file
# subscriber implementation. Runtime startup still delegates to the interface.
__all__ = ["Outcome", "ProcessResult", "process_message", "main"]


def process_message(
    client,
    message,
    insert: Callable[[dict], bool] | None = None,
    sleep: Callable[[float], None] | None = None,
    counters: Counter | None = None,
    counter_lock=None,
) -> ProcessResult:
    """Keep the legacy injectable callback compatible with psycopg exceptions.

    Runtime ingestion translates these errors in the repository layer. Older
    callers may inject an insert callback directly, so translate its database
    exceptions here before delegating to the interface implementation.
    """
    if insert is not None:
        legacy_insert = insert

        def insert(event):
            try:
                return legacy_insert(event)
            except (psycopg.DataError, psycopg.IntegrityError) as exc:
                raise StorageRejectedError(type(exc).__name__) from exc
            except psycopg.Error as exc:
                raise StorageUnavailableError(type(exc).__name__) from exc

    kwargs = {"insert": insert, "counters": counters, "counter_lock": counter_lock}
    if sleep is not None:
        kwargs["sleep"] = sleep
    return _process_message(client, message, **kwargs)


def main() -> None:
    load_dotenv()
    settings = mqtt_settings()
    initialize()
    mqtt_consumer.run(settings)


if __name__ == "__main__":
    main()
