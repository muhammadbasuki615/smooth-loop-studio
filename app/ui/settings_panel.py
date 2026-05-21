"""Application settings panel."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppConfig
from app.core.ffmpeg_installer import FFmpegInstaller, InstallProgress
from app.core.ffmpeg_utils import FFmpeg, detect_gpu

from .widgets import GlassPanel, SectionTitle


class SettingsPanel(QWidget):
    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # FFmpeg section
        ff = GlassPanel()
        fl = QVBoxLayout(ff)
        fl.setContentsMargins(16, 14, 16, 14)
        fl.addWidget(SectionTitle("FFmpeg", "Engine wajib untuk render"))
        self.ff_status = QLabel()
        self.ff_path = QLineEdit()
        self.btn_install = QPushButton("Install FFmpeg")
        self.btn_install.clicked.connect(self._install_ffmpeg)
        fl.addWidget(self.ff_status)
        fl.addWidget(self.ff_path)
        fl.addWidget(self.btn_install)
        layout.addWidget(ff)

        # GPU section
        gpu = GlassPanel()
        gl = QVBoxLayout(gpu)
        gl.setContentsMargins(16, 14, 16, 14)
        gl.addWidget(SectionTitle("GPU Acceleration", "Encoder hardware yang terdeteksi"))
        self.gpu_label = QLabel("Detecting...")
        gl.addWidget(self.gpu_label)
        layout.addWidget(gpu)

        # General
        gen = GlassPanel()
        gen_l = QVBoxLayout(gen)
        gen_l.setContentsMargins(16, 14, 16, 14)
        gen_l.addWidget(SectionTitle("General", "Preferensi aplikasi"))
        form = QFormLayout()
        self.sp_threads = QSpinBox(); self.sp_threads.setRange(0, 256); self.sp_threads.setValue(0)
        self.cb_use_gpu = QCheckBox("Pakai GPU acceleration kalau tersedia")
        self.cb_use_gpu.setChecked(self.config.engine.use_gpu)
        self.cb_show_fps = QCheckBox("Tampilkan FPS monitor")
        self.cb_show_fps.setChecked(self.config.ui.show_fps_monitor)
        self.cb_show_gpu = QCheckBox("Tampilkan GPU monitor")
        self.cb_show_gpu.setChecked(self.config.ui.show_gpu_monitor)
        form.addRow("Render threads (0=auto)", self.sp_threads)
        form.addRow(self.cb_use_gpu)
        form.addRow(self.cb_show_fps)
        form.addRow(self.cb_show_gpu)
        gen_l.addLayout(form)
        layout.addWidget(gen)

        layout.addStretch(1)

        self.refresh_status()

    def refresh_status(self) -> None:
        from app.core.config import load_config
        cfg = self.config
        ffbin = FFmpeg(local_bin_dir=cfg.abs_path("ffmpeg_bin"))
        if ffbin.is_available():
            self.ff_status.setText(f"FFmpeg OK: {ffbin.binary}")
            self.ff_path.setText(ffbin.binary)
            self.btn_install.setEnabled(False)
        else:
            self.ff_status.setText("FFmpeg NOT FOUND")
            self.btn_install.setEnabled(True)

        try:
            info = detect_gpu(ffbin)
            parts = []
            if info.has_nvidia: parts.append("NVENC")
            if info.has_intel: parts.append("QSV")
            if info.has_amd: parts.append("AMF")
            self.gpu_label.setText("Available: " + (", ".join(parts) if parts else "CPU only"))
        except Exception as e:
            self.gpu_label.setText(f"GPU detection failed: {e}")

    def _install_ffmpeg(self) -> None:
        installer = FFmpegInstaller(self.config.abs_path("ffmpeg_bin").parent, progress=self._on_progress)
        try:
            path = installer.install()
            self.ff_status.setText(f"Installed: {path}")
            self.refresh_status()
        except Exception as e:
            self.ff_status.setText(f"Install failed: {e}")

    def _on_progress(self, p: InstallProgress) -> None:
        self.ff_status.setText(f"[{p.stage}] {p.percent:.1f}% {p.message}")
