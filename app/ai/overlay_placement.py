"""Smart overlay placement: estimate optimal text/watermark positions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass
class PlacementSuggestion:
    x: str  # ffmpeg expression
    y: str
    reason: str


class SmartOverlayPlacer:
    """Suggest a corner that's likely to contain low motion/visual entropy."""

    def suggest(self, video_path: str | Path, margin: int = 32) -> PlacementSuggestion:
        try:
            import cv2  # type: ignore
            import numpy as np
        except Exception:
            return PlacementSuggestion("W-w-32", "H-h-32", "default bottom-right")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return PlacementSuggestion("W-w-32", "H-h-32", "default bottom-right")
        try:
            corners_score = {"tl": 0.0, "tr": 0.0, "bl": 0.0, "br": 0.0}
            n = 0
            while n < 30:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                h, w = frame.shape[:2]
                qw, qh = w // 4, h // 4
                tl = frame[0:qh, 0:qw]
                tr = frame[0:qh, w - qw:w]
                bl = frame[h - qh:h, 0:qw]
                br = frame[h - qh:h, w - qw:w]
                for key, region in (("tl", tl), ("tr", tr), ("bl", bl), ("br", br)):
                    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
                    corners_score[key] += float(np.std(gray))
                n += 1
            best = min(corners_score.items(), key=lambda kv: kv[1])[0]
        finally:
            cap.release()

        m = margin
        if best == "tl":
            return PlacementSuggestion(f"{m}", f"{m}", "lowest-entropy: top-left")
        if best == "tr":
            return PlacementSuggestion(f"W-w-{m}", f"{m}", "lowest-entropy: top-right")
        if best == "bl":
            return PlacementSuggestion(f"{m}", f"H-h-{m}", "lowest-entropy: bottom-left")
        return PlacementSuggestion(f"W-w-{m}", f"H-h-{m}", "lowest-entropy: bottom-right")
