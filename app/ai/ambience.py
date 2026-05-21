"""Ambient overlay / sound generation helpers.

Procedural generators (rain, snow, particles) use ffmpeg sources. Real AI
generation would require generative models; we provide quality procedural
fallbacks here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.ffmpeg_utils import FFmpeg


class AmbienceGenerator:
    def __init__(self, ffmpeg: Optional[FFmpeg] = None) -> None:
        self.ffmpeg = ffmpeg or FFmpeg()

    def generate_rain_overlay(
        self,
        output_path: str | Path,
        width: int = 1920,
        height: int = 1080,
        duration: float = 10.0,
    ) -> Path:
        """Procedural rain overlay (white streaks on transparent-like)."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.ffmpeg.binary, "-y",
            "-f", "lavfi", "-i",
            f"nullsrc=s={width}x{height}:d={duration}:r=30,format=rgba,"
            f"geq=r=0:g=0:b=0:a='if(lt(random(1),0.002),255,0)',"
            f"motion=4:0:0:0:0:0",
            "-c:v", "qtrle",
            str(out),
        ]
        try:
            self.ffmpeg.run(cmd, capture=True)
        except Exception:
            # Simpler fallback: just noise
            cmd2 = [
                self.ffmpeg.binary, "-y",
                "-f", "lavfi", "-i", f"color=black:s={width}x{height}:r=30:d={duration}",
                "-vf", "noise=alls=80:allf=t+u,format=gray",
                str(out),
            ]
            self.ffmpeg.run(cmd2, capture=True)
        return out

    def generate_snow_overlay(
        self,
        output_path: str | Path,
        width: int = 1920,
        height: int = 1080,
        duration: float = 10.0,
    ) -> Path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.ffmpeg.binary, "-y",
            "-f", "lavfi", "-i",
            f"color=black:s={width}x{height}:r=30:d={duration}",
            "-vf", "noise=alls=40:allf=t,format=gray",
            str(out),
        ]
        self.ffmpeg.run(cmd, capture=True)
        return out
