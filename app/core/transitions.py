"""Reusable FFmpeg transition filter builders.

These return filtergraph fragments for use inside larger compositions.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class TransitionType(str, enum.Enum):
    CROSSFADE = "crossfade"
    FADE = "fade"
    DISSOLVE = "dissolve"
    BLUR = "blur"
    ZOOM_BLEND = "zoom_blend"
    MOTION_BLEND = "motion_blend"
    MORPH = "morph"
    OPTICAL_FLOW = "optical_flow"
    AI_INTERPOLATION = "ai_interpolation"
    GLOW = "glow"
    SOFT_FADE = "soft_fade"
    CINEMATIC = "cinematic"
    DYNAMIC_BLEND = "dynamic_blend"
    GAUSSIAN_BLEND = "gaussian_blend"
    ULTRA_SMOOTH = "ultra_smooth"


# Mapping of our transition names to xfade transition names where direct mapping works.
_XFADE_MAP: dict[TransitionType, str] = {
    TransitionType.CROSSFADE: "fade",
    TransitionType.FADE: "fade",
    TransitionType.DISSOLVE: "dissolve",
    TransitionType.BLUR: "fade",  # blur is added separately
    TransitionType.ZOOM_BLEND: "smoothleft",
    TransitionType.MOTION_BLEND: "fade",
    TransitionType.MORPH: "pixelize",
    TransitionType.OPTICAL_FLOW: "fade",
    TransitionType.AI_INTERPOLATION: "fade",
    TransitionType.GLOW: "fadewhite",
    TransitionType.SOFT_FADE: "fade",
    TransitionType.CINEMATIC: "fadeblack",
    TransitionType.DYNAMIC_BLEND: "smoothup",
    TransitionType.GAUSSIAN_BLEND: "fade",
    TransitionType.ULTRA_SMOOTH: "fade",
}


@dataclass
class TransitionOptions:
    type: TransitionType = TransitionType.CROSSFADE
    duration: float = 1.0
    offset: float = 0.0
    opacity: float = 1.0
    blur_strength: float = 8.0
    motion_strength: float = 1.0
    speed: float = 1.0
    random_seed: int = 0
    extras: dict[str, str] = field(default_factory=dict)


class TransitionEngine:
    """Build filtergraph fragments for transitions between two streams.

    The returned string assumes two inputs ``[a]`` and ``[b]`` and yields ``[v]``.
    """

    @staticmethod
    def build_xfade(
        in_a: str,
        in_b: str,
        out_label: str,
        options: TransitionOptions,
    ) -> str:
        xname = _XFADE_MAP.get(options.type, "fade")
        return f"[{in_a}][{in_b}]xfade=transition={xname}:duration={options.duration:.3f}:offset={options.offset:.3f}[{out_label}]"

    @staticmethod
    def build_blur_chain(label_in: str, label_out: str, strength: float) -> str:
        s = max(0.1, strength)
        return f"[{label_in}]gblur=sigma={s:.2f}[{label_out}]"

    @staticmethod
    def build_glow(label_in: str, label_out: str, strength: float = 1.5) -> str:
        # Approximate "glow" via a blurred copy blended on top.
        s = max(1.0, strength * 6.0)
        return (
            f"[{label_in}]split=2[g1][g2];"
            f"[g1]gblur=sigma={s:.2f}[g1b];"
            f"[g2][g1b]blend=all_mode=screen[{label_out}]"
        )

    @staticmethod
    def build_cinematic_bars(
        label_in: str,
        label_out: str,
        bar_ratio: float = 0.12,
    ) -> str:
        """Add cinematic top/bottom black bars (letterbox)."""
        r = max(0.0, min(0.49, bar_ratio))
        return (
            f"[{label_in}]drawbox=y=0:w=iw:h=ih*{r:.4f}:color=black@1:t=fill,"
            f"drawbox=y=ih-ih*{r:.4f}:w=iw:h=ih*{r:.4f}:color=black@1:t=fill[{label_out}]"
        )

    @classmethod
    def build_full(
        cls,
        in_a: str,
        in_b: str,
        out_label: str,
        options: TransitionOptions,
    ) -> str:
        """Build a complete transition graph that combines the underlying
        xfade with extra effects (blur, glow, cinematic, etc.) where needed."""
        if options.type == TransitionType.BLUR:
            tmp = "_tblur_a"
            return (
                cls.build_blur_chain(in_a, tmp, options.blur_strength)
                + ";"
                + cls.build_xfade(tmp, in_b, out_label, options)
            )
        if options.type == TransitionType.GLOW:
            tmp = "_tglow_a"
            return (
                cls.build_glow(in_a, tmp, options.motion_strength)
                + ";"
                + cls.build_xfade(tmp, in_b, out_label, options)
            )
        if options.type == TransitionType.CINEMATIC:
            tmp = "_tcine_a"
            return (
                cls.build_cinematic_bars(in_a, tmp, 0.1)
                + ";"
                + cls.build_xfade(tmp, in_b, out_label, options)
            )
        if options.type == TransitionType.GAUSSIAN_BLEND:
            return cls.build_xfade(in_a, in_b, out_label, options)
        return cls.build_xfade(in_a, in_b, out_label, options)
