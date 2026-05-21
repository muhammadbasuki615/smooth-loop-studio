"""Seamless video loop engine.

This module builds FFmpeg filtergraphs that turn a short clip into a long,
seamless loop with a variety of blending modes:

* ``simple``      - back-to-back concat (no blending).
* ``crossfade``   - linear xfade between end and beginning.
* ``ping_pong``   - forward + reverse + forward... etc.
* ``reverse``     - play forward then reverse, repeat.
* ``freeze_smooth`` - smooths last/first frame discontinuities.
* ``optical_flow``  - per-frame minterpolate blending (heavy, smoothest).
* ``ai_smooth``     - hook for AI interpolation model (falls back to optical_flow).

The engine produces an intermediate "seamless unit" clip that is then looped to
fill the target duration via the export pipeline. This keeps render-time low
while still allowing hours-long output.
"""

from __future__ import annotations

import enum
import math
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence

from .ffmpeg_utils import FFmpeg, FFmpegError, build_filter_chain
from .logger import get_logger

logger = get_logger(__name__)


class LoopMode(str, enum.Enum):
    SIMPLE = "simple"
    CROSSFADE = "crossfade"
    PING_PONG = "ping_pong"
    REVERSE = "reverse"
    FREEZE_SMOOTH = "freeze_smooth"
    OPTICAL_FLOW = "optical_flow"
    AI_SMOOTH = "ai_smooth"


@dataclass
class LoopOptions:
    mode: LoopMode = LoopMode.CROSSFADE
    transition_seconds: float = 1.5
    blend_intensity: float = 1.0  # 0..1
    motion_strength: float = 1.0  # for optical flow
    target_duration_seconds: float = 3600.0
    output_fps: Optional[int] = None
    output_size: Optional[tuple[int, int]] = None
    keep_intermediate: bool = False
    extra_filters: list[str] = field(default_factory=list)


@dataclass
class LoopResult:
    output_path: Path
    intermediate_path: Optional[Path] = None
    unit_duration: float = 0.0
    iterations: int = 0


