"""AI color enhancement. Falls back to auto-levels via ffmpeg."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.ffmpeg_utils import FFmpeg


class ColorEnhancer:
    def __init__(self, ffmpeg: Optional[FFmpeg] = None) -> None:
        self.ffmpeg = ffmpeg or FFmpeg()

    def enhance(self, input_path: str | Path, output_path: str | Path) -> Path:
        cmd = [
            self.ffmpeg.binary, "-y", "-i", str(input_path),
            "-vf", "eq=contrast=1.08:saturation=1.15:gamma=1.02,curves=preset=lighter",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-an", str(output_path),
        ]
        self.ffmpeg.run(cmd, capture=True)
        return Path(output_path)
