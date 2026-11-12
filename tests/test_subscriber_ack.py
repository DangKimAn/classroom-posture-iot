import json
from types import SimpleNamespace
from uuid import uuid4

import psycopg

from backend.mqtt_subscriber import Outcome, process_message


def valid_payload():
    return json.dumps(
        {
            "event_id": str(uuid4()),
            "ts": "2026-11-10T03:12:45Z",
            "seat_id": "S01",
            "label": "upright",
            "angles": {"trunk": 4.2},
            "confidence": 0.95,
            "model": "fake-test-v1",
        }
    ).encode()


class FakeClient:
    def __init__(self):
        self.acks = []
        self.disconnects = 0

    def ack(self, mid, qos):
        self.acks.append((mid, qos))
        return 0

    def disconnect(self):
        self.disconnects += 1


def fake_message(payload=None, qos=1):
    return SimpleNamespace(payload=payload or valid_payload(), mid=7, qos=qos)


def test_stored_event_is_acked_once():
    client = FakeClient()
    result = process_message(client, fake_message(), insert=lambda _event: True, sleep=lambda _: None)
    assert result.outcome is Outcome.STORED
    assert client.acks == [(7, 1)]
    assert client.disconnects == 0


def test_duplicate_event_is_acked_once():
    client = FakeClient()
    result = process_message(client, fake_message(), insert=lambda _event: False, sleep=lambda _: None)
    assert result.outcome is Outcome.DUPLICATE
    assert client.acks == [(7, 1)]


def test_invalid_payload_is_acked_and_discarded():
    client = FakeClient()
    result = process_message(client, fake_message(b"not-json"), insert=lambda _event: True, sleep=lambda _: None)
    assert result.outcome is Outcome.INVALID
    assert client.acks == [(7, 1)]


def test_repeated_operational_error_is_not_acked_and_disconnects():
    client = FakeClient()
    calls = []
    delays = []

    def fail(_event):
        calls.append(1)
        raise psycopg.OperationalError("database unavailable")

    result = process_message(client, fake_message(), insert=fail, sleep=delays.append)
    assert result.outcome is Outcome.TEMPORARY
    assert len(calls) == 3
    assert delays == [0.5, 1.0]
    assert client.acks == []
    assert client.disconnects == 1


def test_data_error_is_acked_and_discarded():
    client = FakeClient()

    def fail(_event):
        raise psycopg.DataError("invalid database value")

    result = process_message(client, fake_message(), insert=fail, sleep=lambda _: None)
    assert result.outcome is Outcome.PERMANENT
    assert client.acks == [(7, 1)]
    assert client.disconnects == 0


def test_temporary_failure_then_success_is_acked_once():
    client = FakeClient()
    calls = []
    delays = []

    def fail_once(_event):
        calls.append(1)
        if len(calls) == 1:
            raise psycopg.OperationalError("temporary connection error")
        return True

    result = process_message(client, fake_message(), insert=fail_once, sleep=delays.append)
    assert result.outcome is Outcome.STORED
    assert len(calls) == 2
    assert delays == [0.5]
    assert client.acks == [(7, 1)]
    assert client.disconnects == 0
