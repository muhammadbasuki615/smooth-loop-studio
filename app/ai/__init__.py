"""AI tools for Smooth Loop Studio.

All AI modules are designed to gracefully degrade if model files or ONNX
Runtime aren't available. They provide useful CPU fallbacks built on OpenCV
where possible.
"""

from .interpolation import FrameInterpolator
from .upscale import Upscaler
from .denoise import Denoiser
from .color_enhance import ColorEnhancer
from .scene_detection import SceneDetector
from .audio_balance import AudioBalancer
from .beat_sync import BeatSync
from .ambience import AmbienceGenerator
from .overlay_placement import SmartOverlayPlacer

__all__ = [
    "FrameInterpolator",
    "Upscaler",
    "Denoiser",
    "ColorEnhancer",
    "SceneDetector",
    "AudioBalancer",
    "BeatSync",
    "AmbienceGenerator",
    "SmartOverlayPlacer",
]
