"""Latest-frame OpenCV capture with reconnect support."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

LOGGER = logging.getLogger(__name__)


class VideoCaptureStream:
    """Read a stream or file without making camera I/O part of classification logic."""

    def __init__(
        self,
        source: str | None = None,
        reconnect_delay_seconds: float = 0.5,
        open_timeout_ms: int = 3000,
        read_timeout_ms: int = 3000,
    ) -> None:
        self.source = source or os.getenv("VIDEO_FILE") or os.getenv("CAM_STREAM_URL")
        if not self.source:
            raise ValueError("Set CAM_STREAM_URL or VIDEO_FILE")
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.open_timeout_ms = open_timeout_ms
        self.read_timeout_ms = read_timeout_ms
        self._capture: Any | None = None

    def _connect(self) -> bool:
        try:
            import cv2
        except ImportError as error:
            raise RuntimeError("opencv-python is required for capture") from error
        self.close()
        params = []
        if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
            params.extend((cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.open_timeout_ms))
        if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
            params.extend((cv2.CAP_PROP_READ_TIMEOUT_MSEC, self.read_timeout_ms))
        try:
            if params:
                self._capture = cv2.VideoCapture(self.source, cv2.CAP_ANY, params)
            else:
                self._capture = cv2.VideoCapture(self.source)
        except (TypeError, cv2.error):
            # Some OpenCV builds expose timeout properties but not constructor params.
            self._capture = cv2.VideoCapture(self.source)
        if self._capture.isOpened():
            LOGGER.info("Connected to video source")
            return True
        LOGGER.warning("Unable to connect to video source; retrying")
        self.close()
        return False

    def connect(self) -> bool:
        """Open the configured source and report whether it is reachable."""
        return self._connect()

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

