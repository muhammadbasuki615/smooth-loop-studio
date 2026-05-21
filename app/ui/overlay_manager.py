"""Overlay manager panel."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.overlay_engine import BlendMode, OverlayLayer

from .widgets import GlassPanel, SectionTitle


_OVERLAY_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".mkv", ".webm"}


class OverlayManagerPanel(QWidget):
    layers_changed = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layers: List[OverlayLayer] = []
        self._current_index: int = -1

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # List
        left = GlassPanel()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(14, 12, 14, 12)
        ll.addWidget(SectionTitle("Overlay Layers", "Multi-layer composition"))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_row)
        ll.addWidget(self.list, 1)
        btns = QHBoxLayout()
        b_add = QPushButton("Add")
        b_add.clicked.connect(self._browse)
        b_remove = QPushButton("Remove")
        b_remove.clicked.connect(self._remove_selected)
        b_up = QPushButton("Up")
        b_up.clicked.connect(self._move_up)
        b_down = QPushButton("Down")
        b_down.clicked.connect(self._move_down)
        btns.addWidget(b_add); btns.addWidget(b_remove); btns.addWidget(b_up); btns.addWidget(b_down)
        ll.addLayout(btns)

        # Properties
        right = GlassPanel()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 12, 14, 12)
        rl.addWidget(SectionTitle("Layer Properties", ""))
        form = QFormLayout()

        self.cb_blend = QComboBox()
        for b in BlendMode:
            self.cb_blend.addItem(b.value, b)

        self.sp_opacity = QDoubleSpinBox()
        self.sp_opacity.setRange(0.0, 1.0)
        self.sp_opacity.setSingleStep(0.05)
        self.sp_opacity.setValue(1.0)

        self.le_x = QLineEdit("(W-w)/2")
        self.le_y = QLineEdit("(H-h)/2")
        self.sp_w = QSpinBox(); self.sp_w.setRange(-1, 7680); self.sp_w.setValue(-1)
        self.sp_h = QSpinBox(); self.sp_h.setRange(-1, 4320); self.sp_h.setValue(-1)
        self.sp_rot = QDoubleSpinBox(); self.sp_rot.setRange(-360, 360); self.sp_rot.setValue(0)
        self.sp_speed = QDoubleSpinBox(); self.sp_speed.setRange(0.05, 8.0); self.sp_speed.setSingleStep(0.1); self.sp_speed.setValue(1.0)

        form.addRow("Blend Mode", self.cb_blend)
        form.addRow("Opacity", self.sp_opacity)
        form.addRow("Position X", self.le_x)
        form.addRow("Position Y", self.le_y)
        form.addRow("Scale W", self.sp_w)
        form.addRow("Scale H", self.sp_h)
        form.addRow("Rotation", self.sp_rot)
        form.addRow("Speed", self.sp_speed)

        rl.addLayout(form)
        rl.addStretch(1)

        layout.addWidget(left, 1)
        layout.addWidget(right, 0)

        for w in [self.cb_blend, self.sp_opacity, self.le_x, self.le_y, self.sp_w, self.sp_h, self.sp_rot, self.sp_speed]:
            if hasattr(w, "valueChanged"):
                w.valueChanged.connect(self._apply_props_to_current)
            elif hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self._apply_props_to_current)
            elif hasattr(w, "textChanged"):
                w.textChanged.connect(self._apply_props_to_current)

    # ---------------- helpers ----------------

    def _browse(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add overlays", str(Path.home()),
            "Overlay Files (*.png *.jpg *.jpeg *.gif *.webp *.mp4 *.mov *.mkv *.webm)",
        )
        for p in paths:
            self._add_layer(Path(p))

    def _add_layer(self, path: Path) -> None:
        layer = OverlayLayer(path=path)
        self._layers.append(layer)
        QListWidgetItem(path.name, self.list)
        self.list.setCurrentRow(len(self._layers) - 1)
        self.layers_changed.emit(list(self._layers))

    def _remove_selected(self) -> None:
        row = self.list.currentRow()
        if 0 <= row < len(self._layers):
            self.list.takeItem(row)
            del self._layers[row]
            self.layers_changed.emit(list(self._layers))

    def _move_up(self) -> None:
        i = self.list.currentRow()
        if i > 0:
            self._layers[i - 1], self._layers[i] = self._layers[i], self._layers[i - 1]
            item = self.list.takeItem(i)
            self.list.insertItem(i - 1, item)
            self.list.setCurrentRow(i - 1)
            self.layers_changed.emit(list(self._layers))

    def _move_down(self) -> None:
        i = self.list.currentRow()
        if 0 <= i < len(self._layers) - 1:
            self._layers[i + 1], self._layers[i] = self._layers[i], self._layers[i + 1]
            item = self.list.takeItem(i)
            self.list.insertItem(i + 1, item)
            self.list.setCurrentRow(i + 1)
            self.layers_changed.emit(list(self._layers))

    def _on_row(self, row: int) -> None:
        self._current_index = row
        if not (0 <= row < len(self._layers)):
            return
        l = self._layers[row]
        self.cb_blend.setCurrentText(l.blend_mode.value)
        self.sp_opacity.setValue(l.opacity)
        self.le_x.setText(str(l.x))
        self.le_y.setText(str(l.y))
        self.sp_w.setValue(int(l.scale_w) if isinstance(l.scale_w, int) else -1)
        self.sp_h.setValue(int(l.scale_h) if isinstance(l.scale_h, int) else -1)
        self.sp_rot.setValue(l.rotation_deg)
        self.sp_speed.setValue(l.speed)

    def _apply_props_to_current(self, *_: object) -> None:
        i = self._current_index
        if not (0 <= i < len(self._layers)):
            return
        l = self._layers[i]
        l.blend_mode = BlendMode(self.cb_blend.currentData())
        l.opacity = float(self.sp_opacity.value())
        l.x = self.le_x.text()
        l.y = self.le_y.text()
        l.scale_w = int(self.sp_w.value())
        l.scale_h = int(self.sp_h.value())
        l.rotation_deg = float(self.sp_rot.value())
        l.speed = float(self.sp_speed.value())
        self.layers_changed.emit(list(self._layers))

    def current_layers(self) -> List[OverlayLayer]:
        return list(self._layers)
