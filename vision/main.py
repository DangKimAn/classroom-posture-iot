"""Run the privacy-preserving vision-to-MQTT pipeline."""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any

try:  # Package execution: python -m vision.main
    from .angle import trunk_angle_from_keypoints
    from .capture import VideoCaptureStream
    from .classifier import PostureClassifier
    from .mqtt_publisher import MqttPublisher, build_event
    from .pose_estimator import PoseEstimator
    from .seat_assignment import assign_poses_to_seats
except ImportError:  # Direct script execution: python vision/main.py
    from angle import trunk_angle_from_keypoints
    from capture import VideoCaptureStream
    from classifier import PostureClassifier
    from mqtt_publisher import MqttPublisher, build_event
    from pose_estimator import PoseEstimator
    from seat_assignment import assign_poses_to_seats

LOGGER = logging.getLogger(__name__)


def log_seat_conflicts(conflicts: list[Any], totals: dict[str, list[float]], now: float) -> None:
    """Accumulate conflicts and warn at most once per seat every 60 seconds."""
    for conflict in conflicts:
        state = totals.setdefault(conflict.seat_id, [0, 0, -60.0])
        state[0] += 1
        state[1] += conflict.dropped_poses
        if now - state[2] >= 60.0:
            LOGGER.warning(
                "Seat assignment conflict: seat_id=%s conflict_count=%d dropped_poses=%d",
                conflict.seat_id,
                int(state[0]),
                int(state[1]),
            )
            state[2] = now


def load_config(path: Path) -> dict[str, Any]:
    """Load YAML configuration, retaining all runtime parameters outside code."""
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("PyYAML is required to load config") from error
    with path.open("r", encoding="utf-8") as config_file:
        return validate_config(yaml.safe_load(config_file) or {})


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate the minimum Vision configuration before opening hardware I/O."""
    try:
        model = config["model"]
        classifier = config["classifier"]
        publisher = config["publisher"]
        thresholds = (float(classifier["upright_max"]), float(classifier["leaning_min"]), float(classifier["slouching_min"]))
        window_size = int(classifier["smoothing_window"])
        interval = float(publisher["interval_seconds"])
        keypoint_confidence = float(model["keypoint_confidence"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Invalid vision config: missing or invalid required value") from error
    if not 0 <= thresholds[0] <= thresholds[1] <= thresholds[2]:
        raise ValueError("Invalid vision config: thresholds must be ordered")
    if window_size < 1 or interval <= 0 or not 0 <= keypoint_confidence <= 1:
        raise ValueError("Invalid vision config: window, interval, or keypoint confidence")
    regions = config.get("seat_regions", [])
    if not isinstance(regions, list):
        raise ValueError("Invalid vision config: seat_regions must be a list")
    if not regions:
        raise ValueError(
            "Invalid vision config: seat_regions is empty; configure anonymous "
            "seat_id pixel bounds in vision/config.yaml before starting Vision. "
            "Run `python -m vision.tools.calibrate_seats` to draw regions first"
        )
    for region in regions:
        try:
            seat_id = str(region["seat_id"])
            left, top, right, bottom = (float(region[key]) for key in ("left", "top", "right", "bottom"))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid vision config: malformed seat region") from error
        if not seat_id or left >= right or top >= bottom:
            raise ValueError("Invalid vision config: invalid seat region bounds")
    return config


def run(config: dict[str, Any], debug: bool = False) -> None:
    """Process frames indefinitely; failed publishing does not terminate capture."""
    model_config = config["model"]
    classifier_config = config["classifier"]
    publisher_config = config["publisher"]
    capture = VideoCaptureStream()
    estimator = PoseEstimator(model_config["name"], model_config["keypoint_confidence"])
    publisher = MqttPublisher()
    last_published: dict[str, tuple[str, float]] = {}
    classifiers: dict[str, PostureClassifier] = {}
    conflict_totals: dict[str, list[float]] = {}
    try:
        while True:
            frame = capture.read()
            if frame is None:
                continue
            try:
                poses = estimator.infer(frame)
            except RuntimeError as error:
                LOGGER.error("Pose inference unavailable: %s", error)
                return
            assignments, conflicts = assign_poses_to_seats(poses, config.get("seat_regions", []))
            conflict_now = time.monotonic()
            log_seat_conflicts(conflicts, conflict_totals, conflict_now)
            for pose_index, pose in enumerate(poses):
                seat_id = assignments.get(pose_index)
                if seat_id is None:
                    continue
                angle = trunk_angle_from_keypoints(pose.keypoints)
                classifier = classifiers.setdefault(
                    seat_id,
                    PostureClassifier(
                        classifier_config["upright_max"], classifier_config["slouching_min"],
                        classifier_config["leaning_min"], classifier_config["smoothing_window"],
                    ),
                )
                label, _raw_label = classifier.classify(angle)
                # A missing angle cannot be paired with a smoothed, stale label.
                if angle is None:
                    label = "unknown"
                previous = last_published.get(seat_id)
                now = time.monotonic()
                changed = previous is None or previous[0] != label
                due = previous is None or now - previous[1] >= publisher_config["interval_seconds"]
                if due or (publisher_config["publish_on_change"] and changed):
                    event = build_event(seat_id, label, angle, pose.confidence, model_config["name"])
                    if publisher.publish(event):
                        last_published[seat_id] = (label, now)
            if debug:
                LOGGER.debug("Processed frame")
    finally:
        capture.close()
        publisher.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yaml"))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    load_environment_file()
    run(load_config(args.config), args.debug)


def load_environment_file(path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries from the repository .env without overriding exports."""
    env_file = path or (Path(__file__).resolve().parent.parent / ".env")
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        key = key.strip()
        if key and key.replace("_", "").isalnum():
            os.environ.setdefault(key, value.strip().strip("\"'"))


if __name__ == "__main__":
    main()

