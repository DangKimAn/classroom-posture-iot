#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classroom Posture Monitor — Camera FPS & Latency Benchmark Tool
Role: TV1 (Testing & Performance Measurement)

Measures real-time streaming performance from ESP32-CAM or Mock Camera:
- Average, Min, Max FPS
- Frame Delta Time (latency between frames) & Jitter (std dev)
- Data Throughput (Mbps) and Average JPEG Size (KB)
- Estimated Dropped Frames
"""

import sys
import time
import argparse
import urllib.request
import statistics

def benchmark_stream(stream_url: str, duration_sec: int = 10):
    print("=" * 65)
    print("    ESP32-CAM Stream Performance & FPS Benchmark Tool    ")
    print("=" * 65)
    print(f"Target Stream URL : {stream_url}")
    print(f"Test Duration     : {duration_sec} seconds")
    print("Connecting to camera stream...")

    try:
        req = urllib.request.Request(
            stream_url,
            headers={"User-Agent": "PostureMonitor-FPS-Benchmark/1.0"}
        )
        stream = urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to {stream_url}: {e}")
        print("Please check:")
        print("  1. ESP32-CAM and your laptop are on the same Wi-Fi network.")
        print("  2. The IP address is correct.")
        print("  3. The camera web server is running.")
        sys.exit(1)

    content_type = stream.headers.get("Content-Type", "")
    if "multipart/x-mixed-replace" not in content_type:
        print(f"[WARNING] Stream Content-Type is '{content_type}', expected 'multipart/x-mixed-replace'")

    print("[CONNECTED] Reading video stream and analyzing frame rate...\n")

    frame_timestamps = []
    frame_sizes = []
    buffer = b""
    start_test_time = time.time()
    last_ui_update = start_test_time
    total_bytes_received = 0

    try:
        while True:
            now = time.time()
            if now - start_test_time >= duration_sec:
                break

            chunk = stream.read(4096)
            if not chunk:
                print("\n[WARNING] Stream closed by server.")
                break

            buffer += chunk
            total_bytes_received += len(chunk)

            # Search for JPEG boundaries (0xFF, 0xD8 = SOI, 0xFF, 0xD9 = EOI)
            while True:
                soi = buffer.find(b"\xff\xd8")
                if soi == -1:
                    # Keep only last 2 bytes in case marker is split across chunks
                    buffer = buffer[-2:]
                    break

                eoi = buffer.find(b"\xff\xd9", soi + 2)
                if eoi == -1:
                    # Incomplete frame, wait for next chunk
                    buffer = buffer[soi:]
                    break

                # Valid JPEG frame extracted
                frame_data = buffer[soi : eoi + 2]
                frame_len = len(frame_data)
                frame_time = time.time()

                frame_timestamps.append(frame_time)
                frame_sizes.append(frame_len)

                # Move buffer past current frame
                buffer = buffer[eoi + 2:]

                # Realtime progress update every 1 second
                if frame_time - last_ui_update >= 1.0:
                    current_count = len(frame_timestamps)
                    elapsed = frame_time - start_test_time
                    instant_fps = current_count / elapsed if elapsed > 0 else 0
                    print(f"  --> Progress: {elapsed:.1f}s / {duration_sec}s | Received: {current_count} frames | Avg: {instant_fps:.1f} FPS", end="\r")
                    last_ui_update = frame_time

    except KeyboardInterrupt:
        print("\n\n[INFO] Benchmark interrupted by user.")
    finally:
        stream.close()

    total_frames = len(frame_timestamps)
    total_duration = time.time() - start_test_time

    print("\n" + "=" * 65)
    print("                     BENCHMARK RESULTS                   ")
    print("=" * 65)

    if total_frames < 2:
        print("[ERROR] Not enough frames captured to calculate metrics.")
        return

    # Calculate intervals (delta t) between consecutive frames
    deltas = [
        (frame_timestamps[i] - frame_timestamps[i - 1]) * 1000.0
        for i in range(1, total_frames)
    ]

    avg_fps = total_frames / total_duration
    avg_delta_ms = statistics.mean(deltas)
    min_delta_ms = min(deltas)
    max_delta_ms = max(deltas)
    jitter_ms = statistics.stdev(deltas) if len(deltas) > 1 else 0.0

    # Instantaneous FPS across 1-second intervals
    max_instant_fps = 1000.0 / min_delta_ms if min_delta_ms > 0 else 0.0
    min_instant_fps = 1000.0 / max_delta_ms if max_delta_ms > 0 else 0.0

    avg_frame_kb = statistics.mean(frame_sizes) / 1024.0
    total_mb = total_bytes_received / (1024.0 * 1024.0)
    throughput_mbps = (total_bytes_received * 8.0) / (total_duration * 1000.0 * 1000.0)

    # Frame drop estimate: interval > 2x average interval
    drop_threshold = avg_delta_ms * 2.0
    lagged_frames = sum(1 for d in deltas if d > drop_threshold)

    print(f"Total Frames Received : {total_frames} frames")
    print(f"Actual Test Duration  : {total_duration:.2f} seconds")
    print(f"Average Frame Rate    : {avg_fps:.2f} FPS")
    print(f"Peak Frame Rate       : {max_instant_fps:.2f} FPS")
    print(f"Min Frame Rate        : {min_instant_fps:.2f} FPS")
    print("-" * 65)
    print(f"Avg Frame Interval    : {avg_delta_ms:.2f} ms")
    print(f"Frame Jitter (StdDev) : {jitter_ms:.2f} ms")
    print(f"Min Frame Interval    : {min_delta_ms:.2f} ms")
    print(f"Max Frame Interval    : {max_delta_ms:.2f} ms")
    print(f"Lagged / Stalled Frame: {lagged_frames} frames (gap > {drop_threshold:.1f}ms)")
    print("-" * 65)
    print(f"Avg Frame Size        : {avg_frame_kb:.2f} KB")
    print(f"Total Data Transferred: {total_mb:.2f} MB")
    print(f"Network Throughput    : {throughput_mbps:.2f} Mbps")
    print("=" * 65)

    # Health evaluation
    if avg_fps >= 20.0:
        print("Verdict: EXCELLENT — Suitable for high-accuracy YOLOv8 real-time pose tracking.")
    elif avg_fps >= 12.0:
        print("Verdict: GOOD — Sufficient for classroom posture classification with smoothing.")
    else:
        print("Verdict: LOW — Check Wi-Fi signal (RSSI), sensor clock or power supply brownout.")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32-CAM FPS & Throughput Benchmark")
    parser.add_argument(
        "--url",
        default="http://localhost:8080/stream",
        help="Stream URL (e.g. http://192.168.1.105/stream or http://localhost:8080/stream)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Test duration in seconds (default: 5)"
    )
    args = parser.parse_args()

    benchmark_stream(args.url, args.duration)
