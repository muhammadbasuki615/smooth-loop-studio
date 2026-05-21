"""Render queue panel."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.export_engine import RenderJob, RenderQueue, RenderStatus

from .widgets import GlassPanel, SectionTitle


class RenderQueuePanel(QWidget):
    start_requested = Signal()
    stop_requested = Signal()
    cancel_current_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        panel = GlassPanel()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.addWidget(SectionTitle("Render Queue", "Batch render dengan resume & retry"))

        ctl = QHBoxLayout()
        b_start = QPushButton("Start Queue"); b_start.setObjectName("PrimaryButton")
        b_start.clicked.connect(self.start_requested.emit)
        b_stop = QPushButton("Stop Queue")
        b_stop.clicked.connect(self.stop_requested.emit)
        b_cancel = QPushButton("Cancel Current")
        b_cancel.clicked.connect(self.cancel_current_requested.emit)
        ctl.addWidget(b_start); ctl.addWidget(b_stop); ctl.addWidget(b_cancel)
        ctl.addStretch(1)
        pl.addLayout(ctl)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Job", "Source", "Duration", "Status", "Progress"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        pl.addWidget(self.table, 1)

        layout.addWidget(panel, 1)
        self._row_for_job: dict[str, int] = {}

    def refresh(self, queue: RenderQueue) -> None:
        self.table.setRowCount(len(queue.jobs))
        self._row_for_job.clear()
        for i, job in enumerate(queue.jobs):
            self._row_for_job[job.job_id] = i
            self._set_row(i, job)

    def _set_row(self, i: int, job: RenderJob) -> None:
        self.table.setItem(i, 0, QTableWidgetItem(job.job_id))
        self.table.setItem(i, 1, QTableWidgetItem(str(job.source_video)))
        self.table.setItem(i, 2, QTableWidgetItem(f"{job.target_duration:.0f}s"))
        self.table.setItem(i, 3, QTableWidgetItem(job.status.value))
        self.table.setItem(i, 4, QTableWidgetItem(f"{job.progress:.1f}%"))

    def on_job_update(self, job: RenderJob) -> None:
        if job.job_id in self._row_for_job:
            self._set_row(self._row_for_job[job.job_id], job)
