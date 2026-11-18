"""MQTT event creation and resilient publication for the vision module."""

from __future__ import annotations

import json
import logging
import math
import os
import uuid
from datetime import datetime, timezone
from typing import Any

LOGGER = logging.getLogger(__name__)
DEFAULT_TOPIC = "classroom/posture/events"


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def utc_timestamp() -> str:
    """Return the current UTC timestamp in the contract's ISO-8601 form."""
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_event(seat_id: str, label: str, trunk_angle: float | None, confidence: float, model: str) -> dict[str, Any]:
    """Create one contract-compliant posture event without sensitive image data."""
    if label not in {"upright", "slouching", "leaning", "unknown"}:
        raise ValueError("Unsupported posture label")
    if trunk_angle is not None and not _is_finite_number(trunk_angle):
        raise ValueError(f"angles.trunk must be a finite number or None; received {trunk_angle!r}")
    if trunk_angle is None and label != "unknown":
        raise ValueError("angles.trunk=None requires label=unknown")
    if not _is_finite_number(confidence):
        raise ValueError(f"confidence must be a finite number; received {confidence!r}")
    if not 0 <= confidence <= 1:
        raise ValueError(f"confidence must be between 0 and 1; received {confidence!r}")
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
        self._loop_started = False

    def connect(self) -> None:
        """Create one Paho client and let its network loop handle reconnects."""
        username = os.getenv("MQTT_USERNAME", "").strip()
        password = os.getenv("MQTT_PASSWORD", "")
        if not username or not password:
            raise RuntimeError(
                "MQTT credentials are required; set MQTT_USERNAME and MQTT_PASSWORD "
                "in the process environment or repository .env"
            )
        if self._client is not None:
            # loop_start() enables Paho's built-in reconnect loop; do not create
            # another client or network thread after a broker disconnect.
            return
        try:
            import paho.mqtt.client as mqtt
        except ImportError as error:
            raise RuntimeError("paho-mqtt is required to publish events") from error
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"vision_{uuid.uuid4().hex[:8]}")
        client.username_pw_set(username, password)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.connect(self.host, self.port, keepalive=60)
        client.loop_start()
        self._client = client
        self._loop_started = True

    def _on_connect(self, _client: Any, _userdata: Any, _flags: Any, reason_code: Any, _properties: Any) -> None:
        self._connected = not reason_code.is_failure

    def _on_disconnect(self, _client: Any, _userdata: Any, _disconnect_flags: Any, reason_code: Any, _properties: Any) -> None:
        self._connected = False
        LOGGER.warning("MQTT disconnected (reason=%s); publication will retry", reason_code)

    def publish(self, event: dict[str, Any]) -> bool:
        """Publish an event; return False on a recoverable broker failure."""
        try:
            if not self._connected or self._client is None:
                import time
                if time.monotonic() < self._next_retry_at:
                    return False
                if self._client is None:
                    self.connect()
                else:
                    # Paho's active network loop owns reconnect attempts.
                    return False
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
            self._client.disconnect()
            if self._loop_started:
                self._client.loop_stop()
            self._client = None
            self._loop_started = False
        self._connected = False