class LoopEngine:
    """Build seamless loops with ffmpeg."""

    def __init__(self, ffmpeg: FFmpeg | None = None, temp_dir: Path | str = "temp") -> None:
        self.ffmpeg = ffmpeg or FFmpeg()
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    # ---------------- public API ----------------

    def build_seamless_unit(
        self,
        input_path: str | Path,
        options: LoopOptions,
        output_path: str | Path | None = None,
    ) -> Path:
        """Render one self-blending unit clip from the source.

        The unit's last frame matches its first frame so it can be re-looped
        cleanly any number of times.
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(input_path)

        src_duration = max(0.01, self.ffmpeg.duration_seconds(input_path))
        td = max(0.05, min(options.transition_seconds, max(0.05, src_duration / 2)))
        out = Path(output_path) if output_path else self.temp_dir / f"_unit_{input_path.stem}.mp4"

        if options.mode == LoopMode.SIMPLE:
            self._render_simple_unit(input_path, out, options)
        elif options.mode == LoopMode.CROSSFADE:
            self._render_crossfade_unit(input_path, out, options, src_duration, td)
        elif options.mode == LoopMode.PING_PONG:
            self._render_pingpong_unit(input_path, out, options)
        elif options.mode == LoopMode.REVERSE:
            self._render_reverse_unit(input_path, out, options)
        elif options.mode == LoopMode.FREEZE_SMOOTH:
            self._render_freeze_smooth_unit(input_path, out, options, src_duration, td)
        elif options.mode in (LoopMode.OPTICAL_FLOW, LoopMode.AI_SMOOTH):
            self._render_optical_flow_unit(input_path, out, options, src_duration, td)
        else:
            raise ValueError(f"Unknown loop mode: {options.mode}")

        return out

    def detect_natural_loop_point(self, input_path: str | Path) -> float:
        """Heuristic: scan for the best frame near the end that matches frame 0.

        Returns a duration (in seconds) of the trimmed input that produces the
        smoothest loop, using OpenCV when available. Falls back to the full
        clip duration.
        """
        input_path = Path(input_path)
        full = self.ffmpeg.duration_seconds(input_path)
        try:
            import cv2  # type: ignore
            import numpy as np
        except Exception:
            return full

        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            return full
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total <= 4:
                return full
            ok, first = cap.read()
            if not ok or first is None:
                return full
            first_small = cv2.resize(first, (64, 36))
            first_gray = cv2.cvtColor(first_small, cv2.COLOR_BGR2GRAY).astype(np.float32)

            best_idx = total - 1
            best_score = float("inf")
            # scan last 30% of clip
            scan_start = max(1, int(total * 0.7))
            for i in range(scan_start, total):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue
                small = cv2.resize(frame, (64, 36))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
                diff = float(np.mean((gray - first_gray) ** 2))
                if diff < best_score:
                    best_score = diff
                    best_idx = i
            return max(0.1, best_idx / fps)
        finally:
            cap.release()

    def compute_iterations(self, unit_duration: float, target_duration: float) -> int:
        if unit_duration <= 0:
            return 1
        return max(1, math.ceil(target_duration / unit_duration))

    # ---------------- mode renderers ----------------

    def _per_stream_filters(self, options: LoopOptions) -> list[str]:
        """Filters that are safe to apply on EACH stream before xfade.

        NOTE: ``fps`` MUST NOT be applied per-stream here because the
        combination of ``trim + setpts + fps`` confuses ffmpeg's frame
        timing and produces an over-long output. Apply ``fps`` at the
        end of the chain instead.
        """
        parts: list[str] = []
        if options.output_size:
            w, h = options.output_size
            parts.append(f"scale={w}:{h}:flags=lanczos")
        parts.extend(options.extra_filters)
        return parts

    def _post_xfade_filters(self, options: LoopOptions) -> list[str]:
        parts: list[str] = []
        if options.output_fps:
            parts.append(f"fps={options.output_fps}")
        return parts

    # Backward-compat shim
    def _common_filters(self, options: LoopOptions) -> list[str]:
        return self._per_stream_filters(options)

    def _render_simple_unit(self, src: Path, out: Path, opts: LoopOptions) -> None:
        vf_parts = self._per_stream_filters(opts) + self._post_xfade_filters(opts)
        vf = build_filter_chain(vf_parts)
        cmd = [self.ffmpeg.binary, "-y", "-i", str(src)]
        if vf:
            cmd += ["-vf", vf]
        cmd += [
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-an", str(out),
        ]
        self.ffmpeg.run(cmd, capture=True)

    def _render_crossfade_unit(
        self,
        src: Path,
        out: Path,
        opts: LoopOptions,
        duration: float,
        td: float,
    ) -> None:
        """Build a loop that crossfades the tail back into the head."""
        # Strategy: take the full clip then xfade-overlay the first `td`
        # seconds (taken from the start) on top of the last `td` seconds.
        # The resulting clip has duration ~ (clip_duration) but with a
        # smooth transition at the cut point.
        offset = max(0.0, duration - td)
        pre = build_filter_chain(self._per_stream_filters(opts))
        post = build_filter_chain(self._post_xfade_filters(opts))

        # Two inputs (same file): one full, one trimmed first td seconds
        filter_complex = (
            f"[0:v]split=2[a][b];"
            f"[a]{pre + ',' if pre else ''}setpts=PTS-STARTPTS[av];"
            f"[b]trim=0:{td:.4f},setpts=PTS-STARTPTS{',' + pre if pre else ''}[bv];"
            f"[av][bv]xfade=transition=fade:duration={td:.4f}:offset={offset:.4f}"
            + (f",{post}" if post else "")
            + "[v]"
        )
        cmd = [
            self.ffmpeg.binary, "-y",
            "-i", str(src),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-an", str(out),
        ]
        self.ffmpeg.run(cmd, capture=True)

    def _render_pingpong_unit(self, src: Path, out: Path, opts: LoopOptions) -> None:
        pre = build_filter_chain(self._per_stream_filters(opts))
        post = build_filter_chain(self._post_xfade_filters(opts))
        filter_complex = (
            f"[0:v]split=2[fwd][rev_in];"
            f"[rev_in]reverse[rev];"
            f"[fwd][rev]concat=n=2:v=1:a=0"
            + (f",{pre}" if pre else "")
            + (f",{post}" if post else "")
            + "[v]"
        )
        cmd = [
            self.ffmpeg.binary, "-y",
            "-i", str(src),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-an", str(out),
        ]
        self.ffmpeg.run(cmd, capture=True)

    def _render_reverse_unit(self, src: Path, out: Path, opts: LoopOptions) -> None:
        # Identical to ping-pong for unit, but kept distinct for clarity.
        self._render_pingpong_unit(src, out, opts)

    def _render_freeze_smooth_unit(
        self,
        src: Path,
        out: Path,
        opts: LoopOptions,
        duration: float,
        td: float,
    ) -> None:
        """Use tblend (frame blending) at the junction to smooth out a
        slightly-mismatched loop point."""
        offset = max(0.0, duration - td)
        pre = build_filter_chain(self._per_stream_filters(opts))
        post_extra = f",fps={opts.output_fps}" if opts.output_fps else ""
        filter_complex = (
            f"[0:v]split=2[a][b];"
            f"[a]{pre + ',' if pre else ''}setpts=PTS-STARTPTS[av];"
            f"[b]trim=0:{td:.4f},setpts=PTS-STARTPTS{',' + pre if pre else ''}[bv];"
            f"[av][bv]xfade=transition=dissolve:duration={td:.4f}:offset={offset:.4f},"
            f"tblend=all_mode=average{post_extra}[v]"
        )
        cmd = [
            self.ffmpeg.binary, "-y",
            "-i", str(src),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-an", str(out),
        ]
        self.ffmpeg.run(cmd, capture=True)

    def _render_optical_flow_unit(
        self,
        src: Path,
        out: Path,
        opts: LoopOptions,
        duration: float,
        td: float,
    ) -> None:
        """Use ffmpeg minterpolate for motion-compensated frame blending."""
        offset = max(0.0, duration - td)
        target_fps = opts.output_fps or 60
        pre = build_filter_chain(self._per_stream_filters(opts))
        filter_complex = (
            f"[0:v]split=2[a][b];"
            f"[a]{pre + ',' if pre else ''}setpts=PTS-STARTPTS[av];"
            f"[b]trim=0:{td:.4f},setpts=PTS-STARTPTS{',' + pre if pre else ''}[bv];"
            f"[av][bv]xfade=transition=fade:duration={td:.4f}:offset={offset:.4f},"
            f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:vsbmf=1[v]"
        )
        cmd = [
            self.ffmpeg.binary, "-y",
            "-i", str(src),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-an", str(out),
        ]
        try:
            self.ffmpeg.run(cmd, capture=True)
        except FFmpegError as e:
            logger.warning(f"Optical flow render failed, falling back to crossfade: {e}")
            self._render_crossfade_unit(src, out, opts, duration, td)

    # ---------------- long-form loop builder ----------------

    _PROGRESS_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

    def build_long_loop(
        self,
        unit_path: str | Path,
        target_duration_seconds: float,
        output_path: str | Path,
        loop_options: LoopOptions | None = None,
        on_progress: Optional[Callable[[float, float], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> LoopResult:
        """Loop the unit clip with ``-stream_loop`` to fill the target duration.

        Uses ``-c copy`` for instant looping without re-encoding. If the unit
        clip's codec/timing can't be safely concatenated with copy (rare), the
        caller can fall back via try/except - we attempt copy first.

        ``on_progress`` is called with ``(elapsed_seconds, target_duration)``
        as FFmpeg processes each chunk so the UI can show real progress.
        """
        unit_path = Path(unit_path)
        if not unit_path.exists():
            raise FileNotFoundError(unit_path)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        unit_dur = self.ffmpeg.duration_seconds(unit_path)
        iters = self.compute_iterations(unit_dur, target_duration_seconds)

        # PRIMARY: instant loop via stream copy (no re-encode, completes in
        # seconds for hours-long output). This works because the unit clip is
        # already encoded at the target codec/size/fps inside build_seamless_unit.
        copy_cmd: list[str] = [
            self.ffmpeg.binary, "-y", "-hide_banner", "-loglevel", "error",
            "-stream_loop", str(iters - 1),
            "-i", str(unit_path),
            "-t", f"{target_duration_seconds:.3f}",
            "-c", "copy",
            "-movflags", "+faststart",
            "-an",
            str(out),
        ]
        try:
            self._run_streaming(
                copy_cmd, target_duration_seconds,
                on_progress=on_progress, cancel_event=cancel_event,
            )
        except FFmpegError as e:
            logger.warning("Stream copy loop failed (%s); falling back to re-encode.", e)
            # FALLBACK: re-encode with fast preset.
            enc_cmd: list[str] = [
                self.ffmpeg.binary, "-y", "-hide_banner",
                "-stream_loop", str(iters - 1),
                "-i", str(unit_path),
                "-t", f"{target_duration_seconds:.3f}",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                "-an",
                str(out),
            ]
            self._run_streaming(
                enc_cmd, target_duration_seconds,
                on_progress=on_progress, cancel_event=cancel_event,
            )

        return LoopResult(
            output_path=out,
            intermediate_path=unit_path if (loop_options and loop_options.keep_intermediate) else None,
            unit_duration=unit_dur,
            iterations=iters,
        )

    def _run_streaming(
        self,
        cmd: list[str],
        target_duration: float,
        on_progress: Optional[Callable[[float, float], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> None:
        """Run ffmpeg streaming stdout, calling on_progress on each progress line."""
        logger.info("LoopEngine FFmpeg: %s", " ".join(str(c) for c in cmd))
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        assert proc.stdout is not None
        tail: list[str] = []
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    tail.append(line)
                    if len(tail) > 60:
                        tail.pop(0)
                if cancel_event is not None and cancel_event.is_set():
                    proc.terminate()
                    raise FFmpegError("Loop cancelled by user")
                m = self._PROGRESS_RE.search(line)
                if m and on_progress is not None:
                    hh, mm, ss = m.groups()
                    elapsed = int(hh) * 3600 + int(mm) * 60 + float(ss)
                    try:
                        on_progress(elapsed, target_duration)
                    except Exception:
                        pass
            proc.wait()
        finally:
            if proc.poll() is None:
                proc.kill()
        if proc.returncode != 0:
            tail_text = "\n".join(tail[-20:])
            raise FFmpegError(
                f"FFmpeg loop step failed (exit {proc.returncode}).\nLast output:\n{tail_text}"
            )

    def cleanup_temp(self, keep: Sequence[Path] = ()) -> None:
        keep_set = {Path(p).resolve() for p in keep}
        for child in self.temp_dir.iterdir():
            try:
                if child.resolve() in keep_set:
                    continue
                if child.is_file():
                    child.unlink()
                else:
                    shutil.rmtree(child, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Cleanup skipped {child}: {e}")
