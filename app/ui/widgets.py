"""Reusable custom widgets."""

from __future__ import annotations

from typing import Callable, Iterable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class GlassPanel(QFrame):
    """Rounded translucent panel used throughout the UI."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setFrameShape(QFrame.NoFrame)


class SectionTitle(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        h = QLabel(title)
        h.setObjectName("H2")
        lay.addWidget(h)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("Muted")
            lay.addWidget(sub)


class DropList(QListWidget):
    """QListWidget that accepts drag-and-drop file paths."""

    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None, allowed_suffixes: Optional[Iterable[str]] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.allowed_suffixes = {s.lower() for s in (allowed_suffixes or [])}
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e: QDragEnterEvent) -> None:  # type: ignore[override]
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e: QDropEvent) -> None:
        if not e.mimeData().hasUrls():
            super().dropEvent(e)
            return
        paths: list[str] = []
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if not p:
                continue
            if self.allowed_suffixes:
                if p.lower().rsplit(".", 1)[-1] not in {s.lstrip(".") for s in self.allowed_suffixes}:
                    continue
            paths.append(p)
        if paths:
            self.files_dropped.emit(paths)
        e.acceptProposedAction()


class StatPill(QWidget):
    """Small label+value pill widget for status info."""

    def __init__(self, label: str, value: str = "—", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(8)
        self.lbl = QLabel(label)
        self.lbl.setObjectName("Muted")
        self.val = QLabel(value)
        self.val.setObjectName("Accent")
        lay.addWidget(self.lbl)
        lay.addWidget(self.val)
        self.setStyleSheet(
            "QWidget { background-color: rgba(255,255,255,10); border-radius: 8px; }"
        )
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

    def set_value(self, v: str) -> None:
        self.val.setText(v)


class IconButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None, primary: bool = False) -> None:
        super().__init__(text, parent)
        if primary:
            self.setObjectName("PrimaryButton")


class ProgressCard(QFrame):
    """Progress card with title, bar, and status text."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(6)
        self.title = QLabel(title)
        self.title.setObjectName("H2")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.status = QLabel("Idle")
        self.status.setObjectName("Muted")
        lay.addWidget(self.title)
        lay.addWidget(self.bar)
        lay.addWidget(self.status)

    def set_progress(self, percent: float, text: str = "") -> None:
        self.bar.setValue(int(percent))
        if text:
            self.status.setText(text)
