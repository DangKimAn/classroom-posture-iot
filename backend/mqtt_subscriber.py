"""MQTT subscriber with manual acknowledgements and bounded retry."""

from dataclasses import dataclass
from enum import Enum, auto
import os
import time
from typing import Callable

import psycopg

try:
    from .config import load_dotenv
except ImportError:  # Direct execution from the backend directory.
    from config import load_dotenv

load_dotenv()

try:
    from .database import initialize, insert_event
    from .validator import decode_event_message
except ImportError:  # Direct execution from the backend directory.
    from database import initialize, insert_event
    from validator import decode_event_message


class Outcome(Enum):
    STORED = auto()
    DUPLICATE = auto()
    INVALID = auto()
    TEMPORARY = auto()
    PERMANENT = auto()


@dataclass(frozen=True)
class ProcessResult:
    outcome: Outcome
    reason: str | None = None
    error_type: str | None = None


RETRY_DELAYS = (0.5, 1.0)
RECONNECT_DELAY = 3.0
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1


def handle_payload(
    raw: bytes,
    insert: Callable[[dict], bool] = insert_event,
) -> ProcessResult:
    """Validate and store one MQTT payload, classifying retryable errors."""
    valid, reason, event = decode_event_message(raw)
    if not valid:
        return ProcessResult(Outcome.INVALID, reason=reason)
    try:
        if insert(event):
            return ProcessResult(Outcome.STORED)
        return ProcessResult(Outcome.DUPLICATE)
    except (
        psycopg.OperationalError,
        psycopg.InterfaceError,
        OSError,
        TimeoutError,
        ConnectionError,
    ) as exc:
        return ProcessResult(Outcome.TEMPORARY, error_type=type(exc).__name__)
    except (psycopg.DataError, psycopg.IntegrityError) as exc:
        return ProcessResult(Outcome.PERMANENT, error_type=type(exc).__name__)
    except psycopg.Error as exc:
        # Unknown database errors are retried to avoid losing a valid event.
        return ProcessResult(Outcome.TEMPORARY, error_type=type(exc).__name__)
    except Exception as exc:
        # Unexpected storage errors fail closed and use the same bounded retry.
        return ProcessResult(Outcome.TEMPORARY, error_type=type(exc).__name__)


def process_message(
    client,
    message,
    insert: Callable[[dict], bool] = insert_event,
    sleep: Callable[[float], None] = time.sleep,
) -> ProcessResult:
    """Process serially, ACK completed messages, and reconnect on DB outages."""
    result = ProcessResult(Outcome.TEMPORARY, error_type="UnknownError")
    for attempt in range(MAX_ATTEMPTS):
        result = handle_payload(message.payload, insert)
        if result.outcome is not Outcome.TEMPORARY:
            break
        if attempt < len(RETRY_DELAYS):
            sleep(RETRY_DELAYS[attempt])

    if result.outcome is Outcome.TEMPORARY:
        print(f"[mqtt] storage unavailable after retries: {result.error_type}")
        client.disconnect()
        return result

    if result.outcome is Outcome.INVALID:
        print(f"[mqtt] rejected message: {result.reason}")
    elif result.outcome is Outcome.PERMANENT:
        print(f"[mqtt] permanently rejected message: {result.error_type}")
    elif result.outcome is Outcome.STORED:
        print("[mqtt] event stored")
    else:
        print("[mqtt] duplicate event ignored")

    ack_result = client.ack(message.mid, message.qos)
    if ack_result != 0:
        print(f"[mqtt] ACK failed: {ack_result}")
        client.disconnect()
    return result


def main() -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit("Install backend requirements before starting the MQTT subscriber") from exc

    host = os.getenv("MQTT_HOST", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    topic = os.getenv("MQTT_TOPIC", "classroom/posture/events")
    username, password = os.getenv("MQTT_USERNAME", ""), os.getenv("MQTT_PASSWORD", "")
    initialize()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="posture-backend",
        clean_session=False,
        manual_ack=True,
    )
    if username:
        client.username_pw_set(username, password)

    def on_connect(client, _userdata, _flags, reason_code, _properties=None):
        if reason_code == 0:
            client.subscribe(topic, qos=1)
            print(f"[mqtt] connected; subscribed topic={topic}")
        else:
            print(f"[mqtt] connect failed: reason={reason_code}")

    def on_disconnect(_client, _userdata, _flags, reason_code, _properties=None):
        print(f"[mqtt] disconnected: reason={reason_code}; reconnect will be attempted")

    def on_message(client, _userdata, message):
        process_message(client, message)

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    while True:
        try:
            client.connect(host, port, keepalive=60)
            client.loop_forever(retry_first_connection=True)
        except OSError as exc:
            print(f"[mqtt] broker unavailable: {type(exc).__name__}")
        print(f"[mqtt] reconnecting in {RECONNECT_DELAY:g}s")
        time.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    main()
