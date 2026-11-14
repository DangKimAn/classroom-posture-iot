import os
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "vision"))

from angle import calculate_angle_vertical, trunk_angle_from_keypoints
from classifier import PostureClassifier
from mqtt_publisher import build_event
from seat_assignment import assign_seat, reference_point


def test_angle_rejects_missing_and_duplicate_points():
    assert calculate_angle_vertical(None, (1, 2)) is None
    assert calculate_angle_vertical((1, 2), (1, 2)) is None
    assert trunk_angle_from_keypoints({"left_shoulder": (1, 1)}) is None


def test_classifier_boundaries_and_smoothing():
    classifier = PostureClassifier(window_size=3)
    assert classifier.classify_raw(15.0) == "upright"
    assert classifier.classify_raw(19.9) == "unknown"
    assert classifier.classify_raw(20.0) == "leaning"
    assert classifier.classify_raw(25.0) == "slouching"
    assert classifier.classify(None)[0] == "unknown"
    assert classifier.classify(10.0)[0] == "upright"
    assert classifier.classify(10.0)[0] == "upright"


def test_anonymous_seat_assignment():
    regions = [{"seat_id": "S01", "left": 0, "top": 0, "right": 100, "bottom": 100}]
    keypoints = {"left_hip": (40, 60), "right_hip": (60, 60)}
    assert reference_point(keypoints) == (50.0, 60.0)
    assert assign_seat(reference_point(keypoints), regions) == "S01"
    assert assign_seat((101, 60), regions) is None


def test_contract_event_contains_only_required_fields():
    event = build_event("S01", "leaning", 20.0, 0.91, "yolov8n-pose.pt")
    assert set(event) == {"event_id", "ts", "seat_id", "label", "angles", "confidence", "model"}
    assert set(event["angles"]) == {"trunk"}
    assert re.fullmatch(r"[0-9a-f-]{36}", event["event_id"])
    assert event["ts"].endswith("Z")


def test_publisher_environment_defaults_are_not_credentials():
    os.environ.pop("MQTT_PASSWORD", None)
    from mqtt_publisher import MqttPublisher
    publisher = MqttPublisher(host="broker", port=1883)
    assert publisher.topic == "classroom/posture/events"


def test_package_import_and_config_validation():
    from vision.main import validate_config

    config = {
        "model": {"name": "yolov8n-pose.pt", "keypoint_confidence": 0.5},
        "classifier": {"upright_max": 15, "leaning_min": 20, "slouching_min": 25, "smoothing_window": 5},
        "publisher": {"interval_seconds": 1, "publish_on_change": True},
        "seat_regions": [{"seat_id": "S01", "left": 0, "top": 0, "right": 10, "bottom": 10}],
    }
    assert validate_config(config) is config
    config["publisher"]["interval_seconds"] = 0
    with pytest.raises(ValueError, match="interval"):
        validate_config(config)


def test_pose_estimator_is_lazy_without_ultralytics_import():
    from pose_estimator import PoseEstimator

    estimator = PoseEstimator()
    assert estimator._model is None


def test_capture_reconnects_after_read_failure(monkeypatch):
    from capture import VideoCaptureStream

    class FakeCapture:
        connections = 0

        def __init__(self, _source):
            self.connection_number = FakeCapture.connections
            FakeCapture.connections += 1

        def isOpened(self):
            return True

        def read(self):
            return (self.connection_number > 0, "frame")

        def release(self):
            return None

    class FakeCv2:
        VideoCapture = FakeCapture

    monkeypatch.setitem(sys.modules, "cv2", FakeCv2)
    stream = VideoCaptureStream(source="mock://camera", reconnect_delay_seconds=0)
    assert stream.read() == "frame"


def test_publisher_failure_uses_retry_backoff(monkeypatch):
    from mqtt_publisher import MqttPublisher

    publisher = MqttPublisher(retry_delay_seconds=60)

    def fail_connect():
        raise OSError("broker unavailable")

    monkeypatch.setattr(publisher, "connect", fail_connect)
    assert publisher.publish(build_event("S01", "unknown", None, 0.0, "test")) is False
    assert publisher.publish(build_event("S01", "unknown", None, 0.0, "test")) is False
