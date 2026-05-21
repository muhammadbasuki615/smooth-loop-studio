"""Visual effects stack: color grading, LUTs, filters, stylistic looks."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


class EffectType(str, enum.Enum):
    COLOR_GRADE = "color_grade"
    LUT = "lut"
    CINEMATIC_TONE = "cinematic_tone"
    HDR_SIM = "hdr_sim"
    SHARPEN = "sharpen"
    GLOW = "glow"
    BLOOM = "bloom"
    MOTION_BLUR = "motion_blur"
    STABILIZE = "stabilize"
    SLOW_MOTION = "slow_motion"
    SPEED_RAMP = "speed_ramp"
    VHS = "vhs"
    RETRO = "retro"
    ANIME = "anime"
    DREAM = "dream"
    RELAX = "relax"
    DARK_AMBIENCE = "dark_ambience"
    NEON_CYBERPUNK = "neon_cyberpunk"
    LOFI = "lofi"
    FILM = "film"
    GRAIN = "grain"
    DENOISE = "denoise"
    UPSCALE = "upscale"


@dataclass
class EffectParams:
    # Generic params; specific effects use subset.
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    gamma: float = 1.0
    temperature: float = 0.0  # -1..1 (cold..warm)
    tint: float = 0.0  # -1..1
    sharpen_amount: float = 1.0
    glow_strength: float = 1.0
    grain_strength: float = 0.05
    blur_strength: float = 1.0
    speed: float = 1.0  # for slow motion / speed ramp
    lut_path: Optional[Path] = None
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class Effect:
    type: EffectType
    params: EffectParams = field(default_factory=EffectParams)
    enabled: bool = True


class LUT:
    """Lightweight wrapper for loading a .cube file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)

    def __str__(self) -> str:
        return str(self.path)


