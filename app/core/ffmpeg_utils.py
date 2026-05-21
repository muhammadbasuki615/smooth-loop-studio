"""FFmpeg wrapper utilities and GPU detection."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from .logger import get_logger

logger = get_logger(__name__)


class FFmpegError(RuntimeError):
    """Raised when ffmpeg command fails."""


@dataclass
class GPUInfo:
    has_nvidia: bool = False
    has_amd: bool = False
    has_intel: bool = False
    available_encoders: list[str] = field(default_factory=list)

    @property
    def has_any_gpu(self) -> bool:
        return self.has_nvidia or self.has_amd or self.has_intel

    def best_encoder(self, codec: str = "h264") -> str:
        """Return best available encoder string for a logical codec name."""
        codec = codec.lower()
        candidates: list[str] = []
        if codec in ("h264", "avc"):
            if self.has_nvidia:
                candidates.append("h264_nvenc")
            if self.has_intel:
                candidates.append("h264_qsv")
            if self.has_amd:
                candidates.append("h264_amf")
            candidates.append("libx264")
        elif codec in ("h265", "hevc"):
            if self.has_nvidia:
                candidates.append("hevc_nvenc")
            if self.has_intel:
                candidates.append("hevc_qsv")
            if self.has_amd:
                candidates.append("hevc_amf")
            candidates.append("libx265")
        elif codec == "av1":
            if self.has_nvidia:
                candidates.append("av1_nvenc")
            if self.has_intel:
                candidates.append("av1_qsv")
            candidates.append("libaom-av1")
            candidates.append("libsvtav1")
        elif codec == "vp9":
            candidates.append("libvpx-vp9")
        else:
            candidates.append("libx264")
        for c in candidates:
            if c in self.available_encoders:
                return c
        return candidates[-1]


class FFmpeg:
    """Wrapper around ffmpeg/ffprobe binaries."""

    def __init__(
        self,
        binary: str | None = None,
        probe_binary: str | None = None,
        local_bin_dir: Path | None = None,
    ) -> None:
        self.local_bin_dir = local_bin_dir
        self.binary = binary or self._discover("ffmpeg")
        self.probe_binary = probe_binary or self._discover("ffprobe")

    # ---------------- discovery ----------------

    def _discover(self, name: str) -> str:
        exe = name + (".exe" if os.name == "nt" else "")
        # Local bundled ffmpeg first
        if self.local_bin_dir:
            candidate = Path(self.local_bin_dir) / exe
            if candidate.exists():
                return str(candidate)
        # System PATH
        found = shutil.which(name) or shutil.which(exe)
        if found:
            return found
        # Last resort: imageio-ffmpeg
        if name == "ffmpeg":
            try:
                import imageio_ffmpeg
                return imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                pass
        return name  # may still fail later

    def is_available(self) -> bool:
        try:
            self.run([self.binary, "-version"], capture=True, check=True)
            return True
        except Exception:
            return False

    # ---------------- generic runner ----------------

    def run(
        self,
        cmd: Sequence[str],
        capture: bool = False,
        check: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess:
        logger.debug("Running: %s", " ".join(cmd))
        try:
            cp = subprocess.run(
                list(cmd),
                check=False,
                capture_output=capture,
                text=capture,
                timeout=timeout,
            )
        except FileNotFoundError as e:
            raise FFmpegError(f"FFmpeg binary not found: {e}") from e
        if check and cp.returncode != 0:
            stderr = cp.stderr if capture else ""
            raise FFmpegError(
                f"FFmpeg failed (exit {cp.returncode}): {' '.join(cmd[:6])}... :: {stderr[-2000:] if stderr else ''}"
            )
        return cp

    # ---------------- inspection ----------------

    def list_encoders(self) -> list[str]:
        try:
            cp = self.run([self.binary, "-hide_banner", "-encoders"], capture=True)
        except FFmpegError:
            return []
        encs: list[str] = []
        for line in (cp.stdout or "").splitlines():
            m = re.match(r"^\s*[VAS][\.A-Z]+\s+([A-Za-z0-9_\-]+)", line)
            if m:
                encs.append(m.group(1))
        return encs

    def probe(self, path: str | Path) -> dict:
        cmd = [
            self.probe_binary,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        cp = self.run(cmd, capture=True)
        try:
            return json.loads(cp.stdout)
        except Exception as e:
            raise FFmpegError(f"Failed to parse ffprobe output: {e}") from e

    def duration_seconds(self, path: str | Path) -> float:
        meta = self.probe(path)
        try:
            return float(meta.get("format", {}).get("duration", 0.0))
        except Exception:
            return 0.0

    def video_streams(self, path: str | Path) -> list[dict]:
        meta = self.probe(path)
        return [s for s in meta.get("streams", []) if s.get("codec_type") == "video"]

    def audio_streams(self, path: str | Path) -> list[dict]:
        meta = self.probe(path)
        return [s for s in meta.get("streams", []) if s.get("codec_type") == "audio"]


def detect_gpu(ffmpeg: FFmpeg | None = None) -> GPUInfo:
    """Detect available GPU encoders via ffmpeg -encoders."""
    ff = ffmpeg or FFmpeg()
    encoders = ff.list_encoders()
    info = GPUInfo(available_encoders=encoders)
    info.has_nvidia = any(e.endswith("_nvenc") for e in encoders)
    info.has_intel = any(e.endswith("_qsv") for e in encoders)
    info.has_amd = any(e.endswith("_amf") for e in encoders)
    logger.info(
        f"GPU encoders: NVENC={info.has_nvidia} QSV={info.has_intel} AMF={info.has_amd}"
    )
    return info


def build_filter_chain(parts: Iterable[str]) -> str:
    """Combine non-empty filter parts with commas."""
    return ",".join(p for p in parts if p)
