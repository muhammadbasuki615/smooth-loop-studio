"""AI denoising. Falls back to ffmpeg hqdn3d."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.ffmpeg_utils import FFmpeg


class Denoiser:
    def __init__(self, ffmpeg: Optional[FFmpeg] = None) -> None:
        self.ffmpeg = ffmpeg or FFmpeg()

    def denoise(self, input_path: str | Path, output_path: str | Path, strength: float = 1.0) -> Path:
        input_path = Path(input_path)
        output_path = Path(output_path)
        s = max(0.1, strength)
        cmd = [
            self.ffmpeg.binary, "-y", "-i", str(input_path),
            "-vf", f"hqdn3d={s*4:.1f}:{s*3:.1f}:{s*6:.1f}:{s*4:.1f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-an", str(output_path),
        ]
        self.ffmpeg.run(cmd, capture=True)
        return output_path
