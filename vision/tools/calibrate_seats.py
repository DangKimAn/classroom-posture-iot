"""Draw anonymous seat regions from one camera frame or a still image."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def regions_yaml(regions: list[dict[str, object]]) -> str:
    """Serialize regions using the exact keys consumed by vision.main."""
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError("PyYAML is required; install vision/requirements.txt") from error
    return yaml.safe_dump({"seat_regions": regions}, sort_keys=False, allow_unicode=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, help="Use a local still image instead of a camera stream")
    parser.add_argument("--output", type=Path, help="Write YAML here; by default print it to stdout")
    args = parser.parse_args()

    try:
        import cv2
    except ImportError as error:
        raise SystemExit("OpenCV is required; install vision/requirements.txt") from error

    source: str | int = str(args.image) if args.image else (os.getenv("CAM_STREAM_URL") or os.getenv("VIDEO_FILE") or "")
    if not source:
        raise SystemExit("Set CAM_STREAM_URL or VIDEO_FILE, or pass --image PATH")
    frame = cv2.imread(source) if args.image else None
    if frame is None:
        capture = cv2.VideoCapture(source)
        try:
            ok, frame = capture.read()
        finally:
            capture.release()
        if not ok or frame is None:
            raise SystemExit("Could not read a frame from the selected source")

    regions: list[dict[str, object]] = []
    start: tuple[int, int] | None = None
    cursor: tuple[int, int] | None = None
    drawing = False

    def on_mouse(event, x, y, _flags, _param):
        nonlocal start, cursor, drawing
        if event == cv2.EVENT_LBUTTONDOWN:
            start = cursor = (x, y)
            drawing = True
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            cursor = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and drawing:
            cursor = (x, y)
            drawing = False

    window = "Seat calibration | drag rectangle, u undo, c clear, s save, q quit"
    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_mouse)
    while True:
        display = frame.copy()
        for region in regions:
            cv2.rectangle(display, (region["left"], region["top"]),
                          (region["right"], region["bottom"]), (0, 200, 0), 2)
            cv2.putText(display, str(region["seat_id"]), (region["left"], max(20, region["top"] - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
        if start and cursor:
            cv2.rectangle(display, start, cursor, (0, 180, 255), 2)
        cv2.imshow(window, display)
        key = cv2.waitKey(20) & 0xFF
        if not drawing and start and cursor:
            left, right = sorted((start[0], cursor[0]))
            top, bottom = sorted((start[1], cursor[1]))
            start = cursor = None
            if left < right and top < bottom:
                seat_id = input("Anonymous seat_id for rectangle (blank cancels): ").strip()
                if seat_id:
                    regions.append({"seat_id": seat_id, "left": left, "top": top,
                                    "right": right, "bottom": bottom})
        if key == ord("u") and regions:
            regions.pop()
        elif key == ord("c"):
            regions.clear()
        elif key in (ord("s"), ord("q")):
            if regions:
                output = regions_yaml(regions)
                if args.output:
                    args.output.write_text(output, encoding="utf-8")
                    print(f"Wrote {len(regions)} seat region(s) to {args.output}")
                else:
                    print(output, end="")
            elif key == ord("s"):
                print("No seat regions selected; nothing saved")
            if key == ord("s"):
                break
            if key == ord("q"):
                break
    cv2.destroyWindow(window)


if __name__ == "__main__":
    main()
