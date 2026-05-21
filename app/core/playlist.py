"""Video playlist system: chain multiple source videos with auto transitions."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Sequence

from .transitions import TransitionOptions, TransitionType


@dataclass
class PlaylistItem:
    path: Path
    duration_override: Optional[float] = None
    transition_in: Optional[TransitionType] = None
    transition_out: Optional[TransitionType] = None

    def __post_init__(self) -> None:
        self.path = Path(self.path)


@dataclass
class Playlist:
    name: str = "Untitled Playlist"
    items: List[PlaylistItem] = field(default_factory=list)
    default_transition: TransitionType = TransitionType.CROSSFADE
    transition_duration: float = 1.0
    shuffle: bool = False
    repeat: bool = True
    smart_ordering: bool = False  # if True, sort by duration or similarity

    def add(self, item: PlaylistItem) -> None:
        self.items.append(item)

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.items):
            del self.items[index]

    def ordered(self, seed: int = 0) -> List[PlaylistItem]:
        items = list(self.items)
        if self.shuffle:
            rng = random.Random(seed or None)
            rng.shuffle(items)
        elif self.smart_ordering:
            items.sort(key=lambda i: (i.path.stat().st_size if i.path.exists() else 0))
        return items

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "items": [
                {
                    "path": str(i.path),
                    "duration_override": i.duration_override,
                    "transition_in": i.transition_in.value if i.transition_in else None,
                    "transition_out": i.transition_out.value if i.transition_out else None,
                }
                for i in self.items
            ],
            "default_transition": self.default_transition.value,
            "transition_duration": self.transition_duration,
            "shuffle": self.shuffle,
            "repeat": self.repeat,
            "smart_ordering": self.smart_ordering,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Playlist":
        items = []
        for i in d.get("items", []):
            items.append(
                PlaylistItem(
                    path=Path(i["path"]),
                    duration_override=i.get("duration_override"),
                    transition_in=TransitionType(i["transition_in"]) if i.get("transition_in") else None,
                    transition_out=TransitionType(i["transition_out"]) if i.get("transition_out") else None,
                )
            )
        return cls(
            name=d.get("name", "Untitled"),
            items=items,
            default_transition=TransitionType(d.get("default_transition", "crossfade")),
            transition_duration=d.get("transition_duration", 1.0),
            shuffle=d.get("shuffle", False),
            repeat=d.get("repeat", True),
            smart_ordering=d.get("smart_ordering", False),
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> "Playlist":
        with Path(path).open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
