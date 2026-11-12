"""Lazy YOLOv8 Pose adapter with no identity tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Pose:
    """One anonymous person's COCO keypoints and aggregate confidence."""

    keypoints: dict[str, tuple[float, float] | None]
    confidence: float


COCO_POINTS = {
    0: "nose", 1: "left_eye", 2: "right_eye", 3: "left_ear", 4: "right_ear",
    5: "left_shoulder", 6: "right_shoulder", 11: "left_hip", 12: "right_hip",
}


class PoseEstimator:
    """Run YOLOv8 pose inference; the model is loaded only on first inference."""

    def __init__(self, model_name: str = "yolov8n-pose.pt", keypoint_confidence: float = 0.5) -> None:
        self.model_name = model_name
        self.keypoint_confidence = keypoint_confidence
        self._model: Any | None = None

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from ultralytics import YOLO
            except ImportError as error:
                raise RuntimeError("ultralytics is required for pose inference") from error
            self._model = YOLO(self.model_name)
        return self._model

    def infer(self, frame: Any) -> list[Pose]:
        """Return anonymous poses with low-confidence points set to ``None``."""
        results = self._load_model()(frame, verbose=False)
        poses: list[Pose] = []
        for result in results:
            keypoints = getattr(result, "keypoints", None)
            if keypoints is None or keypoints.xy is None:
                continue
            xy_rows = keypoints.xy.cpu().tolist()
            confidence_rows = keypoints.conf.cpu().tolist() if keypoints.conf is not None else []
            for index, row in enumerate(xy_rows):
                confidences = confidence_rows[index] if index < len(confidence_rows) else []
                selected: dict[str, tuple[float, float] | None] = {}
                usable_confidences: list[float] = []
                for point_index, point_name in COCO_POINTS.items():
                    confidence = float(confidences[point_index]) if point_index < len(confidences) else 0.0
                    if point_index < len(row) and confidence >= self.keypoint_confidence:
                        selected[point_name] = (float(row[point_index][0]), float(row[point_index][1]))
                        usable_confidences.append(confidence)
                    else:
                        selected[point_name] = None
                poses.append(Pose(selected, sum(usable_confidences) / len(usable_confidences) if usable_confidences else 0.0))
        return poses

