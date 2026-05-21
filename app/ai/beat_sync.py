"""Beat detection / sync helpers using librosa."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


class BeatSync:
    def detect_beats(self, audio_path: str | Path) -> Tuple[float, List[float]]:
        """Return (tempo_bpm, beat_times_seconds)."""
        try:
            import librosa  # type: ignore
            import numpy as np
        except Exception:
            return 0.0, []
        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr).tolist()
        return float(tempo), beat_times

    def quantize_to_beat(self, seconds: float, beats: List[float]) -> float:
        """Snap a time value to the nearest beat."""
        if not beats:
            return seconds
        return min(beats, key=lambda b: abs(b - seconds))
