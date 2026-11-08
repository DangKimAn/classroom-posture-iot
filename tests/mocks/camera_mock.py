#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock ESP32-CAM MJPEG Stream Server
Role: TV1 (Mocking & Testing)

Mimics the ESP32-CAM HTTP MJPEG streaming service (/stream) and health status (/status)
for development and testing of Vision (TV2) and Integration tests without physical hardware.
"""

import io
import time
import math
import json
import argparse
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Try importing Pillow to draw synthetic posture frames; fallback to minimal JPEG if missing
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BOUNDARY = "123456789000000000000987654321"

# Standalone precomputed valid JPEG frame for CI environments without Pillow
FALLBACK_JPEG_BYTES = (
    b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00'
    b'\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12'
    b'\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
    b'\xff\xdb\x00C\x01\t\t\t\x0c\x0b\x0c\x18\r\r\x182!\x1c!222222222222222222222222222222'
    b'222222222222222222\xff\xc0\x00\x11\x08\x000\x00@\x03\x01"\x00\x02\x11\x01\x03\x11\x01'
    b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04'
    b'\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142'
    b'\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:'
    b'CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97'
    b'\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba'
    b'\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3'
    b'\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xc4\x00\x1f\x01'
    b'\x00\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05'
    b'\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x11\x00\x02\x01\x02\x04\x04\x03\x04\x07\x05\x04\x04'
    b'\x00\x01\x02w\x00\x01\x02\x03\x11\x04\x05!1\x06\x12AQ\x07aq\x13"2\x81\x08\x14B\x91\xa1'
    b'\xb1\xc1\t#3R\xf0\x15br\xd1\n\x16$4\xe1%\xf1\x17\x18\x19\x1a&\'()*56789:CDEFGHIJSTUVWXYZ'
    b'cdefghijstuvwxyz\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a'
    b'\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5'
    b'\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9'
    b'\xea\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00'
    b'?\x00\xf2\xba(\xa2\xb4 (\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00'
    b'(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00(\xa2\x8a\x00\xff\xd9'
)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads for non-blocking streaming."""
    daemon_threads = True
    allow_reuse_address = True


class MockCameraFrameGenerator:
    """Generates synthetic JPEG frames simulating a classroom seat and student posture."""

    def __init__(self, width: int = 640, height: int = 480):
        self.width = width
        self.height = height
        self.start_time = time.time()
        self.frame_id = 0

    def get_frame(self) -> bytes:
        """Render a synthetic frame as JPEG bytes."""
        self.frame_id += 1
        elapsed = time.time() - self.start_time

        if not HAS_PIL:
            return FALLBACK_JPEG_BYTES

        # Create canvas (classroom background)
        img = Image.new("RGB", (self.width, self.height), color=(35, 39, 46))
        draw = ImageDraw.Draw(img)

        # Draw grid lines to simulate classroom floor / walls
        for y in range(0, self.height, 60):
            draw.line([(0, y), (self.width, y)], fill=(45, 51, 60), width=1)
        for x in range(0, self.width, 80):
            draw.line([(x, 0), (x, self.height)], fill=(45, 51, 60), width=1)

        # Simulate student posture animation (oscillation)
        # Period: ~12 seconds cycle between upright, slouching, and leaning
        angle_deg = 20.0 * math.sin(elapsed * 0.5)
        angle_rad = math.radians(angle_deg)

        # Seat / Desk representation (Seat S01)
        desk_x1, desk_y1 = 180, 320
        desk_x2, desk_y2 = 460, 440
        draw.rectangle([desk_x1, desk_y1, desk_x2, desk_y2], fill=(60, 68, 80), outline=(100, 110, 130), width=2)
        draw.text((desk_x1 + 10, desk_y1 + 10), "DESK S01 (Simulated ROI)", fill=(180, 190, 210))

        # Hip center (base)
        hip_x, hip_y = 320, 330
        # Shoulder center (swaying with angle)
        trunk_length = 120
        shoulder_x = int(hip_x + trunk_length * math.sin(angle_rad))
        shoulder_y = int(hip_y - trunk_length * math.cos(angle_rad))

        # Head / Neck
        head_length = 45
        head_x = int(shoulder_x + head_length * math.sin(angle_rad))
        head_y = int(shoulder_y - head_length * math.cos(angle_rad))

        # Draw spine / torso line
        draw.line([(hip_x, hip_y), (shoulder_x, shoulder_y)], fill=(76, 175, 80), width=6)

        # Draw shoulders
        shoulder_half_width = 35
        left_sh_x = int(shoulder_x - shoulder_half_width * math.cos(angle_rad))
        left_sh_y = int(shoulder_y - shoulder_half_width * math.sin(angle_rad))
        right_sh_x = int(shoulder_x + shoulder_half_width * math.cos(angle_rad))
        right_sh_y = int(shoulder_y + shoulder_half_width * math.sin(angle_rad))
        draw.line([(left_sh_x, left_sh_y), (right_sh_x, right_sh_y)], fill=(129, 199, 132), width=5)

        # Draw head circle
        head_radius = 22
        draw.ellipse(
            [head_x - head_radius, head_y - head_radius, head_x + head_radius, head_y + head_radius],
            fill=(255, 204, 128),
            outline=(255, 255, 255),
            width=2
        )

        # Draw keypoint dots (simulating landmarks)
        keypoints = [
            (head_x, head_y, "Nose"),
            (left_sh_x, left_sh_y, "L_Sh"),
            (right_sh_x, right_sh_y, "R_Sh"),
            (hip_x, hip_y, "Hip")
        ]
        for kx, ky, _ in keypoints:
            draw.ellipse([kx - 4, ky - 4, kx + 4, ky + 4], fill=(244, 67, 54))

        # Overlay telemetry text
        now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        draw.text((15, 15), f"MOCK ESP32-CAM [AI-Thinker OV2640]", fill=(0, 230, 118))
        draw.text((15, 35), f"UTC: {now_utc} | Frame: {self.frame_id}", fill=(200, 200, 200))
        draw.text((15, 55), f"Simulated Trunk Angle: {abs(angle_deg):.1f} deg", fill=(255, 215, 0))

        # Save to buffer as JPEG
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


