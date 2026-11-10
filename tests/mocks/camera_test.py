#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Test for Mock Camera Server
Role: TV1 (Mocking & Proof of Work)
Verifies that the mock camera server functions properly as a drop-in replacement for ESP32-CAM.
"""

import sys
import os
import time
import json
import urllib.request
import threading

# Import mock server components from the same directory
sys.path.insert(0, os.path.dirname(__file__))
from camera_mock import ThreadedHTTPServer, MockCameraHTTPHandler, MockCameraFrameGenerator


def test_mock_camera_server():
    """Start mock server in thread, test /status, /snapshot, and /stream endpoints."""
    test_port = 18088
    server_address = ("127.0.0.1", test_port)
    httpd = ThreadedHTTPServer(server_address, MockCameraHTTPHandler)
    httpd.target_fps = 30
    httpd.generator = MockCameraFrameGenerator(width=640, height=480)

    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{test_port}"

    try:
        # 1. Test /status endpoint
        print(f"[TEST] Testing {base_url}/status ...")
        with urllib.request.urlopen(f"{base_url}/status", timeout=5) as resp:
            assert resp.status == 200, f"Expected 200, got {resp.status}"
            content_type = resp.headers.get("Content-Type", "")
            assert "application/json" in content_type
            data = json.loads(resp.read().decode("utf-8"))
            assert data["device"] == "ESP32-CAM (Mock)"
            assert data["status"] == "ONLINE"
            assert data["stream_endpoint"] == "/stream"
            assert data["simulated_seat"] == "S01"
            print("  -> /status PASSED: Valid JSON & Telemetry received.")

        # 2. Test /snapshot endpoint
        print(f"[TEST] Testing {base_url}/snapshot ...")
        with urllib.request.urlopen(f"{base_url}/snapshot", timeout=5) as resp:
            assert resp.status == 200
            assert resp.headers.get("Content-Type") == "image/jpeg"
            jpeg_data = resp.read()
            # Verify JPEG SOI marker (0xFF, 0xD8) and EOI marker (0xFF, 0xD9)
            assert jpeg_data[:2] == b"\xff\xd8", "Invalid JPEG Start of Image marker"
            assert jpeg_data[-2:] == b"\xff\xd9", "Invalid JPEG End of Image marker"
            print(f"  -> /snapshot PASSED: Received valid JPEG image ({len(jpeg_data)} bytes).")

        # 3. Test /stream endpoint (Read first 2 frame chunks)
        print(f"[TEST] Testing {base_url}/stream ...")
        req = urllib.request.Request(f"{base_url}/stream")
        with urllib.request.urlopen(req, timeout=5) as stream_resp:
            assert stream_resp.status == 200
            ct = stream_resp.headers.get("Content-Type", "")
            assert "multipart/x-mixed-replace" in ct, f"Unexpected Content-Type: {ct}"

            # Read a chunk from the stream to verify boundary and JPEG content
            chunk = stream_resp.read(4096)
            assert b"Content-Type: image/jpeg" in chunk
            assert b"\xff\xd8" in chunk
            print("  -> /stream PASSED: Received multipart MJPEG stream chunk successfully.")

        print("\n[ALL TESTS PASSED] Mock Camera Server operates correctly per DATA_CONTRACT!")

    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    test_mock_camera_server()
