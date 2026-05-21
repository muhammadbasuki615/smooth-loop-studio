"""Project save/load and auto-save system."""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, List, Optional

from .audio_engine import AudioMixOptions, AudioTrack
from .effects import Effect, EffectParams, EffectStack, EffectType
from .export_engine import ExportSettings
from .loop_engine import LoopMode, LoopOptions
from .logger import get_logger
from .overlay_engine import BlendMode, OverlayLayer

logger = get_logger(__name__)

PROJECT_VERSION = "1.0"


@dataclass
class Project:
    name: str = "Untitled Project"
    source_video: Optional[Path] = None
    target_duration: float = 3600.0
    loop_options: LoopOptions = field(default_factory=LoopOptions)
    audio_tracks: List[AudioTrack] = field(default_factory=list)
    audio_options: AudioMixOptions = field(default_factory=AudioMixOptions)
    overlays: List[OverlayLayer] = field(default_factory=list)
    effects: List[Effect] = field(default_factory=list)
    export_settings: Optional[ExportSettings] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: str = PROJECT_VERSION

    def touch(self) -> None:
        self.updated_at = time.time()

    def effect_stack(self) -> EffectStack:
        return EffectStack(self.effects)


class ProjectIO:
    """Serialize/deserialize Project to JSON."""

    @staticmethod
    def to_dict(p: Project) -> dict[str, Any]:
        d: dict[str, Any] = {
            "version": p.version,
            "name": p.name,
            "source_video": str(p.source_video) if p.source_video else None,
            "target_duration": p.target_duration,
            "loop_options": {
                **asdict(p.loop_options),
                "mode": p.loop_options.mode.value,
            },
            "audio_tracks": [
                {**asdict(t), "path": str(t.path)} for t in p.audio_tracks
            ],
            "audio_options": {
                **asdict(p.audio_options),
                "mode": p.audio_options.mode.value if hasattr(p.audio_options.mode, "value") else str(p.audio_options.mode),
            },
            "overlays": [
                {
                    **asdict(o),
                    "path": str(o.path),
                    "blend_mode": o.blend_mode.value,
                }
                for o in p.overlays
            ],
            "effects": [
                {
                    "type": e.type.value,
                    "enabled": e.enabled,
                    "params": {
                        **asdict(e.params),
                        "lut_path": str(e.params.lut_path) if e.params.lut_path else None,
                    },
                }
                for e in p.effects
            ],
            "export_settings": (
                {**asdict(p.export_settings), "output_path": str(p.export_settings.output_path)}
                if p.export_settings
                else None
            ),
            "metadata": p.metadata,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Project:
        loop = d.get("loop_options", {})
        if "mode" in loop:
            try:
                loop["mode"] = LoopMode(loop["mode"])
            except ValueError:
                loop["mode"] = LoopMode.CROSSFADE
        if "output_size" in loop and loop["output_size"] is not None:
            loop["output_size"] = tuple(loop["output_size"])
        loop_options = LoopOptions(**loop) if loop else LoopOptions()

        audio_opts_d = d.get("audio_options", {})
        from .audio_engine import PlaybackMode
        if "mode" in audio_opts_d:
            try:
                audio_opts_d["mode"] = PlaybackMode(audio_opts_d["mode"])
            except ValueError:
                audio_opts_d["mode"] = PlaybackMode.SEQUENCE
        audio_options = AudioMixOptions(**audio_opts_d) if audio_opts_d else AudioMixOptions()

        tracks: List[AudioTrack] = []
        for t in d.get("audio_tracks", []):
            t["path"] = Path(t["path"])
            tracks.append(AudioTrack(**t))

        overlays: List[OverlayLayer] = []
        for o in d.get("overlays", []):
            o["path"] = Path(o["path"])
            try:
                o["blend_mode"] = BlendMode(o["blend_mode"])
            except ValueError:
                o["blend_mode"] = BlendMode.NORMAL
            overlays.append(OverlayLayer(**o))

        effects: List[Effect] = []
        for e in d.get("effects", []):
            params_d = e.get("params", {})
            if params_d.get("lut_path"):
                params_d["lut_path"] = Path(params_d["lut_path"])
            else:
                params_d["lut_path"] = None
            params = EffectParams(**params_d)
            effects.append(
                Effect(type=EffectType(e["type"]), enabled=e.get("enabled", True), params=params)
            )

        es = d.get("export_settings")
        export_settings = None
        if es:
            es["output_path"] = Path(es["output_path"])
            export_settings = ExportSettings(**es)

        p = Project(
            name=d.get("name", "Untitled"),
            source_video=Path(d["source_video"]) if d.get("source_video") else None,
            target_duration=d.get("target_duration", 3600.0),
            loop_options=loop_options,
            audio_tracks=tracks,
            audio_options=audio_options,
            overlays=overlays,
            effects=effects,
            export_settings=export_settings,
            metadata=d.get("metadata", {}),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
            version=d.get("version", PROJECT_VERSION),
        )
        return p

    @classmethod
    def save(cls, project: Project, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        project.touch()
        backup = path.with_suffix(path.suffix + ".bak")
        if path.exists():
            try:
                shutil.copy2(path, backup)
            except Exception:
                pass
        with path.open("w", encoding="utf-8") as f:
            json.dump(cls.to_dict(project), f, indent=2)
        logger.info(f"Saved project to {path}")

    @classmethod
    def load(cls, path: str | Path) -> Project:
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