class MockCameraHTTPHandler(BaseHTTPRequestHandler):
    """HTTP Request handler for mock ESP32-CAM endpoints."""

    def log_message(self, format, *args):
        # Override to suppress noisy per-frame log messages
        pass

    def do_GET(self):
        if self.path == "/":
            self.handle_index()
        elif self.path == "/status":
            self.handle_status()
        elif self.path == "/snapshot":
            self.handle_snapshot()
        elif self.path == "/stream":
            self.handle_stream()
        else:
            self.send_error(404, "Endpoint not found")

    def handle_index(self):
        """Serve HTML live stream viewer with scaled viewport."""
        html = (
            "<!DOCTYPE html>"
            "<html><head><meta charset='utf-8'><title>Mock ESP32-CAM Viewer</title>"
            "<style>body{background:#121214;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}"
            "img{max-width:800px;width:100%;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.6)}</style></head>"
            "<body><div style='text-align:center'>"
            "<h2>Classroom Posture Monitor — Mock Camera</h2>"
            "<img src='/stream'>"
            "</div></body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def handle_status(self):
        """Return simulated device telemetry JSON."""
        status_data = {
            "device": "ESP32-CAM (Mock)",
            "status": "ONLINE",
            "stream_endpoint": "/stream",
            "resolution": f"{self.server.generator.width}x{self.server.generator.height}",
            "target_fps": self.server.target_fps,
            "uptime_sec": int(time.time() - self.server.generator.start_time),
            "simulated_seat": "S01"
        }
        payload = json.dumps(status_data, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def handle_snapshot(self):
        """Return a single JPEG snapshot."""
        jpeg_bytes = self.server.generator.get_frame()
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(jpeg_bytes)

    def handle_stream(self):
        """Return continuous multipart/x-mixed-replace MJPEG stream."""
        self.send_response(200)
        self.send_header(
            "Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}"
        )
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, private")
        self.end_headers()

        frame_interval = 1.0 / self.server.target_fps

        try:
            while True:
                start_loop = time.time()
                jpeg_bytes = self.server.generator.get_frame()

                part_header = (
                    f"--{BOUNDARY}\r\n"
                    f"Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(jpeg_bytes)}\r\n\r\n"
                ).encode("ascii")

                self.wfile.write(part_header)
                self.wfile.write(jpeg_bytes)
                self.wfile.write(b"\r\n")

                # Throttle to simulate camera frame rate
                elapsed = time.time() - start_loop
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except (BrokenPipeError, ConnectionResetError):
            # Client closed stream connection normally
            pass


def run_mock_server(host: str = "0.0.0.0", port: int = 8080, fps: int = 25):
    """Start and run the mock camera server."""
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, MockCameraHTTPHandler)
    httpd.target_fps = fps
    httpd.generator = MockCameraFrameGenerator(width=640, height=480)

    print("========================================================")
    print("      Classroom Posture Monitor — Mock Camera Server    ")
    print("========================================================")
    print(f"[Mock CAM] Server listening on http://{host}:{port}")
    print(f"[Mock CAM] Stream URL  : http://{host}:{port}/stream")
    print(f"[Mock CAM] Status URL  : http://{host}:{port}/status")
    print(f"[Mock CAM] Snapshot URL: http://{host}:{port}/snapshot")
    print(f"[Mock CAM] Target FPS  : {fps} FPS")
    print("Press Ctrl+C to terminate.")
    print("========================================================")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Mock CAM] Shutting down server...")
    finally:
        httpd.server_close()
        print("[Mock CAM] Server stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock ESP32-CAM MJPEG Stream Server")
    parser.add_argument("--host", default="0.0.0.0", help="Binding host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    parser.add_argument("--fps", type=int, default=25, help="Simulation FPS (default: 25)")
    args = parser.parse_args()

    run_mock_server(host=args.host, port=args.port, fps=args.fps)
