"""USB cameras (Ender webcam now, overhead/wrist cams in Phase 5)."""
from __future__ import annotations

import threading

import numpy as np

from ..printers.base import PrinterError


def encode_jpeg(img: np.ndarray, quality: int = 85) -> bytes:
    import cv2

    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise PrinterError("could not encode JPEG")
    return buf.tobytes()


def decode_jpeg(data: bytes) -> np.ndarray:
    import cv2

    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise PrinterError("could not decode image")
    return img


class UsbCamera:
    """Opens the device per snapshot so a crashed handle can't wedge the farm."""

    def __init__(self, index: int, warmup_frames: int = 5):
        self.index = index
        self.warmup = warmup_frames
        self._lock = threading.Lock()

    def snapshot(self) -> bytes:
        import cv2

        with self._lock:
            # CAP_DSHOW = DirectShow, the fast-opening Windows camera backend.
            backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY
            cap = cv2.VideoCapture(self.index, backend)
            try:
                if not cap.isOpened():
                    raise PrinterError(f"camera {self.index} not found")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                frame = None
                for _ in range(self.warmup):  # let auto-exposure settle
                    ok, frame = cap.read()
                if frame is None:
                    raise PrinterError(f"camera {self.index} gave no frame")
                return encode_jpeg(frame)
            finally:
                cap.release()
