"""Core engine modules for Smooth Loop Studio."""

from .config import AppConfig, load_config, save_config
from .logger import get_logger
from .ffmpeg_utils import FFmpeg, FFmpegError, GPUInfo, detect_gpu
from .loop_engine import LoopEngine, LoopMode, LoopOptions
from .transitions import TransitionEngine, TransitionType, TransitionOptions
from .audio_engine import AudioEngine, AudioTrack, AudioMixOptions
from .overlay_engine import OverlayEngine, OverlayLayer, BlendMode
from .effects import EffectStack, EffectType, EffectParams, LUT
from .export_engine import ExportEngine, ExportSettings, RenderJob, RenderQueue
from .project import Project, ProjectIO
from .presets import PresetManager, get_builtin_presets
from .playlist import Playlist, PlaylistItem
from .plugin_api import PluginManager, BasePlugin
from .performance import PerformanceMonitor
from .error_handler import safe_call, ErrorReport

__all__ = [
    "AppConfig",
    "load_config",
    "save_config",
    "get_logger",
    "FFmpeg",
    "FFmpegError",
    "GPUInfo",
    "detect_gpu",
    "LoopEngine",
    "LoopMode",
    "LoopOptions",
    "TransitionEngine",
    "TransitionType",
    "TransitionOptions",
    "AudioEngine",
    "AudioTrack",
    "AudioMixOptions",
    "OverlayEngine",
    "OverlayLayer",
    "BlendMode",
    "EffectStack",
    "EffectType",
    "EffectParams",
    "LUT",
    "ExportEngine",
    "ExportSettings",
    "RenderJob",
    "RenderQueue",
    "Project",
    "ProjectIO",
    "PresetManager",
    "get_builtin_presets",
    "Playlist",
    "PlaylistItem",
    "PluginManager",
    "BasePlugin",
    "PerformanceMonitor",
    "safe_call",
    "ErrorReport",
]
