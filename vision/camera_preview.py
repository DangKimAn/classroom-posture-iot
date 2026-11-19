"""In-memory frame analysis used by the local ESP32-CAM preview."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

try:
    from .angle import trunk_angle_from_keypoints
    from .classifier import PostureClassifier
    from .pose_estimator import PoseEstimator
    from .seat_assignment import assign_seat, reference_point
except ImportError:  # pragma: no cover - direct-script compatibility
    from angle import trunk_angle_from_keypoints
    from classifier import PostureClassifier
    from pose_estimator import PoseEstimator
    from seat_assignment import assign_seat, reference_point


@dataclass(frozen=True)
class PosePreview:
    """Anonymous posture result for one detected pose."""

    seat_id: str | None
    label: str
    trunk_angle: float | None
    confidence: float
    keypoints: Mapping[str, tuple[float, float] | None]


def analyze_frame(
    frame: Any,
    estimator: PoseEstimator,
    classifier_config: Mapping[str, Any],
    seat_regions: Sequence[Mapping[str, object]],
) -> list[PosePreview]:
    """Run pose, angle, label, and seat logic without publishing or saving."""
    classifier = PostureClassifier(
        upright_max=float(classifier_config["upright_max"]),
        leaning_min=float(classifier_config["leaning_min"]),
        slouching_min=float(classifier_config["slouching_min"]),
        window_size=1,
    )
    detections: list[PosePreview] = []
    for pose in estimator.infer(frame):
        angle = trunk_angle_from_keypoints(pose.keypoints)
        detections.append(
            PosePreview(
                seat_id=assign_seat(reference_point(pose.keypoints), seat_regions),
                label=classifier.classify_raw(angle),
                trunk_angle=angle,
                confidence=float(pose.confidence),
                keypoints=pose.keypoints,
            )
        )
    return detections
