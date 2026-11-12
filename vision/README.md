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
python vision/main.py --config vision/config.yaml --debug
pytest -q
```

For a local approved test source, set `VIDEO_FILE` instead of
`CAM_STREAM_URL`. Do not add the video to Git.

Required environment variables are `CAM_STREAM_URL` (or `VIDEO_FILE`),
`MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, and `MQTT_TOPIC`.
Credentials are read only from the environment and are never logged.

## Configuration

All thresholds, keypoint confidence, smoothing, publishing cadence, and seat
regions are in `config.yaml`. Each seat region uses anonymous `seat_id` and
pixel bounds: `seat_id`, `left`, `top`, `right`, `bottom`. A pose outside every
configured region is not published.

The trunk angle is the angle in degrees between the image vertical and the
segment from the shoulder midpoint to the hip midpoint. `left/right_shoulder`
are COCO points 5/6 and `left/right_hip` are points 11/12. Missing or
low-confidence points produce `unknown`; no identity tracking is used.

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
