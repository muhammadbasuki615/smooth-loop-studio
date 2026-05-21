"""Realtime preview widget powered by OpenCV.

Streams frames from a video file (or a virtual stream) into a QLabel using a
QThread to keep the UI responsive. Supports play/pause, seek, and target
preview FPS.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class _PreviewWorker(QObject):
    frame_ready = Signal(object)  # numpy ndarray or None
    finished = Signal()
    duration = Signal(float)

    def __init__(self, source: str, target_fps: int = 24) -> None:
        super().__init__()
        self._source = source
        self._target_fps = target_fps
        self._running = False
        self._seek_to: Optional[float] = None
        self._paused = False

    @Slot()
    def run(self) -> None:
        try:
            import cv2  # type: ignore
        except Exception:
            self.finished.emit()
            return
        cap = cv2.VideoCapture(self._source)
        if not cap.isOpened():
            self.finished.emit()
            return
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            self.duration.emit(float(total / fps) if fps else 0.0)
            interval_ms = int(1000 / max(1, self._target_fps))
            self._running = True
            from PySide6.QtCore import QThread as _QThread
            while self._running:
                if self._seek_to is not None:
                    cap.set(cv2.CAP_PROP_POS_MSEC, self._seek_to * 1000)
                    self._seek_to = None
                if self._paused:
                    _QThread.msleep(50)
                    continue
                ok, frame = cap.read()
                if not ok:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                self.frame_ready.emit(frame)
                _QThread.msleep(interval_ms)
        finally:
            cap.release()
            self.finished.emit()

    def stop(self) -> None:
        self._running = False

    def seek(self, seconds: float) -> None:
        self._seek_to = seconds

    def set_paused(self, paused: bool) -> None:
        self._paused = paused


class PreviewWidget(QWidget):
    """Embeddable preview widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.canvas = QLabel("No source loaded")
        self.canvas.setAlignment(Qt.AlignCenter)
        self.canvas.setMinimumSize(640, 360)
        self.canvas.setStyleSheet(
            "background-color: #000000; border-radius: 10px; color: #5D6478;"
        )
        layout.addWidget(self.canvas, 1)

        controls = QHBoxLayout()
        self.btn_play = QPushButton("Play")
        self.btn_stop = QPushButton("Stop")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_stop)
        controls.addWidget(self.slider, 1)
        layout.addLayout(controls)

        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_stop.clicked.connect(self.stop)
        self.slider.sliderReleased.connect(self._on_slider)

        self._thread: Optional[QThread] = None
        self._worker: Optional[_PreviewWorker] = None
        self._duration: float = 0.0
        self._playing: bool = False
        self._source: Optional[str] = None

    # ---------------- public ----------------

    def load(self, source: str | Path, target_fps: int = 24) -> None:
        self.stop()
        self._source = str(source)
        self._thread = QThread(self)
        self._worker = _PreviewWorker(self._source, target_fps=target_fps)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.frame_ready.connect(self._on_frame)
        self._worker.duration.connect(self._on_duration)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()
        self._playing = True
        self.btn_play.setText("Pause")

    def stop(self) -> None:
        if self._worker is not None:
            self._worker.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(500)
        self._worker = None
        self._thread = None
        self._playing = False
        self.btn_play.setText("Play")

    def toggle_play(self) -> None:
        if self._worker is None and self._source:
            self.load(self._source)
            return
        if self._worker is None:
            return
        self._playing = not self._playing
        self._worker.set_paused(not self._playing)
        self.btn_play.setText("Pause" if self._playing else "Play")

    # ---------------- internals ----------------

    @Slot(object)
    def _on_frame(self, frame) -> None:
        try:
            import cv2  # type: ignore
        except Exception:
            return
        if frame is None:
            return
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self.canvas.width(), self.canvas.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.canvas.setPixmap(pix)

    @Slot(float)
    def _on_duration(self, d: float) -> None:
        self._duration = d

    def _on_slider(self) -> None:
        if self._worker is None or self._duration <= 0:
            return
        ratio = self.slider.value() / 1000.0
        self._worker.seek(ratio * self._duration)
