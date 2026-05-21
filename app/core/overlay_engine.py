"""Overlay engine: image / GIF / video / particle overlays composited on the base video."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .ffmpeg_utils import FFmpeg


class BlendMode(str, enum.Enum):
    NORMAL = "normal"
    SCREEN = "screen"
    MULTIPLY = "multiply"
    OVERLAY = "overlay"
    ADD = "addition"
    DIFFERENCE = "difference"
    LIGHTEN = "lighten"
    DARKEN = "darken"
    SOFTLIGHT = "softlight"
    HARDLIGHT = "hardlight"


@dataclass
class OverlayLayer:
    path: Path
    name: str = ""
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.NORMAL
    x: str = "(W-w)/2"  # ffmpeg expression
    y: str = "(H-h)/2"
    scale_w: int | str = -1  # -1 = keep aspect
    scale_h: int | str = -1
    rotation_deg: float = 0.0
    start_time: float = 0.0
    end_time: float | None = None  # None = full duration
    loop_overlay: bool = True
    speed: float = 1.0
    enabled: bool = True
    is_image: bool = False  # True for PNG/JPG single-frame

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if not self.name:
            self.name = self.path.stem
        if self.path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
            self.is_image = True


class OverlayEngine:
    """Build ffmpeg filter complex chains for overlay composition."""

    def __init__(self, ffmpeg: FFmpeg | None = None) -> None:
        self.ffmpeg = ffmpeg or FFmpeg()

    def build_overlay_graph(
        self,
        base_input_index: int,
        layers: Sequence[OverlayLayer],
        output_label: str = "comp",
    ) -> tuple[list[str], str]:
        """Return (extra ffmpeg input args, filter_complex string).

        The base video is assumed to be input ``base_input_index``. The graph
        composites all enabled layers and produces ``[output_label]``.
        """
        enabled = [l for l in layers if l.enabled]
        extra_inputs: list[str] = []
        layer_inputs_start = base_input_index + 1

        filter_parts: list[str] = []
        # base label
        filter_parts.append(f"[{base_input_index}:v]format=rgba[bg0]")

        if not enabled:
            filter_parts.append(f"[bg0]format=yuv420p[{output_label}]")
            return extra_inputs, ";".join(filter_parts)

        for i, layer in enumerate(enabled):
            layer_idx = layer_inputs_start + i
            if layer.is_image:
                extra_inputs += ["-loop", "1", "-i", str(layer.path)]
            else:
                if layer.loop_overlay:
                    extra_inputs += ["-stream_loop", "-1"]
                extra_inputs += ["-i", str(layer.path)]

            ov_chain: list[str] = []
            if layer.scale_w != -1 or layer.scale_h != -1:
                w = layer.scale_w if layer.scale_w != -1 else "iw"
                h = layer.scale_h if layer.scale_h != -1 else "ih"
                ov_chain.append(f"scale={w}:{h}")
            if layer.rotation_deg:
                ov_chain.append(
                    f"rotate={layer.rotation_deg}*PI/180:c=none:"
                    f"ow=rotw({layer.rotation_deg}*PI/180):oh=roth({layer.rotation_deg}*PI/180)"
                )
            if layer.speed != 1.0 and not layer.is_image:
                ov_chain.append(f"setpts=PTS/{max(0.05, layer.speed):.4f}")
            ov_chain.append("format=rgba")
            if layer.opacity < 1.0:
                ov_chain.append(f"colorchannelmixer=aa={layer.opacity:.3f}")

            filter_parts.append(f"[{layer_idx}:v]" + ",".join(ov_chain) + f"[ol{i}]")

            prev = f"bg{i}"
            nxt = f"bg{i+1}"
            enable_expr = ""
            if layer.start_time > 0 or layer.end_time is not None:
                start = layer.start_time
                end = layer.end_time if layer.end_time is not None else 1e9
                enable_expr = f":enable='between(t,{start:.3f},{end:.3f})'"

            if layer.blend_mode == BlendMode.NORMAL:
                filter_parts.append(
                    f"[{prev}][ol{i}]overlay=x={layer.x}:y={layer.y}:format=auto{enable_expr}[{nxt}]"
                )
            else:
                filter_parts.append(
                    f"[{prev}][ol{i}]overlay=x={layer.x}:y={layer.y}:format=auto{enable_expr}[ov_pos{i}];"
                    f"[{prev}][ov_pos{i}]blend=all_mode={layer.blend_mode.value}:all_opacity={layer.opacity:.3f}[{nxt}]"
                )

        last = f"bg{len(enabled)}"
        filter_parts.append(f"[{last}]format=yuv420p[{output_label}]")
        return extra_inputs, ";".join(filter_parts)

    def has_layers(self, layers: Iterable[OverlayLayer]) -> bool:
        return any(l.enabled for l in layers)
