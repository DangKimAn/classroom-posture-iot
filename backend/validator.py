"""Validate incoming posture events against the proposed project contract."""

from datetime import datetime
import json
import math
import re
from typing import Any
from uuid import UUID

MAX_PAYLOAD_BYTES = 16_384
MAX_POSTGRES_REAL = 3.4028234663852886e38
LABELS = {"upright", "slouching", "leaning", "unknown"}
REQUIRED_FIELDS = {"event_id", "ts", "seat_id", "label", "confidence", "model", "angles"}


def validate_event_payload(payload: Any) -> tuple[bool, str, dict[str, Any] | None]:
    """Return validity, a safe reason, and the validated mapping."""
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object", None
    missing = sorted(REQUIRED_FIELDS - payload.keys())
    if missing:
        return False, f"Missing required field: {missing[0]}", None
    if payload.keys() - REQUIRED_FIELDS:
        return False, "Unexpected field", None
    try:
        payload["event_id"] = str(UUID(payload["event_id"]))
    except (ValueError, TypeError, AttributeError):
        return False, "event_id must be a UUID", None
    ts = payload["ts"]
    if not isinstance(ts, str):
        return False, "ts must be an ISO-8601 UTC timestamp", None
    try:
        parsed_ts = datetime.fromisoformat(ts[:-1] + "+00:00" if ts.endswith("Z") else ts)
    except ValueError:
        return False, "ts must be an ISO-8601 UTC timestamp", None
    if parsed_ts.tzinfo is None or parsed_ts.utcoffset().total_seconds() != 0:
        return False, "ts must use the UTC timezone", None
    seat_id = payload["seat_id"]
    if not isinstance(seat_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", seat_id):
        return False, "seat_id must be a 1-32 character location code", None
    if payload["label"] not in LABELS:
        return False, "Invalid label", None
    confidence = payload["confidence"]
    try:
        confidence_is_finite = math.isfinite(confidence)
    except (OverflowError, TypeError, ValueError):
        confidence_is_finite = False
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not confidence_is_finite or not 0 <= confidence <= 1:
        return False, "confidence must be a finite number from 0 to 1", None
    if not isinstance(payload["model"], str) or not payload["model"] or len(payload["model"]) > 100:
        return False, "model must be a non-empty string of at most 100 characters", None
    angles = payload["angles"]
    if not isinstance(angles, dict) or angles.keys() - {"trunk"}:
        return False, "angles must contain only the trunk field", None
    trunk = angles.get("trunk")
    try:
        trunk_is_finite = trunk is None or math.isfinite(trunk)
    except (OverflowError, TypeError, ValueError):
        trunk_is_finite = False
    if trunk is not None and (isinstance(trunk, bool) or not isinstance(trunk, (int, float)) or not trunk_is_finite):
        return False, "angles.trunk must be a finite degree value or null", None
    if trunk is not None and abs(trunk) > MAX_POSTGRES_REAL:
        return False, "angles.trunk exceeds the supported database range", None
    if trunk is None and payload["label"] != "unknown":
        return False, "angles.trunk may be null only when label is unknown", None
    return True, "", payload


def decode_event_message(raw: bytes) -> tuple[bool, str, dict[str, Any] | None]:
    """Decode a size-limited MQTT JSON message and validate it."""
    if len(raw) > MAX_PAYLOAD_BYTES:
        return False, "Payload exceeds maximum size", None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return False, "Payload is not valid UTF-8 JSON", None
    try:
        return validate_event_payload(payload)
    except (OverflowError, TypeError, ValueError, RecursionError):
        return False, "Payload has invalid values", None
