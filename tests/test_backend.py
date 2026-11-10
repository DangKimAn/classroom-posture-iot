import json
import os
from uuid import UUID, uuid4
from unittest.mock import Mock

import pytest

pytest.importorskip("psycopg")

from backend import database
from backend.validator import decode_event_message, validate_event_payload


def sample_event(**overrides):
    event = {
        "event_id": str(uuid4()),
        "ts": "2026-11-08T03:12:45Z",
        "seat_id": "S01",
        "label": "leaning",
        "angles": {"trunk": 18.4},
        "confidence": 0.91,
        "model": "mock-generator-v1",
    }
    event.update(overrides)
    return event


@pytest.fixture
def db_url():
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL test database")
    return value


def test_rejects_extra_fields_and_invalid_utc():
    valid, error, _ = validate_event_payload(sample_event(name="student"))
    assert not valid and "Unexpected" in error
    valid, error, _ = validate_event_payload(sample_event(ts="2026-11-08T03:12:45+07:00"))
    assert not valid and "UTC" in error


def test_unknown_event_may_have_null_trunk():
    valid, error, _ = validate_event_payload(sample_event(label="unknown", angles={"trunk": None}))
    assert valid and not error


def test_rejects_oversized_mqtt_payload():
    valid, error, _ = decode_event_message(b" " * 16385)
    assert not valid and "maximum size" in error


def test_large_integer_does_not_crash_mqtt_decoder():
    event = sample_event()
    event["confidence"] = int("1" * 400)
    valid, error, parsed = decode_event_message(json.dumps(event).encode())
    assert not valid and parsed is None
    assert error


def test_deep_json_does_not_crash_mqtt_decoder():
    raw = b"[" * 2000 + b"0" + b"]" * 2000
    valid, _, parsed = decode_event_message(raw)
    assert not valid and parsed is None


def test_database_component_password_passes_unchanged(monkeypatch):
    monkeypatch.setattr(database, "DEFAULT_DB_URL", None)
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "posture_db")
    monkeypatch.setenv("DB_USER", "posture_app")
    monkeypatch.setenv("DB_PASSWORD", "p@ss:w/rd#?%")
    connect = Mock()
    monkeypatch.setattr(database.psycopg, "connect", connect)

    database.connect()

    assert connect.call_args.kwargs["password"] == "p@ss:w/rd#?%"
    assert connect.call_args.kwargs["port"] == 5433


def test_database_url_overrides_component_settings(monkeypatch):
    monkeypatch.setattr(database, "DEFAULT_DB_URL", None)
    monkeypatch.setenv("DB_URL", "postgresql://override/db")
    connect = Mock()
    monkeypatch.setattr(database.psycopg, "connect", connect)

    database.connect()

    assert connect.call_args.args[0] == "postgresql://override/db"
    assert "password" not in connect.call_args.kwargs


def test_event_id_is_normalized_and_trunk_fits_postgres_real():
    event = sample_event(event_id=str(uuid4()).upper())
    valid, _, parsed = decode_event_message(json.dumps(event).encode())
    assert valid and parsed["event_id"] == str(UUID(event["event_id"]))

    event = sample_event(angles={"trunk": 1e300})
    valid, error, _ = decode_event_message(json.dumps(event).encode())
    assert not valid and "database range" in error


def test_api_compares_utc_offsets_as_instants():
    from backend.api import _utc_param

    start = _utc_param("2026-11-08T03:12:45Z", "from")
    end = _utc_param("2026-11-08T03:12:45+00:00", "to")
    assert start == end


def test_api_rejects_duplicate_query_parameters():
    from backend import api
    from http.server import ThreadingHTTPServer
    from threading import Thread
    from urllib.error import HTTPError
    from urllib.request import urlopen

    server = ThreadingHTTPServer(("127.0.0.1", 0), api.ApiHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/events?limit=1&limit=2"
        with pytest.raises(HTTPError) as exc:
            urlopen(url)
        assert exc.value.code == 400
    finally:
        server.shutdown()
        server.server_close()


def test_insert_is_idempotent_and_latest_is_per_seat(db_url):
    database.initialize(db_url)
    seat_one, seat_two = f"S{uuid4().hex[:8]}", f"S{uuid4().hex[:8]}"
    first = sample_event(seat_id=seat_one)
    assert database.insert_event(first, db_url)
    assert not database.insert_event(first, db_url)
    second = sample_event(seat_id=seat_two, label="unknown", angles={"trunk": None})
    assert database.insert_event(second, db_url)
    latest = database.latest_events(db_url)
    assert {row["seat_id"] for row in latest} >= {seat_one, seat_two}
    assert len(database.query_events(seat_id=seat_one, limit=10, db_url=db_url)) == 1


def test_api_rejects_bad_query_parameters(db_url, monkeypatch):
    from backend import api
    from http.server import ThreadingHTTPServer
    from threading import Thread
    from urllib.error import HTTPError
    from urllib.request import urlopen

    database.initialize(db_url)
    monkeypatch.setattr(api, "latest_events", lambda: database.latest_events(db_url))
    monkeypatch.setattr(api, "query_events", lambda *args: database.query_events(*args, db_url=db_url))
    server = ThreadingHTTPServer(("127.0.0.1", 0), api.ApiHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        assert isinstance(json.load(urlopen(base + f"/api/events?seat_id=S{uuid4().hex[:8]}")), list)
        try:
            urlopen(base + "/api/events?limit=99999")
            assert False, "expected invalid limit response"
        except HTTPError as exc:
            assert exc.code == 400
    finally:
        server.shutdown()
        server.server_close()
