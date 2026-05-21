"""Export engine: ties together loop + transitions + overlays + audio into a final render.

Manages a render queue with multi-job, batch, retry, and resume semantics.
"""

from __future__ import annotations

import enum
import json
import re
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from .audio_engine import AudioEngine, AudioMixOptions, AudioTrack
from .effects import EffectStack
from .ffmpeg_utils import FFmpeg, FFmpegError, GPUInfo, build_filter_chain, detect_gpu
from .loop_engine import LoopEngine, LoopMode, LoopOptions, LoopResult
from .logger import get_logger
from .overlay_engine import OverlayEngine, OverlayLayer

logger = get_logger(__name__)


class RenderStatus(str, enum.Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    RENDERING = "rendering"
    MUXING = "muxing"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class ExportSettings:
    output_path: Path
    container: str = "mp4"            # mp4, mkv, mov, avi, webm
    codec: str = "h264"               # h264, h265, av1, vp9
    width: int = 1920
    height: int = 1080
    fps: int = 30
    bitrate: str = "8M"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    use_gpu: bool = True
    encoder_override: Optional[str] = None
    crf: Optional[int] = None         # if set, used instead of bitrate (for CPU codecs)
    preset: str = "veryfast"
    pixel_format: str = "yuv420p"
    two_pass: bool = False
    extra_args: list[str] = field(default_factory=list)
    overwrite: bool = True

    def __post_init__(self) -> None:
        self.output_path = Path(self.output_path)


@dataclass
class RenderJob:
    job_id: str
    source_video: Path
    target_duration: float
    loop_options: LoopOptions
    audio_tracks: List[AudioTrack] = field(default_factory=list)
    audio_options: AudioMixOptions = field(default_factory=AudioMixOptions)
    overlays: List[OverlayLayer] = field(default_factory=list)
    effects: EffectStack = field(default_factory=EffectStack)
    export: ExportSettings = field(default=None)  # type: ignore[assignment]
    status: RenderStatus = RenderStatus.PENDING
    progress: float = 0.0
    eta_seconds: float = 0.0
    error_message: str = ""
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    attempts: int = 0
    max_attempts: int = 2

    def __post_init__(self) -> None:
        self.source_video = Path(self.source_video)

    @classmethod
    def create(
        cls,
        source_video: str | Path,
        target_duration: float,
        export: ExportSettings,
        loop_options: LoopOptions | None = None,
        audio_tracks: Optional[List[AudioTrack]] = None,
        audio_options: Optional[AudioMixOptions] = None,
        overlays: Optional[List[OverlayLayer]] = None,
        effects: Optional[EffectStack] = None,
    ) -> "RenderJob":
        return cls(
            job_id=uuid.uuid4().hex[:12],
            source_video=Path(source_video),
            target_duration=target_duration,
            loop_options=loop_options or LoopOptions(target_duration_seconds=target_duration),
            audio_tracks=audio_tracks or [],
            audio_options=audio_options or AudioMixOptions(),
            overlays=overlays or [],
            effects=effects or EffectStack(),
            export=export,
        )


ProgressCallback = Callable[[RenderJob], None]


class ExportEngine:
    """High-level pipeline that performs full render of a job."""

    def __init__(
        self,
        ffmpeg: Optional[FFmpeg] = None,
        temp_dir: Path | str = "temp",
        gpu_info: Optional[GPUInfo] = None,
    ) -> None:
        self.ffmpeg = ffmpeg or FFmpeg()
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.loop_engine = LoopEngine(self.ffmpeg, self.temp_dir)
        self.audio_engine = AudioEngine(self.ffmpeg, self.temp_dir)
        self.overlay_engine = OverlayEngine(self.ffmpeg)
        self.gpu = gpu_info or detect_gpu(self.ffmpeg)

    # ------------------ encoder helpers ------------------

    def select_video_encoder(self, settings: ExportSettings) -> str:
        if settings.encoder_override:
            return settings.encoder_override
        if not settings.use_gpu:
            return {"h264": "libx264", "h265": "libx265", "av1": "libsvtav1", "vp9": "libvpx-vp9"}.get(
                settings.codec, "libx264"
            )
        return self.gpu.best_encoder(settings.codec)

    def smart_bitrate(self, settings: ExportSettings) -> str:
        # Rule-of-thumb bitrate based on resolution + fps
        pixels = settings.width * settings.height
        base_kbps = (pixels / (1280 * 720)) * 3500
        base_kbps *= (settings.fps / 30)
        if settings.codec in ("h265", "av1"):
            base_kbps *= 0.6
        return f"{int(max(2000, base_kbps))}k"

    # ------------------ main pipeline ------------------

    def render(
        self,
        job: RenderJob,
        on_progress: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Path:
        """Run a single render job end-to-end. Returns final output path."""
        job.started_at = time.time()
        job.status = RenderStatus.PREPARING
        if on_progress:
            on_progress(job)
        try:
            return self._render_inner(job, on_progress, cancel_event)
        except Exception as e:
            job.attempts += 1
            job.error_message = str(e)
            if job.attempts < job.max_attempts:
                logger.warning(f"Job {job.job_id} failed, retrying ({job.attempts}/{job.max_attempts}): {e}")
                time.sleep(1.0)
                return self.render(job, on_progress, cancel_event)
            job.status = RenderStatus.ERROR
            job.finished_at = time.time()
            if on_progress:
                on_progress(job)
            raise

    def _render_inner(
        self,
        job: RenderJob,
        on_progress: Optional[ProgressCallback],
        cancel_event: Optional[threading.Event],
    ) -> Path:
        s = job.export
        s.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Build a seamless unit clip
        job.status = RenderStatus.PREPARING
        if on_progress:
            on_progress(job)
        job.loop_options.output_size = (s.width, s.height)
        job.loop_options.output_fps = s.fps
        job.loop_options.target_duration_seconds = job.target_duration
        unit_path = self.loop_engine.build_seamless_unit(job.source_video, job.loop_options)

        # 2. Loop unit to target duration (silent video baseline)
        looped_video = self.temp_dir / f"_looped_{job.job_id}.mp4"
        self.loop_engine.build_long_loop(
            unit_path, job.target_duration, looped_video, job.loop_options
        )

        # 3. Apply overlays + effects (single re-encode)
        composed_video = self.temp_dir / f"_composed_{job.job_id}.mp4"
        self._apply_overlays_and_effects(looped_video, composed_video, job, on_progress, cancel_event)

        # 4. Build audio (if any tracks)
        audio_path: Optional[Path] = None
        if job.audio_tracks:
            audio_path = self._build_final_audio(job)

        # 5. Mux audio + video into final output (re-encode to target codec/bitrate)
        job.status = RenderStatus.MUXING
        if on_progress:
            on_progress(job)
        final_out = self._final_mux(composed_video, audio_path, job, on_progress, cancel_event)

        # 6. Cleanup intermediates
        for p in (unit_path, looped_video, composed_video):
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass
        if audio_path:
            try:
                audio_path.unlink(missing_ok=True)
            except Exception:
                pass

        job.status = RenderStatus.DONE
        job.progress = 100.0
        job.finished_at = time.time()
        if on_progress:
            on_progress(job)
        return final_out

    # ------------------ stages ------------------

    def _apply_overlays_and_effects(
        self,
        in_video: Path,
        out_video: Path,
        job: RenderJob,
        on_progress: Optional[ProgressCallback],
        cancel_event: Optional[threading.Event],
    ) -> None:
        layers = [l for l in job.overlays if l.enabled]
        has_effects = bool(job.effects and any(e.enabled for e in job.effects.effects))

        if not layers and not has_effects:
            shutil.copy2(in_video, out_video)
            return

        cmd: list[str] = [self.ffmpeg.binary, "-y", "-i", str(in_video)]

        if layers:
            extra_inputs, fc = self.overlay_engine.build_overlay_graph(0, layers, "comp")
            cmd += extra_inputs
            if has_effects:
                fc_eff = job.effects.build_complex("comp", "final")
                fc = f"{fc};{fc_eff}"
                map_label = "[final]"
            else:
                map_label = "[comp]"
            cmd += [
                "-filter_complex", fc,
                "-map", map_label,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-an",
                str(out_video),
            ]
        else:
            # Effects only — pick simple chain if possible, else filter_complex.
            if job.effects.has_complex():
                fc = job.effects.build_complex("0:v", "final")
                cmd += [
                    "-filter_complex", fc,
                    "-map", "[final]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p",
                    "-an",
                    str(out_video),
                ]
            else:
                vf = job.effects.build_chain()
                cmd += [
                    "-vf", vf,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p",
                    "-an",
                    str(out_video),
                ]

        self._run_with_progress(cmd, job, on_progress, cancel_event, stage="composing")

    def _build_final_audio(self, job: RenderJob) -> Path:
        """Combine and loop audio tracks to job duration."""
        tracks = [t for t in job.audio_tracks if t.enabled]
        if not tracks:
            return None  # type: ignore[return-value]

        # If any track is marked loop=True we use the parallel-mix layer pipeline
        # so background ambience can be infinitely looped under the main music.
        loop_layer_present = any(t.loop for t in tracks)
        if loop_layer_present or len(tracks) > 1 and job.audio_options.mode != "sequence":
            return self.audio_engine.mix_layers(
                tracks, job.audio_options, job.target_duration,
                output_path=self.temp_dir / f"_audio_{job.job_id}.m4a",
            )

        # Build a concatenated playlist...
        playlist = self.audio_engine.build_concat_playlist(
            tracks, job.audio_options,
            output_path=self.temp_dir / f"_playlist_{job.job_id}.m4a",
        )
        # ...then loop it to target duration.
        return self.audio_engine.loop_to_duration(
            playlist, job.target_duration,
            output_path=self.temp_dir / f"_audio_{job.job_id}.m4a",
            fade_join=job.audio_options.crossfade_seconds,
        )

    def _final_mux(
        self,
        video: Path,
        audio: Optional[Path],
        job: RenderJob,
        on_progress: Optional[ProgressCallback],
        cancel_event: Optional[threading.Event],
    ) -> Path:
        s = job.export
        enc = self.select_video_encoder(s)
        bitrate = s.bitrate or self.smart_bitrate(s)

        cmd: list[str] = [self.ffmpeg.binary, "-y" if s.overwrite else "-n", "-i", str(video)]
        if audio:
            cmd += ["-i", str(audio)]

        # Video encoder args
        cmd += ["-c:v", enc]
        if enc.startswith("lib"):
            if s.crf is not None:
                cmd += ["-crf", str(s.crf), "-preset", s.preset]
            else:
                cmd += ["-b:v", bitrate, "-preset", s.preset]
        else:
            # GPU encoders
            cmd += ["-b:v", bitrate]
            if "nvenc" in enc:
                cmd += ["-preset", "p5", "-tune", "hq", "-rc", "vbr"]
            elif "qsv" in enc:
                cmd += ["-preset", "veryfast"]
            elif "amf" in enc:
                cmd += ["-quality", "balanced"]

        cmd += ["-pix_fmt", s.pixel_format, "-r", str(s.fps)]
        # Audio
        if audio:
            cmd += ["-c:a", s.audio_codec, "-b:a", s.audio_bitrate, "-map", "0:v:0", "-map", "1:a:0"]
        else:
            if job.audio_options.mute_video_audio:
                cmd += ["-an"]
        # Container-specific extras
        if s.container == "mp4":
            cmd += ["-movflags", "+faststart"]
        cmd += list(s.extra_args)
        cmd.append(str(s.output_path))

        self._run_with_progress(cmd, job, on_progress, cancel_event, stage="encoding")
        return s.output_path

    # ------------------ runner ------------------

    _PROGRESS_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

    def _run_with_progress(
        self,
        cmd: list[str],
        job: RenderJob,
        on_progress: Optional[ProgressCallback],
        cancel_event: Optional[threading.Event],
        stage: str,
    ) -> None:
        logger.debug("FFmpeg [%s] %s", stage, " ".join(cmd))
        job.status = RenderStatus.RENDERING
        if on_progress:
            on_progress(job)
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        assert proc.stdout is not None
        start = time.time()
        try:
            for line in proc.stdout:
                if cancel_event is not None and cancel_event.is_set():
                    proc.terminate()
                    job.status = RenderStatus.CANCELLED
                    if on_progress:
                        on_progress(job)
                    raise RuntimeError("Render cancelled")
                m = self._PROGRESS_RE.search(line)
                if m:
                    hh, mm, ss = m.groups()
                    elapsed = int(hh) * 3600 + int(mm) * 60 + float(ss)
                    if job.target_duration > 0:
                        progress = min(99.0, elapsed * 100.0 / job.target_duration)
                        job.progress = progress
                        # Rough ETA
                        wall = time.time() - start
                        rate = elapsed / max(0.01, wall)
                        remaining = max(0.0, job.target_duration - elapsed) / max(0.01, rate)
                        job.eta_seconds = remaining
                        if on_progress:
                            on_progress(job)
            proc.wait()
        finally:
            if proc.poll() is None:
                proc.kill()
        if proc.returncode != 0:
            raise FFmpegError(f"FFmpeg stage '{stage}' failed (exit {proc.returncode})")


class RenderQueue:
    """Simple thread-based render queue with batch + retry."""

    def __init__(self, engine: ExportEngine) -> None:
        self.engine = engine
        self.jobs: List[RenderJob] = []
        self._lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._cancel_current = threading.Event()
        self._listeners: List[ProgressCallback] = []
        self._active: Optional[RenderJob] = None

    # listeners
    def add_listener(self, cb: ProgressCallback) -> None:
        self._listeners.append(cb)

    def _notify(self, job: RenderJob) -> None:
        for cb in list(self._listeners):
            try:
                cb(job)
            except Exception:
                logger.exception("Listener failed")

    def add_job(self, job: RenderJob) -> None:
        with self._lock:
            self.jobs.append(job)
        self._notify(job)

    def remove_job(self, job_id: str) -> None:
        with self._lock:
            self.jobs = [j for j in self.jobs if j.job_id != job_id]

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()
        self._cancel_current.set()

    def cancel_current(self) -> None:
        self._cancel_current.set()

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            job = self._next_pending()
            if job is None:
                time.sleep(0.5)
                continue
            self._active = job
            self._cancel_current.clear()
            try:
                self.engine.render(job, on_progress=self._notify, cancel_event=self._cancel_current)
            except Exception as e:
                logger.error(f"Job {job.job_id} failed: {e}")
            finally:
                self._active = None

    def _next_pending(self) -> Optional[RenderJob]:
        with self._lock:
            for j in self.jobs:
                if j.status == RenderStatus.PENDING:
                    return j
        return None
