"""Map an anonymous body reference point to configured seat regions."""

from __future__ import annotations

from typing import Mapping, Sequence

try:  # Supports both ``python vision/main.py`` and ``python -m vision.main``.
    from .angle import midpoint
except ImportError:  # pragma: no cover - exercised by direct-script execution.
    from angle import midpoint


def reference_point(keypoints: Mapping[str, Sequence[float] | None]) -> tuple[float, float] | None:
    """Prefer hip midpoint, then shoulder midpoint, without identifying a person."""
    return midpoint(keypoints.get("left_hip"), keypoints.get("right_hip")) or midpoint(
        keypoints.get("left_shoulder"), keypoints.get("right_shoulder")
    )


def assign_seat(point: tuple[float, float] | None, regions: Sequence[Mapping[str, object]]) -> str | None:
    """Return the configured seat ID containing ``point``; never invent an ID."""
    if point is None:
        return None
    x, y = point
    for region in regions:
        try:
            seat_id = str(region["seat_id"])
            left, top, right, bottom = (float(region[name]) for name in ("left", "top", "right", "bottom"))
        except (KeyError, TypeError, ValueError):
            continue
        if left <= x <= right and top <= y <= bottom:
            return seat_id
    return None

