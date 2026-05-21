"""Export panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.export_engine import ExportSettings
from app.core.presets import get_builtin_presets

from .widgets import GlassPanel, SectionTitle


class ExportPanel(QWidget):
    start_render_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._presets = get_builtin_presets()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        panel = GlassPanel()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.addWidget(SectionTitle("Export", "Pengaturan render & GPU"))

        form = QFormLayout()

        self.cb_preset = QComboBox()
        self.cb_preset.addItem("Custom", None)
        for key, p in self._presets.items():
            self.cb_preset.addItem(p.name, key)
        self.cb_preset.currentIndexChanged.connect(self._apply_preset)

        self.cb_codec = QComboBox()
        self.cb_codec.addItems(["h264", "h265", "av1", "vp9"])
        self.cb_container = QComboBox()
        self.cb_container.addItems(["mp4", "mkv", "mov", "avi", "webm"])
        self.cb_gpu = QComboBox()
        self.cb_gpu.addItems(["auto", "nvenc", "qsv", "amf", "cpu"])

        self.sp_w = QSpinBox(); self.sp_w.setRange(64, 7680); self.sp_w.setValue(1920)
        self.sp_h = QSpinBox(); self.sp_h.setRange(64, 4320); self.sp_h.setValue(1080)
        self.sp_fps = QSpinBox(); self.sp_fps.setRange(1, 240); self.sp_fps.setValue(30)
        self.le_bitrate = QLineEdit("8M")

        form.addRow("Preset", self.cb_preset)
        form.addRow("Container", self.cb_container)
        form.addRow("Codec", self.cb_codec)
        form.addRow("GPU", self.cb_gpu)
        form.addRow("Width", self.sp_w)
        form.addRow("Height", self.sp_h)
        form.addRow("FPS", self.sp_fps)
        form.addRow("Bitrate", self.le_bitrate)
        pl.addLayout(form)

        out_row = QHBoxLayout()
        self.le_out = QLineEdit()
        self.le_out.setPlaceholderText("Pilih lokasi output...")
        b_browse = QPushButton("Browse")
        b_browse.clicked.connect(self._browse_out)
        out_row.addWidget(QLabel("Output"))
        out_row.addWidget(self.le_out, 1)
        out_row.addWidget(b_browse)
        pl.addLayout(out_row)

        action_row = QHBoxLayout()
        self.btn_render = QPushButton("Start Render")
        self.btn_render.setObjectName("PrimaryButton")
        self.btn_render.clicked.connect(self.start_render_requested.emit)
        action_row.addStretch(1)
        action_row.addWidget(self.btn_render)
        pl.addLayout(action_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label = QLabel("Idle")
        self.status_label.setObjectName("Muted")
        pl.addWidget(self.progress)
        pl.addWidget(self.status_label)

        layout.addWidget(panel)
        layout.addStretch(1)

    def _apply_preset(self) -> None:
        key = self.cb_preset.currentData()
        if not key:
            return
        p = self._presets[key]
        self.cb_codec.setCurrentText(p.codec)
        self.cb_container.setCurrentText(p.container)
        self.sp_w.setValue(p.width)
        self.sp_h.setValue(p.height)
        self.sp_fps.setValue(p.fps)
        self.le_bitrate.setText(p.bitrate)

    def _browse_out(self) -> None:
        ext = self.cb_container.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save output", str(Path.home() / f"smooth_loop.{ext}"),
            f"Video Files (*.{ext})",
        )
        if path:
            self.le_out.setText(path)

    def current_settings(self) -> ExportSettings:
        gpu_pref = self.cb_gpu.currentText()
        use_gpu = gpu_pref != "cpu"
        encoder = None
        if gpu_pref not in ("auto", "cpu"):
            codec = self.cb_codec.currentText()
            mapping = {
                "nvenc": {"h264": "h264_nvenc", "h265": "hevc_nvenc", "av1": "av1_nvenc"},
                "qsv": {"h264": "h264_qsv", "h265": "hevc_qsv", "av1": "av1_qsv"},
                "amf": {"h264": "h264_amf", "h265": "hevc_amf"},
            }
            encoder = mapping.get(gpu_pref, {}).get(codec)
        return ExportSettings(
            output_path=Path(self.le_out.text() or "output.mp4"),
            container=self.cb_container.currentText(),
            codec=self.cb_codec.currentText(),
            width=int(self.sp_w.value()),
            height=int(self.sp_h.value()),
            fps=int(self.sp_fps.value()),
            bitrate=self.le_bitrate.text().strip() or "8M",
            use_gpu=use_gpu,
            encoder_override=encoder,
        )

    def set_progress(self, percent: float, status: str) -> None:
        self.progress.setValue(int(percent))
        self.status_label.setText(status)
