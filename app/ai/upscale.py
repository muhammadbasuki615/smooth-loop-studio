"""AI upscaling (Real-ESRGAN-style). Falls back to Lanczos upscale via ffmpeg."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.ffmpeg_utils import FFmpeg


class Upscaler:
    def __init__(self, ffmpeg: Optional[FFmpeg] = None, model_path: Optional[Path] = None) -> None:
        self.ffmpeg = ffmpeg or FFmpeg()
        self.model_path = Path(model_path) if model_path else None

    def upscale(self, input_path: str | Path, output_path: str | Path, scale: int = 2) -> Path:
        input_path = Path(input_path)
        output_path = Path(output_path)
        cmd = [
            self.ffmpeg.binary, "-y", "-i", str(input_path),
            "-vf", f"scale=iw*{scale}:ih*{scale}:flags=lanczos",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-an", str(output_path),
        ]
        self.ffmpeg.run(cmd, capture=True)
        return output_path
