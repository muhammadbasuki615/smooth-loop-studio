"""Audio engine for Smooth Loop Studio.

Handles:
 - importing many audio tracks (MP3, WAV, FLAC, AAC, OGG, M4A)
 - playlists, shuffle, repeat
 - fade in/out, crossfade, normalization, ducking
 - replacing or muting the source video's audio
 - mixing multiple tracks with per-track volume + delay
 - producing a final audio track of an arbitrary target duration
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .ffmpeg_utils import FFmpeg, FFmpegError, build_filter_chain
from .logger import get_logger

logger = get_logger(__name__)

SUPPORTED_AUDIO_FORMATS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus"}


class PlaybackMode(str, enum.Enum):
    SEQUENCE = "sequence"
    SHUFFLE = "shuffle"
    REPEAT_ONE = "repeat_one"
    REPEAT_ALL = "repeat_all"


@dataclass
class AudioTrack:
    path: Path
    volume: float = 1.0  # linear gain
    fade_in: float = 0.0
    fade_out: float = 0.0
    start_offset: float = 0.0  # seconds to start within the source
    delay: float = 0.0  # delay before this track plays (when in mix)
    loop: bool = False
    enabled: bool = True

    def __post_init__(self) -> None:
        self.path = Path(self.path)


@dataclass
class AudioMixOptions:
    target_duration: float = 0.0  # 0 = match input video duration
    normalize: bool = True
    auto_balance: bool = True
    crossfade_seconds: float = 1.0
    mode: PlaybackMode = PlaybackMode.SEQUENCE
    mute_video_audio: bool = True
    replace_video_audio: bool = True
    ducking: bool = False
    ducking_ratio: float = 6.0  # how aggressive (sidechaincompress)
    sample_rate: int = 48000
    channels: int = 2
    output_codec: str = "aac"
    output_bitrate: str = "192k"


class AudioEngine:
    def __init__(self, ffmpeg: FFmpeg | None = None, temp_dir: Path | str = "temp") -> None:
        self.ffmpeg = ffmpeg or FFmpeg()
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    # ---------------- helpers ----------------

    @staticmethod
    def is_supported(path: str | Path) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_AUDIO_FORMATS

    @staticmethod
    def order_tracks(tracks: Sequence[AudioTrack], mode: PlaybackMode, seed: int = 0) -> list[AudioTrack]:
        if mode == PlaybackMode.SHUFFLE:
            rng = random.Random(seed or None)
            shuffled = list(tracks)
            rng.shuffle(shuffled)
            return shuffled
        return list(tracks)

    def duration(self, path: str | Path) -> float:
        try:
            return self.ffmpeg.duration_seconds(path)
        except FFmpegError:
            return 0.0

    # ---------------- track concat with crossfade ----------------

    def build_concat_playlist(
        self,
        tracks: Sequence[AudioTrack],
        options: AudioMixOptions,
        output_path: str | Path | None = None,
    ) -> Path:
        """Concatenate audio tracks into one continuous file with crossfades."""
        if not tracks:
            raise ValueError("No audio tracks provided")
        ordered = self.order_tracks(tracks, options.mode)

        out = Path(output_path) if output_path else self.temp_dir / "_playlist.m4a"

        if len(ordered) == 1:
            # Single track: just process fades + normalize.
            return self._render_single_track(ordered[0], out, options)

        # Build a chained acrossfade graph
        inputs: list[str] = []
        cmd: list[str] = [self.ffmpeg.binary, "-y"]
        for i, t in enumerate(ordered):
            cmd += ["-i", str(t.path)]
            label = f"a{i}"
            inputs.append(label)

        filter_parts: list[str] = []
        # Per-track preprocessing
        for i, t in enumerate(ordered):
            chain: list[str] = []
            if t.start_offset > 0:
                chain.append(f"atrim=start={t.start_offset:.3f}")
                chain.append("asetpts=PTS-STARTPTS")
            if t.volume != 1.0:
                chain.append(f"volume={t.volume:.3f}")
            if t.fade_in > 0:
                chain.append(f"afade=t=in:st=0:d={t.fade_in:.3f}")
            if t.fade_out > 0:
                d = self.duration(t.path)
                start = max(0.0, d - t.fade_out - t.start_offset)
                chain.append(f"afade=t=out:st={start:.3f}:d={t.fade_out:.3f}")
            chain.append(f"aformat=sample_rates={options.sample_rate}:channel_layouts=stereo")
            if chain:
                filter_parts.append(f"[{i}:a]" + ",".join(chain) + f"[p{i}]")
            else:
                filter_parts.append(f"[{i}:a]anull[p{i}]")

        # Chain acrossfade
        prev = "p0"
        for i in range(1, len(ordered)):
            cur = f"p{i}"
            out_label = "mix" if i == len(ordered) - 1 else f"m{i}"
            cf = max(0.05, options.crossfade_seconds)
            filter_parts.append(
                f"[{prev}][{cur}]acrossfade=d={cf:.3f}:c1=tri:c2=tri[{out_label}]"
            )
            prev = out_label

        final_label = "mix"
        if options.normalize:
            filter_parts.append(f"[{final_label}]loudnorm=I=-16:TP=-1.5:LRA=11[norm]")
            final_label = "norm"

        cmd += [
            "-filter_complex", ";".join(filter_parts),
            "-map", f"[{final_label}]",
            "-c:a", options.output_codec,
            "-b:a", options.output_bitrate,
            "-ar", str(options.sample_rate),
            "-ac", str(options.channels),
            str(out),
        ]
        self.ffmpeg.run(cmd, capture=True)
        return out

    def _render_single_track(self, t: AudioTrack, out: Path, options: AudioMixOptions) -> Path:
        chain: list[str] = []
        if t.start_offset > 0:
            chain.append(f"atrim=start={t.start_offset:.3f}")
            chain.append("asetpts=PTS-STARTPTS")
        if t.volume != 1.0:
            chain.append(f"volume={t.volume:.3f}")
        if t.fade_in > 0:
            chain.append(f"afade=t=in:st=0:d={t.fade_in:.3f}")
        if t.fade_out > 0:
            d = self.duration(t.path)
            start = max(0.0, d - t.fade_out - t.start_offset)
            chain.append(f"afade=t=out:st={start:.3f}:d={t.fade_out:.3f}")
        chain.append(f"aformat=sample_rates={options.sample_rate}:channel_layouts=stereo")
        if options.normalize:
            chain.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        af = build_filter_chain(chain)
        cmd = [
            self.ffmpeg.binary, "-y",
            "-i", str(t.path),
            "-af", af,
            "-c:a", options.output_codec,
            "-b:a", options.output_bitrate,
            "-ar", str(options.sample_rate),
            "-ac", str(options.channels),
            str(out),
        ]
        self.ffmpeg.run(cmd, capture=True)
        return out

    # ---------------- loop / pad to target duration ----------------

    def loop_to_duration(
        self,
        audio_path: str | Path,
        target_duration: float,
        output_path: str | Path | None = None,
        fade_join: float = 0.5,
    ) -> Path:
        """Loop an audio file to the target duration with seamless joins."""
        src = Path(audio_path)
        out = Path(output_path) if output_path else self.temp_dir / f"_aloop_{src.stem}.m4a"
        src_d = max(0.1, self.duration(src))
        loops = max(0, int(target_duration // src_d))  # full repeats minus 1
        cmd = [
            self.ffmpeg.binary, "-y",
            "-stream_loop", str(max(0, loops)),
            "-i", str(src),
            "-t", f"{target_duration:.3f}",
            "-af", f"afade=t=in:st=0:d={fade_join:.3f},afade=t=out:st={max(0.0, target_duration - fade_join):.3f}:d={fade_join:.3f}",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out),
        ]
        self.ffmpeg.run(cmd, capture=True)
        return out

    # ---------------- mix multiple parallel tracks ----------------

    def mix_layers(
        self,
        tracks: Sequence[AudioTrack],
        options: AudioMixOptions,
        target_duration: float,
        output_path: str | Path | None = None,
    ) -> Path:
        """Mix multiple tracks in parallel (ambience + music + sfx)."""
        if not tracks:
            raise ValueError("No tracks provided")
        out = Path(output_path) if output_path else self.temp_dir / "_layers.m4a"
        cmd: list[str] = [self.ffmpeg.binary, "-y"]
        for t in tracks:
            if t.loop:
                cmd += ["-stream_loop", "-1"]
            cmd += ["-i", str(t.path)]

        filter_parts: list[str] = []
        for i, t in enumerate(tracks):
            chain: list[str] = []
            if t.start_offset > 0:
                chain.append(f"atrim=start={t.start_offset:.3f}")
                chain.append("asetpts=PTS-STARTPTS")
            if t.delay > 0:
                chain.append(f"adelay={int(t.delay * 1000)}|{int(t.delay * 1000)}")
            if t.volume != 1.0:
                chain.append(f"volume={t.volume:.3f}")
            if t.fade_in > 0:
                chain.append(f"afade=t=in:st=0:d={t.fade_in:.3f}")
            if t.fade_out > 0:
                start = max(0.0, target_duration - t.fade_out)
                chain.append(f"afade=t=out:st={start:.3f}:d={t.fade_out:.3f}")
            chain.append(f"aformat=sample_rates={options.sample_rate}:channel_layouts=stereo")
            filter_parts.append(f"[{i}:a]" + ",".join(chain) + f"[t{i}]")

        mix_inputs = "".join(f"[t{i}]" for i in range(len(tracks)))
        filter_parts.append(
            f"{mix_inputs}amix=inputs={len(tracks)}:duration=longest:dropout_transition=0:normalize=0[mix]"
        )

        final_label = "mix"
        if options.normalize:
            filter_parts.append("[mix]loudnorm=I=-16:TP=-1.5:LRA=11[norm]")
            final_label = "norm"

        cmd += [
            "-filter_complex", ";".join(filter_parts),
            "-map", f"[{final_label}]",
            "-t", f"{target_duration:.3f}",
            "-c:a", options.output_codec,
            "-b:a", options.output_bitrate,
            "-ar", str(options.sample_rate),
            "-ac", str(options.channels),
            str(out),
        ]
        self.ffmpeg.run(cmd, capture=True)
        return out

    # ---------------- combine with video ----------------

    def attach_audio_to_video(
        self,
        video_path: str | Path,
        audio_path: str | Path | None,
        output_path: str | Path,
        options: AudioMixOptions,
    ) -> Path:
        """Mux audio onto an existing rendered (silent or loud) video.

        Behavior:
          - If ``options.mute_video_audio`` and audio_path is None -> output is silent.
          - If audio_path is given and ``replace_video_audio`` -> source video audio is dropped.
          - If audio_path is given and replace is False -> source audio is mixed with provided audio.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if audio_path is None and options.mute_video_audio:
            cmd = [
                self.ffmpeg.binary, "-y",
                "-i", str(video_path),
                "-c:v", "copy", "-an",
                str(out),
            ]
            self.ffmpeg.run(cmd, capture=True)
            return out

        cmd = [self.ffmpeg.binary, "-y", "-i", str(video_path)]
        if audio_path is not None:
            cmd += ["-i", str(audio_path)]

        if audio_path is not None and not options.replace_video_audio:
            # Mix source audio + provided audio
            filter_complex = (
                f"[0:a][1:a]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a]"
            )
            cmd += [
                "-filter_complex", filter_complex,
                "-map", "0:v", "-map", "[a]",
                "-c:v", "copy",
                "-c:a", options.output_codec, "-b:a", options.output_bitrate,
                "-shortest",
                str(out),
            ]
        elif audio_path is not None:
            cmd += [
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", options.output_codec, "-b:a", options.output_bitrate,
                "-shortest",
                str(out),
            ]
        else:
            cmd += ["-c:v", "copy", "-c:a", "copy", str(out)]

        self.ffmpeg.run(cmd, capture=True)
        return out
