"""Performance monitoring utilities."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from .logger import get_logger

logger = get_logger(__name__)

try:
    import psutil
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False

try:
    import GPUtil  # type: ignore
    _HAS_GPUTIL = True
except Exception:
    _HAS_GPUTIL = False


@dataclass
class PerfSnapshot:
    cpu_percent: float
    ram_percent: float
    ram_used_mb: float
    ram_total_mb: float
    gpu_percent: float
    gpu_mem_percent: float
    gpu_name: str
    fps: float


class PerformanceMonitor:
    def __init__(self) -> None:
        self._last_t = time.time()
        self._frame_count = 0
        self._fps = 0.0

    def tick_frame(self) -> None:
        """Call once per rendered/preview frame."""
        self._frame_count += 1
        now = time.time()
        dt = now - self._last_t
        if dt >= 0.5:
            self._fps = self._frame_count / dt
            self._frame_count = 0
            self._last_t = now

    def fps(self) -> float:
        return self._fps

    def snapshot(self) -> PerfSnapshot:
        cpu = ram = ram_used = ram_total = 0.0
        if _HAS_PSUTIL:
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                ram = mem.percent
                ram_used = mem.used / 1024 / 1024
                ram_total = mem.total / 1024 / 1024
            except Exception:
                pass

        gpu_percent = gpu_mem = 0.0
        gpu_name = ""
        if _HAS_GPUTIL:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    g = gpus[0]
                    gpu_percent = float(g.load) * 100.0
                    gpu_mem = float(g.memoryUtil) * 100.0
                    gpu_name = g.name
            except Exception:
                pass

        return PerfSnapshot(
            cpu_percent=cpu,
            ram_percent=ram,
            ram_used_mb=ram_used,
            ram_total_mb=ram_total,
            gpu_percent=gpu_percent,
            gpu_mem_percent=gpu_mem,
            gpu_name=gpu_name,
            fps=self._fps,
        )

    @staticmethod
    def cpu_count() -> int:
        try:
            return os.cpu_count() or 1
        except Exception:
            return 1
