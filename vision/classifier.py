"""Configurable posture classification and temporal majority smoothing."""

from __future__ import annotations

from collections import Counter, deque
from math import isfinite

VALID_LABELS = ("upright", "slouching", "leaning", "unknown")


class PostureClassifier:
    """Convert a trunk angle in degrees to a stable MVP posture label."""

    def __init__(
        self,
        upright_max: float = 15.0,
        slouching_min: float = 25.0,
        leaning_min: float = 20.0,
        window_size: int = 5,
    ) -> None:
        if not 0 <= upright_max <= leaning_min <= slouching_min:
            raise ValueError("Thresholds must satisfy 0 <= upright <= leaning <= slouching")
        if window_size < 1:
            raise ValueError("window_size must be positive")
        self.upright_max = upright_max
        self.leaning_min = leaning_min
        self.slouching_min = slouching_min
        self._labels: deque[str] = deque(maxlen=window_size)

    def classify_raw(self, angle: float | None) -> str:
        """Classify one angle without temporal smoothing."""
        if angle is None or not isinstance(angle, (int, float)) or not isfinite(angle) or angle < 0:
            return "unknown"
        if angle <= self.upright_max:
            return "upright"
        if angle >= self.slouching_min:
            return "slouching"
        # The 15--20 degree interval is deliberately conservative: it remains
        # unknown rather than asserting a posture below the leaning threshold.
        if angle >= self.leaning_min:
            return "leaning"
        return "unknown"

    def classify(self, angle: float | None) -> tuple[str, str]:
        """Return ``(smoothed_label, raw_label)`` for one frame."""
        raw_label = self.classify_raw(angle)
        self._labels.append(raw_label)
        counts = Counter(self._labels)
        # max preserves the latest occurrence as a deterministic tie-breaker.
        smoothed = max(reversed(self._labels), key=lambda label: counts[label])
        return smoothed, raw_label

