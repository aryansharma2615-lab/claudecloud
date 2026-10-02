"""'Is the bed clear?' — compare the bed region against a photo of the empty bed.

Method from OctoPrint-BedReady / Bambuddy: grayscale, blur, absolute difference in a
fixed region of interest (ROI), score = share of pixels that changed a lot.
Fails closed: no reference photo → not clear.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .cameras import decode_jpeg

DEFAULT_THRESHOLD = 0.02  # >2 % of ROI pixels changed → something is on the bed
PIXEL_DELTA = 40          # grey levels (0-255) that count as "changed"


@dataclass
class BedCheck:
    clear: bool
    score: float | None
    reason: str


def _prep(img: np.ndarray, roi: tuple[int, int, int, int] | None) -> np.ndarray:
    import cv2

    if roi:
        x, y, w, h = roi
        img = img[y:y + h, x:x + w]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (9, 9), 0)


def compare(current: np.ndarray, reference: np.ndarray,
            roi: tuple[int, int, int, int] | None = None,
            threshold: float = DEFAULT_THRESHOLD) -> BedCheck:
    import cv2

    if current.shape != reference.shape:
        return BedCheck(False, None, "camera resolution changed: recapture the reference")
    a, b = _prep(current, roi), _prep(reference, roi)
    changed = float(np.mean(cv2.absdiff(a, b) > PIXEL_DELTA))
    if changed > threshold:
        return BedCheck(False, changed, f"{changed:.1%} of the bed differs from the empty reference")
    return BedCheck(True, changed, f"bed matches empty reference ({changed:.1%} changed)")


def check(printer: str, snapshot_jpeg: bytes, vision_dir: Path) -> BedCheck:
    ref_path = vision_dir / f"{printer}_empty.jpg"
    if not ref_path.exists():
        return BedCheck(False, None, f"no empty-bed reference for {printer}: "
                                     f"run `python -m farm.cli capture-reference {printer}`")
    roi = None
    roi_path = vision_dir / f"{printer}_roi.json"
    if roi_path.exists():
        r = json.loads(roi_path.read_text())
        roi = (int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"]))
    return compare(decode_jpeg(snapshot_jpeg), decode_jpeg(ref_path.read_bytes()), roi)
