"""Plugin manager panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.plugin_api import PluginManager

from .widgets import GlassPanel, SectionTitle


class PluginManagerPanel(QWidget):
    def __init__(self, plugins: PluginManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.plugins = plugins

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        panel = GlassPanel()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.addWidget(SectionTitle("Plugin Manager", "Plugin Python di app/plugins"))

        self.list = QListWidget()
        pl.addWidget(self.list, 1)

        btns = QHBoxLayout()
        b_reload = QPushButton("Reload Plugins")
        b_reload.clicked.connect(self.reload)
        b_open = QPushButton("Open Plugins Folder")
        b_open.clicked.connect(self._open_folder)
        btns.addWidget(b_reload); btns.addWidget(b_open)
        btns.addStretch(1)
        pl.addLayout(btns)

        layout.addWidget(panel, 1)
        self.reload()

    def reload(self) -> None:
        self.list.clear()
        # Unload existing first
        for info in list(self.plugins.plugins):
            self.plugins.unload(info.name)
        self.plugins.load_all()
        for info in self.plugins.plugins:
            QListWidgetItem(f"{info.name}  ({info.path.name})", self.list)

    def _open_folder(self) -> None:
        import os
        path = self.plugins.plugin_dir
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif os.uname().sysname == "Darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception:
            pass
