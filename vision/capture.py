"""Latest-frame OpenCV capture with reconnect support."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

LOGGER = logging.getLogger(__name__)


class VideoCaptureStream:
    """Read a stream or file without making camera I/O part of classification logic."""

    def __init__(self, source: str | None = None, reconnect_delay_seconds: float = 0.5) -> None:
        self.source = source or os.getenv("VIDEO_FILE") or os.getenv("CAM_STREAM_URL")
        if not self.source:
            raise ValueError("Set CAM_STREAM_URL or VIDEO_FILE")
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self._capture: Any | None = None

    def _connect(self) -> bool:
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError("opencv-python is required for capture") from error
        self.close()
        self._capture = cv2.VideoCapture(self.source)
        if self._capture.isOpened():
            LOGGER.info("Connected to video source")
            return True
        LOGGER.warning("Unable to connect to video source; retrying")
        self.close()
        return False

    def read(self) -> Any | None:
        """Return a new frame, reconnecting after a failed read."""
        if self._capture is None and not self._connect():
            time.sleep(self.reconnect_delay_seconds)
            return None
        success, frame = self._capture.read()
        if success:
            return frame
        LOGGER.warning("Video read failed; reconnecting")
        if self._connect():
            success, frame = self._capture.read()
            if success:
                return frame
        time.sleep(self.reconnect_delay_seconds)
        return None

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

