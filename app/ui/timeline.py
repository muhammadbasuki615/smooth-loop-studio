"""Multi-track timeline editor (simplified visual)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)


@dataclass
class TimelineClip:
    name: str
    start: float
    duration: float
    color: str = "#00E5FF"
    track: int = 0


class TimelineView(QGraphicsView):
    pixels_per_second = 40.0
    track_height = 36
    track_gap = 6

    clip_selected = Signal(TimelineClip)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scene_ = QGraphicsScene(self)
        self.setScene(self.scene_)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor(8, 12, 22))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setMinimumHeight(180)
        self.clips: List[TimelineClip] = []

    def set_zoom(self, pps: float) -> None:
        self.pixels_per_second = max(4.0, pps)
        self.redraw()

    def add_clip(self, clip: TimelineClip) -> None:
        self.clips.append(clip)
        self.redraw()

    def clear_clips(self) -> None:
        self.clips.clear()
        self.redraw()

    def redraw(self) -> None:
        self.scene_.clear()
        # Time ruler
        ruler_pen = QPen(QColor(255, 255, 255, 40))
        total_s = max(60.0, max([c.start + c.duration for c in self.clips], default=60.0))
        for s in range(0, int(total_s) + 1, 5):
            x = s * self.pixels_per_second
            self.scene_.addLine(x, 0, x, 14, ruler_pen)
            t = self.scene_.addText(f"{s:02d}s")
            t.setDefaultTextColor(QColor(180, 200, 230))
            t.setPos(x + 2, -4)

        for c in self.clips:
            y = 24 + c.track * (self.track_height + self.track_gap)
            rect = QRectF(
                c.start * self.pixels_per_second,
                y,
                c.duration * self.pixels_per_second,
                self.track_height,
            )
            item = QGraphicsRectItem(rect)
            color = QColor(c.color)
            color.setAlpha(180)
            item.setBrush(QBrush(color))
            item.setPen(QPen(QColor("#FFFFFF"), 0.5))
            item.setData(0, c.name)
            self.scene_.addItem(item)
            label = self.scene_.addText(c.name)
            label.setDefaultTextColor(QColor(20, 20, 30))
            label.setPos(rect.left() + 6, rect.top() + 4)

        self.scene_.setSceneRect(0, 0, max(800.0, total_s * self.pixels_per_second), 240)


class TimelinePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(QLabel("Timeline"))
        top.addStretch(1)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(10, 200)
        self.zoom.setValue(40)
        self.zoom.setFixedWidth(180)
        top.addWidget(QLabel("Zoom"))
        top.addWidget(self.zoom)
        lay.addLayout(top)

        self.view = TimelineView(self)
        lay.addWidget(self.view, 1)

        self.zoom.valueChanged.connect(lambda v: self.view.set_zoom(float(v)))

    def add_video_clip(self, name: str, start: float, duration: float) -> None:
        self.view.add_clip(TimelineClip(name, start, duration, color="#00E5FF", track=0))

    def add_audio_clip(self, name: str, start: float, duration: float, layer: int = 1) -> None:
        self.view.add_clip(TimelineClip(name, start, duration, color="#FF4ECD", track=layer))

    def add_overlay_clip(self, name: str, start: float, duration: float, layer: int = 3) -> None:
        self.view.add_clip(TimelineClip(name, start, duration, color="#FFD600", track=layer))

    def clear(self) -> None:
        self.view.clear_clips()
