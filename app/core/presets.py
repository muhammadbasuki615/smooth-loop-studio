"""Built-in render presets (YouTube, TikTok, Instagram, Wallpaper, Livestream)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .export_engine import ExportSettings


@dataclass(frozen=True)
class RenderPreset:
    name: str
    description: str
    width: int
    height: int
    fps: int
    codec: str
    bitrate: str
    container: str
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    crf: int | None = None
    preset: str = "veryfast"

    def to_export_settings(self, output_path: str | Path) -> ExportSettings:
        return ExportSettings(
            output_path=Path(output_path),
            container=self.container,
            codec=self.codec,
            width=self.width,
            height=self.height,
            fps=self.fps,
            bitrate=self.bitrate,
            audio_codec=self.audio_codec,
            audio_bitrate=self.audio_bitrate,
            crf=self.crf,
            preset=self.preset,
            use_gpu=True,
        )


def get_builtin_presets() -> Dict[str, RenderPreset]:
    return {
        "youtube_1080p": RenderPreset(
            name="YouTube 1080p",
            description="YouTube recommended 1080p 30fps, H.264, 8 Mbps.",
            width=1920, height=1080, fps=30,
            codec="h264", bitrate="8M", container="mp4",
        ),
        "youtube_4k": RenderPreset(
            name="YouTube 4K",
            description="YouTube recommended 2160p 30fps, H.265, 40 Mbps.",
            width=3840, height=2160, fps=30,
            codec="h265", bitrate="40M", container="mp4",
        ),
        "youtube_long_loop": RenderPreset(
            name="YouTube 24h Loop",
            description="Optimized for very long looping uploads: 1080p 30fps H.264 6 Mbps.",
            width=1920, height=1080, fps=30,
            codec="h264", bitrate="6M", container="mp4",
        ),
        "tiktok_vertical": RenderPreset(
            name="TikTok / Reels / Shorts",
            description="9:16 vertical, 1080x1920 30fps H.264.",
            width=1080, height=1920, fps=30,
            codec="h264", bitrate="6M", container="mp4",
        ),
        "instagram_square": RenderPreset(
            name="Instagram Square",
            description="1:1 square 1080x1080 30fps H.264.",
            width=1080, height=1080, fps=30,
            codec="h264", bitrate="5M", container="mp4",
        ),
        "instagram_story": RenderPreset(
            name="Instagram Story",
            description="9:16 vertical 1080x1920 30fps H.264.",
            width=1080, height=1920, fps=30,
            codec="h264", bitrate="6M", container="mp4",
        ),
        "wallpaper_engine": RenderPreset(
            name="Wallpaper Engine",
            description="Optimized for Wallpaper Engine: 1080p 30fps H.264 4 Mbps (light).",
            width=1920, height=1080, fps=30,
            codec="h264", bitrate="4M", container="mp4",
            preset="medium",
        ),
        "livestream_rtmp": RenderPreset(
            name="Livestream RTMP",
            description="1080p 60fps H.264 6 Mbps; good baseline for OBS feeds.",
            width=1920, height=1080, fps=60,
            codec="h264", bitrate="6M", container="mp4",
            preset="veryfast",
        ),
        "ambience_2k": RenderPreset(
            name="Ambience 2K",
            description="2560x1440 30fps H.265 10 Mbps for cinematic ambience.",
            width=2560, height=1440, fps=30,
            codec="h265", bitrate="10M", container="mp4",
        ),
        "asmr_high_bitrate": RenderPreset(
            name="ASMR High Bitrate",
            description="1080p 60fps H.264 12 Mbps for noise-sensitive content.",
            width=1920, height=1080, fps=60,
            codec="h264", bitrate="12M", container="mp4",
        ),
        "webm_vp9": RenderPreset(
            name="WebM VP9",
            description="WebM container with VP9 - good for web embedding.",
            width=1920, height=1080, fps=30,
            codec="vp9", bitrate="5M", container="webm",
        ),
    }


class PresetManager:
    def __init__(self) -> None:
        self._presets: Dict[str, RenderPreset] = dict(get_builtin_presets())
        self._user_presets: Dict[str, RenderPreset] = {}

    def all(self) -> Dict[str, RenderPreset]:
        d = dict(self._presets)
        d.update(self._user_presets)
        return d

    def get(self, key: str) -> RenderPreset:
        if key in self._user_presets:
            return self._user_presets[key]
        return self._presets[key]

    def add_user_preset(self, key: str, preset: RenderPreset) -> None:
        self._user_presets[key] = preset
