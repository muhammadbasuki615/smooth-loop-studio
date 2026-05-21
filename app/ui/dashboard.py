"""Dashboard panel with quick actions and performance monitors."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.performance import PerformanceMonitor

from .widgets import GlassPanel, ProgressCard, SectionTitle, StatPill


class DashboardPanel(QWidget):
    """Welcome/overview panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.perf = PerformanceMonitor()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("Smooth Loop Studio")
        title.setObjectName("H1")
        subtitle = QLabel("Buat video looping super halus — siap untuk live stream, ASMR, ambience, wallpaper.")
        subtitle.setObjectName("Muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Quick action grid
        grid = QGridLayout()
        grid.setSpacing(12)
        cards = [
            ("Loop Project", "Buat seamless loop dari video pendek.", "primary"),
            ("Long Render", "Render hingga 24 jam tanpa patah.", ""),
            ("Audio Mixer", "Layer banyak musik & replace audio asli.", ""),
            ("Overlay Manager", "PNG, GIF, video overlay + blend mode.", ""),
            ("Export Queue", "Batch render dengan GPU acceleration.", ""),
            ("AI Tools", "Frame interpolation, upscale, denoise.", ""),
        ]
        for i, (t, d, kind) in enumerate(cards):
            card = self._make_card(t, d, primary=(kind == "primary"))
            grid.addWidget(card, i // 3, i % 3)
        layout.addLayout(grid)

        # Performance monitors
        perf_panel = GlassPanel()
        pl = QVBoxLayout(perf_panel)
        pl.addWidget(SectionTitle("Performance", "Realtime monitoring"))
        row = QHBoxLayout()
        self.pill_cpu = StatPill("CPU", "—")
        self.pill_ram = StatPill("RAM", "—")
        self.pill_gpu = StatPill("GPU", "—")
        self.pill_fps = StatPill("Preview FPS", "—")
        for p in (self.pill_cpu, self.pill_ram, self.pill_gpu, self.pill_fps):
            row.addWidget(p)
        row.addStretch(1)
        pl.addLayout(row)
        layout.addWidget(perf_panel)

        # Render status card
        self.render_card = ProgressCard("Render Status")
        layout.addWidget(self.render_card)

        layout.addStretch(1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_perf)
        self._timer.start(1000)

    def _make_card(self, title: str, desc: str, primary: bool = False) -> QFrame:
        card = GlassPanel()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)
        t = QLabel(title)
        t.setObjectName("H2")
        d = QLabel(desc)
        d.setObjectName("Muted")
        d.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(d)
        lay.addStretch(1)
        btn = QPushButton("Open")
        if primary:
            btn.setObjectName("PrimaryButton")
        btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        lay.addWidget(btn, 0, Qt.AlignRight)
        return card

    def _refresh_perf(self) -> None:
        snap = self.perf.snapshot()
        self.pill_cpu.set_value(f"{snap.cpu_percent:.0f}%")
        if snap.ram_total_mb > 0:
            self.pill_ram.set_value(
                f"{snap.ram_used_mb/1024:.1f}/{snap.ram_total_mb/1024:.1f} GB"
            )
        if snap.gpu_name:
            self.pill_gpu.set_value(f"{snap.gpu_name} {snap.gpu_percent:.0f}%")
        self.pill_fps.set_value(f"{snap.fps:.1f}")

    def set_render_progress(self, percent: float, text: str) -> None:
        self.render_card.set_progress(percent, text)
