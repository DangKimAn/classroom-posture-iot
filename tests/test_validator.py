#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from validator import validate_event_payload

def test_valid_payload():
    payload = {
        "event_id": "9bbddfe2-0bf1-42a9-9ee2-419e104ad023",
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
        "angles": {"trunk": 12.5},
        "confidence": 0.95,
        "model": "yolov8n-pose"
    }
    is_valid, err, _ = validate_event_payload(payload)
    assert is_valid is False
    assert "event_id" in err

def test_invalid_label():
    payload = {
        "event_id": "57bd66f4-331e-4e0e-b842-07c8117d59a0",
        "ts": "2026-11-08T03:12:45Z",
        "seat_id": "S01",
        "label": "sleeping", # Nhan khong nam trong DATA_CONTRACT
        "angles": {"trunk": 12.5},
        "confidence": 0.95,
        "model": "yolov8n-pose"
    }
    is_valid, err, _ = validate_event_payload(payload)
    assert is_valid is False
    assert "Invalid label" in err
