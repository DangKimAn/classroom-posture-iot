"""Geometry helpers for posture estimation. All returned angles are degrees."""

from __future__ import annotations

from math import atan2, degrees, isfinite
from typing import Mapping, Sequence

Point = tuple[float, float]


def _as_point(value: Sequence[float] | None) -> Point | None:
    if value is None or len(value) < 2:
        return None
    try:
        point = (float(value[0]), float(value[1]))
    except (TypeError, ValueError):
        return None
    return point if all(isfinite(component) for component in point) else None


def midpoint(first: Sequence[float] | None, second: Sequence[float] | None) -> Point | None:
    """Return the midpoint of two 2D points, or ``None`` for invalid input."""
    first_point, second_point = _as_point(first), _as_point(second)
    if first_point is None or second_point is None:
        return None
    return ((first_point[0] + second_point[0]) / 2, (first_point[1] + second_point[1]) / 2)


def calculate_angle_vertical(top_point: Sequence[float] | None, bottom_point: Sequence[float] | None) -> float | None:
    """Return the unsigned angle between a segment and image vertical, in degrees."""
    top, bottom = _as_point(top_point), _as_point(bottom_point)
    if top is None or bottom is None:
        return None
    dx, dy = bottom[0] - top[0], bottom[1] - top[1]
    if dx == 0 and dy == 0:
        return None
    return degrees(atan2(abs(dx), abs(dy)))


def trunk_angle_from_keypoints(keypoints: Mapping[str, Sequence[float] | None]) -> float | None:
    """Compute trunk angle from shoulder and hip midpoints when all points exist."""
    shoulders = midpoint(keypoints.get("left_shoulder"), keypoints.get("right_shoulder"))
    hips = midpoint(keypoints.get("left_hip"), keypoints.get("right_hip"))
    return calculate_angle_vertical(shoulders, hips)

