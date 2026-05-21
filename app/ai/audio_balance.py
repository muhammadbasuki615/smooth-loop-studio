"""Automatic loudness balancing using librosa peak estimation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class AudioBalancer:
    def estimate_gain_db(self, audio_path: str | Path, target_db: float = -16.0) -> float:
        """Estimate gain (in dB) needed to bring file to target loudness."""
        try:
            import librosa  # type: ignore
            import numpy as np
        except Exception:
            return 0.0
        y, sr = librosa.load(str(audio_path), sr=None, mono=True)
        rms = float(np.sqrt(np.mean(y ** 2)))
        if rms <= 1e-9:
            return 0.0
        current_db = 20.0 * float(np.log10(rms))
        return target_db - current_db
