"""Scene detection using OpenCV histogram diffs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Scene:
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float


class SceneDetector:
    def __init__(self, threshold: float = 0.4) -> None:
        self.threshold = threshold

    def detect(self, input_path: str | Path) -> List[Scene]:
        try:
            import cv2  # type: ignore
            import numpy as np
        except Exception:
            return []
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            return []
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        scenes: List[Scene] = []
        prev_hist = None
        scene_start = 0
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            small = cv2.resize(frame, (160, 90))
            hist = cv2.calcHist([small], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            cv2.normalize(hist, hist)
            if prev_hist is not None:
                diff = 1.0 - float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL))
                if diff > self.threshold:
                    scenes.append(
                        Scene(
                            start_frame=scene_start,
                            end_frame=idx - 1,
                            start_time=scene_start / fps,
                            end_time=(idx - 1) / fps,
                        )
                    )
                    scene_start = idx
            prev_hist = hist
            idx += 1
        if scene_start < idx:
            scenes.append(
                Scene(start_frame=scene_start, end_frame=idx - 1, start_time=scene_start / fps, end_time=(idx - 1) / fps)
            )
        cap.release()
        return scenes
