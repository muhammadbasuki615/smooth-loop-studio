"""Configuration loading and saving."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_FILE = _ROOT / "config.json"


@dataclass
class EngineConfig:
    default_loop_seconds: int = 3600
    default_transition_seconds: float = 1.5
    default_crossfade_audio_seconds: float = 1.0
    default_fps: int = 30
    default_resolution: tuple[int, int] = (1920, 1080)
    preview_resolution: tuple[int, int] = (854, 480)
    preview_fps: int = 24
    cache_max_frames: int = 256
    use_gpu: bool = True
    gpu_codec_preference: list[str] = field(
        default_factory=lambda: ["nvenc", "qsv", "amf", "cpu"]
    )
    threads: int = 0  # 0 = auto


@dataclass
class ExportConfig:
    default_format: str = "mp4"
    default_codec: str = "h264"
    default_bitrate: str = "8M"
    smart_bitrate: bool = True
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    two_pass: bool = False


@dataclass
class UIConfig:
    window_size: tuple[int, int] = (1480, 900)
    accent_color: str = "#00E5FF"
    secondary_accent: str = "#FF4ECD"
    glass_blur: int = 18
    show_fps_monitor: bool = True
    show_gpu_monitor: bool = True


@dataclass
class AIConfig:
    interpolation_enabled: bool = False
    upscale_enabled: bool = False
    denoise_enabled: bool = False
    scene_detection_enabled: bool = True
    beat_sync_enabled: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"
    rotate_mb: int = 10
    backup_count: int = 5


@dataclass
class PathsConfig:
    ffmpeg_bin: str = "app/ffmpeg/bin"
    temp: str = "app/temp"
    exports: str = "app/exports"
    logs: str = "app/logs"
    presets: str = "app/presets"
    overlays: str = "app/overlays"
    music: str = "app/music"
    plugins: str = "app/plugins"
    ai_models: str = "app/ai/models"


@dataclass
class AppMeta:
    name: str = "Smooth Loop Studio"
    version: str = "1.0.0"
    author: str = "Smooth Loop Studio"
    default_theme: str = "dark_glass"


@dataclass
class AppConfig:
    app: AppMeta = field(default_factory=AppMeta)
    paths: PathsConfig = field(default_factory=PathsConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def root(self) -> Path:
        return _ROOT

    def abs_path(self, key: str) -> Path:
        rel = getattr(self.paths, key, None)
        if rel is None:
            raise KeyError(f"Unknown path key: {key}")
        p = Path(rel)
        return p if p.is_absolute() else _ROOT / p


def _dict_to_config(data: dict[str, Any]) -> AppConfig:
    cfg = AppConfig()
    if "app" in data:
        cfg.app = AppMeta(**{**asdict(cfg.app), **data["app"]})
    if "paths" in data:
        cfg.paths = PathsConfig(**{**asdict(cfg.paths), **data["paths"]})
    if "engine" in data:
        eng = {**asdict(cfg.engine), **data["engine"]}
        # tuples may serialize as lists
        if isinstance(eng.get("default_resolution"), list):
            eng["default_resolution"] = tuple(eng["default_resolution"])
        if isinstance(eng.get("preview_resolution"), list):
            eng["preview_resolution"] = tuple(eng["preview_resolution"])
        cfg.engine = EngineConfig(**eng)
    if "export" in data:
        cfg.export = ExportConfig(**{**asdict(cfg.export), **data["export"]})
    if "ui" in data:
        ui = {**asdict(cfg.ui), **data["ui"]}
        if isinstance(ui.get("window_size"), list):
            ui["window_size"] = tuple(ui["window_size"])
        cfg.ui = UIConfig(**ui)
    if "ai" in data:
        cfg.ai = AIConfig(**{**asdict(cfg.ai), **data["ai"]})
    if "logging" in data:
        cfg.logging = LoggingConfig(**{**asdict(cfg.logging), **data["logging"]})
    return cfg


def load_config(path: Path | str | None = None) -> AppConfig:
    p = Path(path) if path else _CONFIG_FILE
    if not p.exists():
        logger.warning(f"config.json not found at {p}; using defaults")
        return AppConfig()
    try:
        with p.open("r", encoding="utf-8") as f:
            return _dict_to_config(json.load(f))
    except Exception as e:
        logger.exception(f"Failed to load config: {e}")
        return AppConfig()


def save_config(cfg: AppConfig, path: Path | str | None = None) -> None:
    p = Path(path) if path else _CONFIG_FILE
    try:
        data = asdict(cfg)
        # convert tuples to lists for JSON
        data["engine"]["default_resolution"] = list(data["engine"]["default_resolution"])
        data["engine"]["preview_resolution"] = list(data["engine"]["preview_resolution"])
        data["ui"]["window_size"] = list(data["ui"]["window_size"])
        with p.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.exception(f"Failed to save config: {e}")
