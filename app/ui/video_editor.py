"""Video editor panel: pick source, loop mode, duration, transitions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.loop_engine import LoopMode, LoopOptions

from .preview import PreviewWidget
from .widgets import GlassPanel, SectionTitle


class VideoEditorPanel(QWidget):
    source_changed = Signal(str)
    options_changed = Signal(object)  # LoopOptions

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Left controls
        left = GlassPanel()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(16, 14, 16, 14)
        left_lay.setSpacing(10)
        left_lay.addWidget(SectionTitle("Video Source", "Sumber utama untuk dilooping"))

        src_row = QHBoxLayout()
        self.src_input = QLineEdit()
        self.src_input.setPlaceholderText("Pilih file video sumber...")
        browse = QPushButton("Browse")
        browse.clicked.connect(self._browse_source)
        src_row.addWidget(self.src_input, 1)
        src_row.addWidget(browse)
        left_lay.addLayout(src_row)

        left_lay.addWidget(SectionTitle("Loop Settings", "Atur mode looping & smoothing"))
        form = QFormLayout()
        form.setFormAlignment(Qt.AlignTop)
        form.setLabelAlignment(Qt.AlignRight)

        self.cb_mode = QComboBox()
        for m in LoopMode:
            self.cb_mode.addItem(m.value, m)
        self.cb_mode.setCurrentText("crossfade")

        self.sp_transition = QDoubleSpinBox()
        self.sp_transition.setRange(0.05, 30.0)
        self.sp_transition.setValue(1.5)
        self.sp_transition.setSuffix(" s")

        self.sp_blend = QDoubleSpinBox()
        self.sp_blend.setRange(0.0, 1.0)
        self.sp_blend.setSingleStep(0.05)
        self.sp_blend.setValue(1.0)

        self.sp_motion = QDoubleSpinBox()
        self.sp_motion.setRange(0.0, 4.0)
        self.sp_motion.setSingleStep(0.1)
        self.sp_motion.setValue(1.0)

        # Target duration is in MINUTES (easier than seconds)
        # 1 = 1 minute, 60 = 1 hour, 1440 = 24 hours
        self.sp_target = QSpinBox()
        self.sp_target.setRange(1, 24 * 60)  # 1 min to 24 hours
        self.sp_target.setValue(60)            # default 60 min = 1 hour
        self.sp_target.setSuffix(" menit")

        self.cb_duration_preset = QComboBox()
        self.cb_duration_preset.addItems([
            "Custom", "1 menit", "10 menit", "30 menit",
            "1 jam", "5 jam", "10 jam", "24 jam",
        ])
        self.cb_duration_preset.currentTextChanged.connect(self._apply_duration_preset)

        form.addRow("Loop Mode", self.cb_mode)
        form.addRow("Transition Length", self.sp_transition)
        form.addRow("Blend Intensity", self.sp_blend)
        form.addRow("Motion Strength", self.sp_motion)
        form.addRow("Duration Preset", self.cb_duration_preset)
        form.addRow("Target Duration", self.sp_target)
        left_lay.addLayout(form)

        # Output size + fps
        left_lay.addWidget(SectionTitle("Output", "Resolusi & framerate target"))
        size_row = QHBoxLayout()
        self.sp_width = QSpinBox()
        self.sp_width.setRange(64, 7680)
        self.sp_width.setValue(1920)
        self.sp_height = QSpinBox()
        self.sp_height.setRange(64, 4320)
        self.sp_height.setValue(1080)
        self.sp_fps = QSpinBox()
        self.sp_fps.setRange(1, 240)
        self.sp_fps.setValue(30)
        size_row.addWidget(QLabel("W:"))
        size_row.addWidget(self.sp_width)
        size_row.addWidget(QLabel("H:"))
        size_row.addWidget(self.sp_height)
        size_row.addWidget(QLabel("FPS:"))
        size_row.addWidget(self.sp_fps)
        left_lay.addLayout(size_row)

        left_lay.addStretch(1)

        # Right preview
        right = GlassPanel()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(12, 12, 12, 12)
        right_lay.setSpacing(8)
        right_lay.addWidget(SectionTitle("Realtime Preview", "Pratinjau sumber"))
        self.preview = PreviewWidget()
        right_lay.addWidget(self.preview, 1)

        layout.addWidget(left, 0)
        layout.addWidget(right, 1)

        # Wire change events
        for w in [self.cb_mode, self.sp_transition, self.sp_blend, self.sp_motion, self.sp_target, self.sp_width, self.sp_height, self.sp_fps]:
            if hasattr(w, "valueChanged"):
                w.valueChanged.connect(self._emit_options)
            elif hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self._emit_options)
        self.src_input.textChanged.connect(lambda t: self.source_changed.emit(t))

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Video", str(Path.home()),
            "Video Files (*.mp4 *.mkv *.mov *.avi *.webm *.gif);;All Files (*)",
        )
        if path:
            self.src_input.setText(path)
            self.preview.load(path)

    def _apply_duration_preset(self, text: str) -> None:
        # Values are in MINUTES
        m = {
            "1 menit": 1,
            "10 menit": 10,
            "30 menit": 30,
            "1 jam": 60,
            "5 jam": 5 * 60,
            "10 jam": 10 * 60,
            "24 jam": 24 * 60,
        }
        if text in m:
            self.sp_target.setValue(m[text])

    def _emit_options(self, *_: object) -> None:
        self.options_changed.emit(self.current_options())

    def current_options(self) -> LoopOptions:
        return LoopOptions(
            mode=LoopMode(self.cb_mode.currentData()),
            transition_seconds=float(self.sp_transition.value()),
            blend_intensity=float(self.sp_blend.value()),
            motion_strength=float(self.sp_motion.value()),
            target_duration_seconds=float(self.sp_target.value()) * 60.0,  # minutes -> seconds
            output_fps=int(self.sp_fps.value()),
            output_size=(int(self.sp_width.value()), int(self.sp_height.value())),
        )

    def source_path(self) -> str:
        return self.src_input.text().strip()
