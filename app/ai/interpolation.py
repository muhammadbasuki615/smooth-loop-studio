"""AI frame interpolation.

Currently uses ffmpeg ``minterpolate`` as a robust fallback. Hooks are in
place to swap in RIFE / FILM ONNX models when available in ``app/ai/models``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.ffmpeg_utils import FFmpeg


class FrameInterpolator:
    def __init__(self, ffmpeg: Optional[FFmpeg] = None, model_path: Optional[Path] = None) -> None:
        self.ffmpeg = ffmpeg or FFmpeg()
        self.model_path = Path(model_path) if model_path else None

    def is_ai_available(self) -> bool:
        if self.model_path is None or not self.model_path.exists():
            return False
        try:
            import onnxruntime  # noqa: F401
        except Exception:
            return False
        return True

    def interpolate(self, input_path: str | Path, output_path: str | Path, target_fps: int = 60) -> Path:
        """Interpolate frames to reach target_fps."""
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Use minterpolate as a strong CPU fallback. If an AI model is available we'd
        # call it here (left as extension point).
        cmd = [
            self.ffmpeg.binary, "-y", "-i", str(input_path),
            "-vf", f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:vsbmf=1",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-an", str(output_path),
        ]
        self.ffmpeg.run(cmd, capture=True)
        return output_path