class EffectStack:
    """Compose an ordered list of effects into an ffmpeg filter chain.

    Two output modes:
      * ``build_chain()`` returns a simple comma-joined ``-vf`` string. This
        ONLY works for the subset of effects that don't need split/blend.
      * ``build_complex(in_label, out_label)`` returns a ``;``-separated
        filter_complex string with proper labels — handles every effect.

    The exporter calls ``build_chain`` first; if it sees a ``;`` it
    auto-switches to filter_complex (or ``build_complex`` is used directly).
    """

    # Effects that produce a multi-filter graph with split/blend.
    _COMPLEX = {EffectType.GLOW, EffectType.BLOOM, EffectType.DREAM}

    def __init__(self, effects: Optional[list[Effect]] = None) -> None:
        self.effects: list[Effect] = effects or []

    def add(self, effect: Effect) -> None:
        self.effects.append(effect)

    def clear(self) -> None:
        self.effects.clear()

    def has_complex(self) -> bool:
        return any(ef.enabled and ef.type in self._COMPLEX for ef in self.effects)

    # ---------------- simple chain (-vf) ----------------

    def build_chain(self) -> str:
        """Return a comma-joined filter chain (safe for ``-vf``).

        Complex effects (split/blend based) are skipped here — call
        ``build_complex()`` if you need those, or check ``has_complex()``
        first.
        """
        parts: list[str] = []
        for ef in self.effects:
            if not ef.enabled or ef.type in self._COMPLEX:
                continue
            parts.append(self._effect_simple(ef))
        return ",".join(p for p in parts if p)

    # ---------------- complex chain (-filter_complex) ----------------

    def build_complex(self, in_label: str, out_label: str) -> str:
        """Return a ``;``-separated filter_complex sequence with proper labels.

        ``in_label`` is the upstream label (e.g. ``"0:v"`` or ``"comp"``);
        ``out_label`` is the final output label.
        """
        enabled = [ef for ef in self.effects if ef.enabled]
        if not enabled:
            return f"[{in_label}]copy[{out_label}]"

        segments: list[str] = []
        cur = in_label
        for i, ef in enumerate(enabled):
            nxt = out_label if i == len(enabled) - 1 else f"_efx{i}"
            segments.append(self._effect_complex(ef, cur, nxt))
            cur = nxt
        return ";".join(segments)

    # ---------------- per-effect emitters ----------------

    def _effect_simple(self, ef: Effect) -> str:
        """Return a single ``,``-joinable filter expression for non-complex effects."""
        p = ef.params
        t = ef.type
        if t == EffectType.COLOR_GRADE:
            base = (
                f"eq=brightness={p.brightness:.3f}:contrast={p.contrast:.3f}:"
                f"saturation={p.saturation:.3f}:gamma={p.gamma:.3f}"
            )
            if p.temperature or p.tint:
                r = p.temperature * 0.3
                b = -p.temperature * 0.3
                g = p.tint * 0.3
                base += f",colorbalance=rs={r:.3f}:gs={g:.3f}:bs={b:.3f}"
            return base
        if t == EffectType.LUT and p.lut_path:
            return f"lut3d=file={p.lut_path}"
        if t == EffectType.CINEMATIC_TONE:
            return "eq=contrast=1.12:saturation=0.92:gamma=0.95,curves=preset=darker"
        if t == EffectType.HDR_SIM:
            return "eq=contrast=1.2:saturation=1.15:brightness=0.02,unsharp=5:5:1.0:5:5:0.0"
        if t == EffectType.SHARPEN:
            return f"unsharp=5:5:{p.sharpen_amount:.2f}:5:5:0.0"
        if t == EffectType.MOTION_BLUR:
            return "tblend=all_mode=average"
        if t == EffectType.STABILIZE:
            return "deshake"
        if t in (EffectType.SLOW_MOTION, EffectType.SPEED_RAMP):
            return f"setpts=PTS/{max(0.05, p.speed):.3f}"
        if t == EffectType.VHS:
            return "noise=alls=20:allf=t,curves=preset=vintage,hue=s=1.1"
        if t == EffectType.RETRO:
            return "curves=preset=vintage,eq=saturation=0.9:contrast=1.05"
        if t == EffectType.ANIME:
            return "eq=saturation=1.4:contrast=1.1,unsharp=5:5:1.5"
        if t == EffectType.RELAX:
            return "eq=brightness=0.02:saturation=0.85:contrast=0.98,curves=preset=lighter"
        if t == EffectType.DARK_AMBIENCE:
            return "eq=brightness=-0.05:contrast=1.1:saturation=0.7,curves=preset=darker"
        if t == EffectType.NEON_CYBERPUNK:
            return "eq=saturation=1.5:contrast=1.15,colorbalance=rs=0.05:gs=-0.05:bs=0.15"
        if t == EffectType.LOFI:
            return "eq=saturation=0.7:contrast=0.95,curves=preset=vintage,noise=alls=8:allf=t"
        if t == EffectType.FILM:
            return "curves=preset=vintage,noise=alls=10:allf=t,eq=saturation=0.95:contrast=1.05"
        if t == EffectType.GRAIN:
            strength = max(1, int(p.grain_strength * 100))
            return f"noise=alls={strength}:allf=t+u"
        if t == EffectType.DENOISE:
            return "hqdn3d=4:3:6:4"
        if t == EffectType.UPSCALE:
            return "scale=iw*2:ih*2:flags=lanczos"
        # Complex effects emit a placeholder; build_complex handles them.
        if t in self._COMPLEX:
            return "null"
        return "null"

    def _effect_complex(self, ef: Effect, in_label: str, out_label: str) -> str:
        """Return a labeled chain fragment ending in ``[out_label]``."""
        p = ef.params
        t = ef.type
        if t == EffectType.GLOW:
            s = max(1.0, p.glow_strength * 6.0)
            return (
                f"[{in_label}]split[_g_a_{out_label}][_g_b_{out_label}];"
                f"[_g_a_{out_label}]gblur=sigma={s:.2f}[_g_bl_{out_label}];"
                f"[_g_bl_{out_label}][_g_b_{out_label}]blend=all_mode=screen[{out_label}]"
            )
        if t == EffectType.BLOOM:
            s = max(1.0, p.glow_strength * 10.0)
            return (
                f"[{in_label}]split[_b_a_{out_label}][_b_b_{out_label}];"
                f"[_b_a_{out_label}]gblur=sigma={s:.2f},eq=contrast=1.3[_b_bl_{out_label}];"
                f"[_b_bl_{out_label}][_b_b_{out_label}]blend=all_mode=screen[{out_label}]"
            )
        if t == EffectType.DREAM:
            return (
                f"[{in_label}]split[_d_a_{out_label}][_d_b_{out_label}];"
                f"[_d_a_{out_label}]gblur=sigma=6[_d_bl_{out_label}];"
                f"[_d_bl_{out_label}][_d_b_{out_label}]blend=all_mode=screen:all_opacity=0.6,"
                f"eq=saturation=1.15[{out_label}]"
            )
        # Simple effect — wrap with explicit labels.
        return f"[{in_label}]{self._effect_simple(ef)}[{out_label}]"


def build_lookup_presets() -> dict[str, list[Effect]]:
    """Predefined effect stacks for one-click looks."""
    presets: dict[str, list[Effect]] = {}

    presets["cinematic"] = [
        Effect(EffectType.CINEMATIC_TONE),
        Effect(EffectType.GLOW, EffectParams(glow_strength=0.6)),
        Effect(EffectType.GRAIN, EffectParams(grain_strength=0.05)),
    ]
    presets["aesthetic_lofi"] = [
        Effect(EffectType.LOFI),
        Effect(EffectType.GRAIN, EffectParams(grain_strength=0.1)),
    ]
    presets["asmr_relax"] = [
        Effect(EffectType.RELAX),
        Effect(EffectType.GLOW, EffectParams(glow_strength=0.8)),
    ]
    presets["neon_cyber"] = [
        Effect(EffectType.NEON_CYBERPUNK),
        Effect(EffectType.BLOOM, EffectParams(glow_strength=1.2)),
    ]
    presets["dream"] = [Effect(EffectType.DREAM)]
    presets["anime"] = [Effect(EffectType.ANIME)]
    presets["vhs_retro"] = [Effect(EffectType.VHS), Effect(EffectType.GRAIN)]
    presets["dark_ambience"] = [Effect(EffectType.DARK_AMBIENCE)]
    return presets
