"""MQTT consumer: nhận bản tin, giao cho ingest_service, rồi ACK thủ công hoặc ngắt kết nối."""

import time
from collections import Counter
from threading import Event, Lock, Thread
from typing import Callable

from backend.config import MqttSettings
from backend.services.ingest_service import Outcome, ProcessResult, ingest

RECONNECT_DELAY = 3.0
SUMMARY_INTERVAL = 60.0


def suback_succeeded(reason_codes) -> bool:
    """Return whether every MQTT v5 SUBACK reason code was accepted."""
    return all(
        not (reason.is_failure if hasattr(reason, "is_failure") else int(reason) >= 128)
        for reason in reason_codes
    )


def process_message(
    client,
    message,
    insert: Callable[[dict], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    counters: Counter | None = None,
    counter_lock=None,
) -> ProcessResult:
    """Process serially, ACK completed messages, and reconnect on DB outages."""
    result = ingest(message.payload, insert, sleep)

    if result.outcome is Outcome.TEMPORARY:
        print(f"[mqtt] storage unavailable after retries: {result.error_type}")
        if counters is not None:
            if counter_lock is None:
                counters["temporary_error"] += 1
            else:
                with counter_lock:
                    counters["temporary_error"] += 1
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

    if counters is not None:
        key = {
            Outcome.STORED: "stored",
            Outcome.DUPLICATE: "duplicate",
            Outcome.INVALID: "invalid",
            Outcome.PERMANENT: "invalid",
        }[result.outcome]
        if counter_lock is None:
            counters[key] += 1
        else:
            with counter_lock:
                counters[key] += 1

    ack_result = client.ack(message.mid, message.qos)
    if ack_result != 0:
        print(f"[mqtt] ACK failed: {ack_result}")
        client.disconnect()
    return result


def run(settings: MqttSettings) -> None:
    """Connect to the broker and consume forever, reconnecting after failures."""
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit("Install backend requirements before starting the MQTT subscriber") from exc

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="posture-backend",
        clean_session=False,
        manual_ack=True,
    )
    if settings.username:
        client.username_pw_set(settings.username, settings.password)

    counters = Counter(stored=0, duplicate=0, invalid=0, temporary_error=0)
    counter_lock = Lock()
    stop_summary = Event()

    def report_summaries():
        while not stop_summary.wait(SUMMARY_INTERVAL):
            with counter_lock:
                totals = dict(counters)
            print(
                "[mqtt] summary "
                f"stored={totals['stored']} duplicate={totals['duplicate']} "
                f"invalid={totals['invalid']} temporary_error={totals['temporary_error']}"
            )

    Thread(target=report_summaries, name="mqtt-summary", daemon=True).start()

    def on_connect(client, _userdata, _flags, reason_code, _properties=None):
        if reason_code == 0:
            result, _mid = client.subscribe(settings.topic, qos=1)
            if result != mqtt.MQTT_ERR_SUCCESS:
                print(f"[mqtt] subscribe request failed: code={result}")
                client.disconnect()
        else:
            print(f"[mqtt] connect failed: reason={reason_code}")

    def on_subscribe(client, _userdata, mid, reason_code_list, _properties=None):
        reasons = list(reason_code_list)
        if not suback_succeeded(reasons):
            print(f"[mqtt] subscription rejected: mid={mid}; reason_codes={reasons}")
            client.disconnect()
        else:
            print(f"[mqtt] ready; subscribed topic={settings.topic}; mid={mid}")

    def on_disconnect(_client, _userdata, _flags, reason_code, _properties=None):
        print(f"[mqtt] disconnected: reason={reason_code}; reconnect will be attempted")

    def on_message(client, _userdata, message):
        process_message(client, message, counters=counters, counter_lock=counter_lock)

    client.on_connect, client.on_disconnect = on_connect, on_disconnect
    client.on_subscribe, client.on_message = on_subscribe, on_message
    while True:
        try:
            client.connect(settings.host, settings.port, keepalive=60)
            client.loop_forever(retry_first_connection=True)
        except OSError as exc:
            print(f"[mqtt] broker unavailable: {type(exc).__name__}")
        print(f"[mqtt] reconnecting in {RECONNECT_DELAY:g}s")
        time.sleep(RECONNECT_DELAY)
