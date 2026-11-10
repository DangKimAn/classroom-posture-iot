#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

# Skip test gracefully if backend module is not yet implemented (TV3 task)
validator_mod = pytest.importorskip("validator", reason="Module backend/validator.py not yet implemented by TV3")
validate_event_payload = validator_mod.validate_event_payload

def test_valid_payload():
    payload = {
        "event_id": "test-uuid-1234",
        "ts": "2026-11-08T03:12:45Z",
        "seat_id": "S01",
        "label": "upright",
        "angles": {"trunk": 12.5},
        "confidence": 0.95,
        "model": "yolov8n-pose"
    }
    is_valid, err, data = validate_event_payload(payload)
    assert is_valid is True
    assert err == ""

def test_missing_required_fields():
    # Thieu truong event_id
    payload = {
        "ts": "2026-11-08T03:12:45Z",
        "seat_id": "S01",
        "label": "upright",
        "confidence": 0.95,
        "model": "yolov8n-pose"
    }
    is_valid, err, _ = validate_event_payload(payload)
    assert is_valid is False
    assert "event_id" in err

def test_invalid_label():
    payload = {
        "event_id": "test-uuid-1234",
        "ts": "2026-11-08T03:12:45Z",
        "seat_id": "S01",
        "label": "sleeping", # Nhan khong nam trong DATA_CONTRACT
        "confidence": 0.95,
        "model": "yolov8n-pose"
    }
    is_valid, err, _ = validate_event_payload(payload)
    assert is_valid is False
    assert "Invalid label" in err
