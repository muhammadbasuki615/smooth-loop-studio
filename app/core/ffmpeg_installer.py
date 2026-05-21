"""Auto-installer for FFmpeg.

Downloads a portable build into ``app/ffmpeg/bin`` if the system has no
ffmpeg available. Supports Windows (gyan.dev build) and Linux (johnvansickle
static build). macOS users are expected to install via Homebrew.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .logger import get_logger

logger = get_logger(__name__)


WIN_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
LINUX_URL = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
MAC_HINT = (
    "On macOS, install via: brew install ffmpeg  (or download a build from https://evermeet.cx/ffmpeg/)"
)


@dataclass
class InstallProgress:
    stage: str
    percent: float
    message: str = ""


ProgressCallback = Callable[[InstallProgress], None]


class FFmpegInstaller:
    def __init__(
        self,
        install_dir: Path | str,
        progress: Optional[ProgressCallback] = None,
    ) -> None:
        self.install_dir = Path(install_dir)
        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir = self.install_dir / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.progress = progress or (lambda p: None)

    # ---------------- public ----------------

    def is_installed(self) -> bool:
        return self._candidate_binary().exists() or bool(shutil.which("ffmpeg"))

    def installed_path(self) -> Optional[Path]:
        cand = self._candidate_binary()
        if cand.exists():
            return cand
        sysp = shutil.which("ffmpeg")
        return Path(sysp) if sysp else None

    def install(self, force: bool = False) -> Path:
        """Download and install ffmpeg if not present. Returns binary path."""
        if not force and self.is_installed():
            self._emit("done", 100, "ffmpeg already installed")
            return self.installed_path()  # type: ignore[return-value]

        system = platform.system().lower()
        if system == "windows":
            return self._install_windows()
        if system == "linux":
            return self._install_linux()
        if system == "darwin":
            self._emit("error", 0, MAC_HINT)
            raise RuntimeError(MAC_HINT)
        raise RuntimeError(f"Unsupported platform: {system}")

    # ---------------- internals ----------------

    def _candidate_binary(self) -> Path:
        return self.bin_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")

    def _emit(self, stage: str, percent: float, message: str = "") -> None:
        try:
            self.progress(InstallProgress(stage=stage, percent=percent, message=message))
        except Exception:
            pass

    def _download(self, url: str, dest: Path) -> None:
        import requests
        self._emit("download", 0, f"Downloading {url}")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 256
            with dest.open("wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = min(99.0, downloaded * 100 / total)
                        self._emit("download", pct, f"{downloaded/1e6:.1f} / {total/1e6:.1f} MB")
        self._emit("download", 100, "Download complete")

    def _install_windows(self) -> Path:
        archive = self.install_dir / "ffmpeg-win.zip"
        self._download(WIN_URL, archive)
        self._emit("extract", 0, "Extracting...")
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(self.install_dir)
        # Find the extracted bin/ folder and copy binaries
        for child in self.install_dir.iterdir():
            if child.is_dir() and child.name.startswith("ffmpeg"):
                src_bin = child / "bin"
                if src_bin.exists():
                    for exe in src_bin.iterdir():
                        shutil.copy2(exe, self.bin_dir / exe.name)
                    break
        archive.unlink(missing_ok=True)
        self._emit("done", 100, "FFmpeg installed")
        return self._candidate_binary()

    def _install_linux(self) -> Path:
        archive = self.install_dir / "ffmpeg-linux.tar.xz"
        self._download(LINUX_URL, archive)
        self._emit("extract", 0, "Extracting...")
        with tarfile.open(archive, "r:xz") as tf:
            tf.extractall(self.install_dir)
        for child in self.install_dir.iterdir():
            if child.is_dir() and child.name.startswith("ffmpeg"):
                for exe_name in ("ffmpeg", "ffprobe", "qt-faststart"):
                    src = child / exe_name
                    if src.exists():
                        dest = self.bin_dir / exe_name
                        shutil.copy2(src, dest)
                        dest.chmod(0o755)
                break
        archive.unlink(missing_ok=True)
        self._emit("done", 100, "FFmpeg installed")
        return self._candidate_binary()
