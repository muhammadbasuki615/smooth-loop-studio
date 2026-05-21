"""AI tools panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

from app.ai import (
    BeatSync,
    Denoiser,
    FrameInterpolator,
    SceneDetector,
    Upscaler,
)

from .widgets import GlassPanel, SectionTitle


class AIToolsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Interpolation
        ip = GlassPanel()
        il = QVBoxLayout(ip)
        il.setContentsMargins(16, 14, 16, 14)
        il.addWidget(SectionTitle("Frame Interpolation", "Naikkan FPS untuk gerakan lebih halus"))
        self.le_ip_src = QLineEdit()
        self.le_ip_src.setPlaceholderText("Source video...")
        b_browse_ip = QPushButton("Browse"); b_browse_ip.clicked.connect(lambda: self._browse_into(self.le_ip_src))
        self.sp_target_fps = QSpinBox(); self.sp_target_fps.setRange(24, 240); self.sp_target_fps.setValue(60)
        b_run_ip = QPushButton("Interpolate")
        b_run_ip.clicked.connect(self._run_interp)
        row = QHBoxLayout(); row.addWidget(self.le_ip_src, 1); row.addWidget(b_browse_ip)
        il.addLayout(row)
        form = QFormLayout(); form.addRow("Target FPS", self.sp_target_fps); il.addLayout(form)
        il.addWidget(b_run_ip)
        layout.addWidget(ip)

        # Upscale
        up = GlassPanel()
        ul = QVBoxLayout(up)
        ul.setContentsMargins(16, 14, 16, 14)
        ul.addWidget(SectionTitle("Upscale", "Perbesar resolusi"))
        self.le_up_src = QLineEdit()
        b_browse_up = QPushButton("Browse"); b_browse_up.clicked.connect(lambda: self._browse_into(self.le_up_src))
        self.sp_scale = QSpinBox(); self.sp_scale.setRange(2, 4); self.sp_scale.setValue(2)
        b_run_up = QPushButton("Upscale"); b_run_up.clicked.connect(self._run_upscale)
        row2 = QHBoxLayout(); row2.addWidget(self.le_up_src, 1); row2.addWidget(b_browse_up)
        ul.addLayout(row2)
        f2 = QFormLayout(); f2.addRow("Scale", self.sp_scale); ul.addLayout(f2)
        ul.addWidget(b_run_up)
        layout.addWidget(up)

        # Denoise
        dn = GlassPanel()
        dl = QVBoxLayout(dn)
        dl.setContentsMargins(16, 14, 16, 14)
        dl.addWidget(SectionTitle("Denoise", "Hilangkan noise pada video"))
        self.le_dn_src = QLineEdit()
        b_browse_dn = QPushButton("Browse"); b_browse_dn.clicked.connect(lambda: self._browse_into(self.le_dn_src))
        b_run_dn = QPushButton("Denoise"); b_run_dn.clicked.connect(self._run_denoise)
        row3 = QHBoxLayout(); row3.addWidget(self.le_dn_src, 1); row3.addWidget(b_browse_dn)
        dl.addLayout(row3); dl.addWidget(b_run_dn)
        layout.addWidget(dn)

        # Scene detect & beat sync
        sd = GlassPanel()
        sl = QVBoxLayout(sd)
        sl.setContentsMargins(16, 14, 16, 14)
        sl.addWidget(SectionTitle("Analysis", "Scene & beat detection"))
        self.scene_label = QLabel("No analysis yet")
        b_scene = QPushButton("Detect Scenes"); b_scene.clicked.connect(self._scene_detect)
        sl.addWidget(b_scene); sl.addWidget(self.scene_label)
        self.le_audio = QLineEdit()
        self.le_audio.setPlaceholderText("Audio file untuk beat detection...")
        b_audio = QPushButton("Browse"); b_audio.clicked.connect(lambda: self._browse_into(self.le_audio, audio=True))
        row4 = QHBoxLayout(); row4.addWidget(self.le_audio, 1); row4.addWidget(b_audio)
        sl.addLayout(row4)
        b_beat = QPushButton("Detect Beats"); b_beat.clicked.connect(self._beat_detect)
        self.beat_label = QLabel("No beats yet")
        sl.addWidget(b_beat); sl.addWidget(self.beat_label)
        layout.addWidget(sd)

        self.status = QLabel("Ready")
        self.status.setObjectName("Muted")
        layout.addWidget(self.status)
        layout.addStretch(1)

    def _browse_into(self, line: QLineEdit, audio: bool = False) -> None:
        f = (
            "Audio Files (*.mp3 *.wav *.flac *.aac *.ogg *.m4a)"
            if audio
            else "Video Files (*.mp4 *.mkv *.mov *.webm)"
        )
        path, _ = QFileDialog.getOpenFileName(self, "Select", str(Path.home()), f)
        if path:
            line.setText(path)

    def _run_interp(self) -> None:
        src = self.le_ip_src.text().strip()
        if not src:
            self.status.setText("Source kosong"); return
        out = str(Path(src).with_name(Path(src).stem + "_ai_fps.mp4"))
        try:
            FrameInterpolator().interpolate(src, out, int(self.sp_target_fps.value()))
            self.status.setText(f"Saved: {out}")
        except Exception as e:
            self.status.setText(f"Error: {e}")

    def _run_upscale(self) -> None:
        src = self.le_up_src.text().strip()
        if not src:
            self.status.setText("Source kosong"); return
        out = str(Path(src).with_name(Path(src).stem + "_upscaled.mp4"))
        try:
            Upscaler().upscale(src, out, int(self.sp_scale.value()))
            self.status.setText(f"Saved: {out}")
        except Exception as e:
            self.status.setText(f"Error: {e}")

    def _run_denoise(self) -> None:
        src = self.le_dn_src.text().strip()
        if not src:
            self.status.setText("Source kosong"); return
        out = str(Path(src).with_name(Path(src).stem + "_denoised.mp4"))
        try:
            Denoiser().denoise(src, out)
            self.status.setText(f"Saved: {out}")
        except Exception as e:
            self.status.setText(f"Error: {e}")

    def _scene_detect(self) -> None:
        src = self.le_dn_src.text().strip() or self.le_ip_src.text().strip() or self.le_up_src.text().strip()
        if not src:
            self.scene_label.setText("Pilih video dulu"); return
        scenes = SceneDetector().detect(src)
        self.scene_label.setText(f"Detected {len(scenes)} scenes")

    def _beat_detect(self) -> None:
        src = self.le_audio.text().strip()
        if not src:
            self.beat_label.setText("Pilih audio dulu"); return
        tempo, beats = BeatSync().detect_beats(src)
        self.beat_label.setText(f"Tempo: {tempo:.1f} BPM, {len(beats)} beats")
