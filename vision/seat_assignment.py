"""Map an anonymous body reference point to configured seat regions."""

from __future__ import annotations

from dataclasses import dataclass
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


def intersection_area(
    bbox: Sequence[float] | None, region: Mapping[str, object]
) -> float:
    """Return the pixel area shared by a pose bbox and a seat region."""
    if bbox is None or len(bbox) < 4:
        return 0.0
    try:
        x1, y1, x2, y2 = (float(value) for value in bbox[:4])
        left, top, right, bottom = (
            float(region[name]) for name in ("left", "top", "right", "bottom")
        )
    except (KeyError, TypeError, ValueError):
        return 0.0
    return max(0.0, min(x2, right) - max(x1, left)) * max(
        0.0, min(y2, bottom) - max(y1, top)
    )


@dataclass(frozen=True)
class SeatConflict:
    seat_id: str
    dropped_poses: int


def assign_poses_to_seats(
    poses: Sequence[object], regions: Sequence[Mapping[str, object]]
) -> tuple[dict[int, str], list[SeatConflict]]:
    """Assign each pose to at most one seat and keep one pose per seat.

    Pose objects provide ``keypoints``, ``confidence``, and optional ``bbox``.
    The existing hip/shoulder reference point determines region membership.
    """
    candidates: dict[str, list[tuple[int, object, Mapping[str, object]]]] = {}
    for pose_index, pose in enumerate(poses):
        point = reference_point(getattr(pose, "keypoints", {}))
        matching_regions = []
        for region in regions:
            seat_id = assign_seat(point, [region])
            if seat_id is not None:
                matching_regions.append((region, seat_id))
        if not matching_regions:
            continue
        # A reference point must be inside; among overlapping regions choose
        # the one with the greatest pose-box intersection, then seat ID.
        region, seat_id = min(
            matching_regions,
            key=lambda item: (-intersection_area(getattr(pose, "bbox", None), item[0]), item[1]),
        )
        candidates.setdefault(seat_id, []).append((pose_index, pose, region))

    assignments: dict[int, str] = {}
    conflicts: list[SeatConflict] = []
    for seat_id, seat_candidates in candidates.items():
        ranked = sorted(
            seat_candidates,
            key=lambda item: (
                -float(getattr(item[1], "confidence", 0.0)),
                -intersection_area(getattr(item[1], "bbox", None), item[2]),
                item[0],  # Stable tie break: keep the first detector result.
            ),
        )
        assignments[ranked[0][0]] = seat_id
        if len(ranked) > 1:
            conflicts.append(SeatConflict(seat_id, len(ranked) - 1))
    return assignments, conflicts

