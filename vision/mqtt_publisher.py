"""MQTT event creation and resilient publication for the vision module."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

LOGGER = logging.getLogger(__name__)
DEFAULT_TOPIC = "classroom/posture/events"


def utc_timestamp() -> str:
    """Return the current UTC timestamp in the contract's ISO-8601 form."""
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_event(seat_id: str, label: str, trunk_angle: float | None, confidence: float, model: str) -> dict[str, Any]:
    """Create one contract-compliant posture event without sensitive image data."""
    if label not in {"upright", "slouching", "leaning", "unknown"}:
        raise ValueError("Unsupported posture label")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    return {
        "event_id": str(uuid.uuid4()),
        "ts": utc_timestamp(),
        "seat_id": seat_id,
        "label": label,
        "angles": {"trunk": trunk_angle},
        "confidence": confidence,
        "model": model,
    }


class MqttPublisher:
    """Publish contract events with QoS 1 and no retained messages."""

    def __init__(self, host: str | None = None, port: int | None = None, topic: str | None = None, retry_delay_seconds: float = 1.0) -> None:
        self.host = host or os.getenv("MQTT_HOST", "localhost")
        self.port = port or int(os.getenv("MQTT_PORT", "1883"))
        self.topic = topic or os.getenv("MQTT_TOPIC", DEFAULT_TOPIC)
        self._client: Any | None = None
        self._connected = False
        self._retry_delay_seconds = retry_delay_seconds
        self._next_retry_at = 0.0

    def connect(self) -> None:
        """Connect lazily so unit tests do not need paho-mqtt installed."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError as error:
            raise RuntimeError("paho-mqtt is required to publish events") from error
        client = mqtt.Client(client_id=f"vision_{uuid.uuid4().hex[:8]}")
        username = os.getenv("MQTT_USERNAME")
        if username:
            client.username_pw_set(username, os.getenv("MQTT_PASSWORD"))
        client.on_disconnect = self._on_disconnect
        client.connect(self.host, self.port, keepalive=60)
        client.loop_start()
        self._client, self._connected = client, True

    def _on_disconnect(self, _client: Any, _userdata: Any, _flags: Any, reason_code: Any, *_: Any) -> None:
        self._connected = False
        LOGGER.warning("MQTT disconnected (reason=%s); publication will retry", reason_code)

    def publish(self, event: dict[str, Any]) -> bool:
        """Publish an event; return False on a recoverable broker failure."""
        try:
            if not self._connected or self._client is None:
                import time
                if time.monotonic() < self._next_retry_at:
                    return False
                self.connect()
            result = self._client.publish(self.topic, json.dumps(event), qos=1, retain=False)
            if getattr(result, "rc", 0) != 0:
                LOGGER.warning("MQTT publish failed with rc=%s", result.rc)
                return False
            return True
        except (OSError, RuntimeError) as error:
            import time
            self._connected = False
            self._next_retry_at = time.monotonic() + self._retry_delay_seconds
            LOGGER.warning("MQTT publish unavailable: %s", error)
            return False

    def close(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
        self._connected = False

