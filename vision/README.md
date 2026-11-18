# Vision module

`vision/` reads an MJPEG/HTTP camera stream or a local approved test video,
estimates anonymous body pose with YOLOv8 Pose, derives a 2D trunk angle, and
publishes posture events to MQTT. It never persists or publishes frames.

## Install and run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r vision/requirements.txt
$env:CAM_STREAM_URL = "http://camera-host/stream"
$env:MQTT_HOST = "localhost"
$env:MQTT_USERNAME = "your-local-broker-user"
$env:MQTT_PASSWORD = "your-local-broker-password"
python vision/main.py --config vision/config.yaml --debug
python -m pytest -q tests/test_vision_pipeline.py tests/test_classifier.py
```

For a local approved test source, set `VIDEO_FILE` instead of
`CAM_STREAM_URL`. Do not add the video to Git.

Required settings are `CAM_STREAM_URL` (or `VIDEO_FILE`), MQTT connection
settings, and credentials for the authenticated local Compose broker. Vision
loads simple `KEY=VALUE` entries from the repository-root `.env` when launched
with the command above. Values already exported in PowerShell take precedence.
Alternatively, export credentials in the process as shown. If either MQTT
credential is absent, Vision reports that both are required and retries without
printing credential values. Keep `.env` out of Git.

## Configuration

All thresholds, keypoint confidence, smoothing, publishing cadence, and seat
regions are in `config.yaml`. `seat_regions` must contain the real anonymous
seat regions for the camera view; Vision stops at startup with a configuration
message if the list is empty. Do not use example seat IDs as real configuration.
Each seat region uses anonymous `seat_id` and
pixel bounds: `seat_id`, `left`, `top`, `right`, `bottom`. A pose outside every
configured region is not published.

The trunk angle is the angle in degrees between the image vertical and the
segment from the shoulder midpoint to the hip midpoint. `left/right_shoulder`
are COCO points 5/6 and `left/right_hip` are points 11/12. Missing or
low-confidence points produce `unknown`; no identity tracking is used.

Seat assignment uses the hip midpoint, falling back to the shoulder midpoint.
The current operating assumption is **one person per seat region**: if several
poses map to the same seat in a frame, Vision keeps the pose with higher pose
confidence, then the larger intersection between its YOLO bounding box and the
seat region. Exact ties keep the first detector result. A pose whose reference
point lies in overlapping regions goes to the region with the larger bounding
box intersection (ties use `seat_id` order). A pose is never assigned to more
than one seat. Conflicts produce a rate-limited warning per seat with
cumulative conflict and dropped-pose counts. This is an assumption; it has not
been tested against real multi-person classroom scenes.

Thresholds are experimental 2D-image parameters, not a health assessment:
`<=15` is `upright`, `20.. <25` is `leaning`, `>=25` is `slouching`, and the
intermediate uncertainty band is `unknown`. Majority voting runs over the
configured latest frames.

## Contract and assumptions

Events use the existing `classroom/posture/events` contract and contain only
`event_id`, UTC `ts`, `seat_id`, `label`, `angles.trunk`, `confidence`, and
`model`. Publisher defaults are QoS 1 and `retain=false`.

The repository decisions D-01, D-02, D-03, D-09, and D-10 are still OPEN.
This module uses their documented defaults: MVP labels, configured seat regions
using hip/shoulder midpoint, and QoS 1 without retain. It does not settle or
modify those shared decisions. Hip-less fallback geometry is intentionally not
published until the group confirms D-02.

## Validation and limitations

Run `pytest -q` for geometry, boundaries, smoothing, seat mapping, and event
schema tests. Camera, YOLO model download, broker reconnection, FPS, latency,
and accuracy have **not been measured** in this workspace because no approved
camera/video/model/broker was supplied. When data is approved, record lighting,
camera angle, distance, resolution, FPS, sample count, CPU/GPU, confusion
matrix, precision/recall/F1, inference FPS, and end-to-end latency.

## Integration checklist

- TV1 provides an approved reachable `CAM_STREAM_URL`; Vision changes only its
  environment value, never firmware code.
- Configure one anonymous pixel region for every available seat before
  publishing; poses outside those regions are safely ignored.
- TV3 starts the broker and validates a sample Vision event against the shared
  schema. Vision does not import backend code.
- Test camera and broker reconnection on the actual isolated classroom network
  before declaring the module ready for demonstration.

## ESP32-CAM preview

The local Streamlit preview accepts an HTTP MJPEG URL and reads frames from an
ESP32-CAM about twice per second. It loads the operational `config.yaml`,
including the real anonymous seat regions, and uses the existing pose, angle,
classifier, and seat assignment logic. Frames and overlays stay in process
memory, are not written to disk, and are not published to MQTT. This preview is
for interaction checks, not FPS or latency measurement.

Install the optional preview dependency and run from the repository root:

    pip install -r vision/requirements-camera-preview.txt
    streamlit run vision/esp32_camera_preview.py --server.address 127.0.0.1 --server.port 8501

Open http://127.0.0.1:8501, confirm approved test use, and follow these steps:

1. Start the ESP32-CAM and open Arduino IDE Serial Monitor at 115200 baud.
2. Copy the `Stream URL` printed after Wi-Fi connects, for example
   `http://192.168.1.105/stream`. The computer running Streamlit must be able
   to reach that address on the same LAN.
3. Paste it into **URL luồng MJPEG** and click **Kết nối / Bắt đầu**. Click
   **Ngắt kết nối** to release the camera.

If the URL is invalid or the camera cannot be reached, the page displays an
error. The app requires model
weights to already exist locally under the repository root or `vision/`; it
does not download them. Without weights, the camera stream can still be
previewed but pose inference is unavailable. Use only approved test data; do
not point the camera at students without the required consent.
