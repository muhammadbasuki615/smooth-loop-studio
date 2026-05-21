"""Smooth Loop Studio - application entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_repo_root_on_path() -> None:
    """Allow running as ``python app/main.py`` without an install."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def main() -> int:
    _ensure_repo_root_on_path()

    # High-DPI before QApplication construction
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
    except Exception as e:
        print("PySide6 is required to run the GUI. Install with: pip install -r requirements.txt")
        print(f"Import error: {e}")
        return 2

    from app.core.config import load_config
    from app.core.logger import get_logger
    from app.ui.main_window import MainWindow
    from app.ui.theme import apply_dark_glass_theme

    logger = get_logger("main")
    cfg = load_config()
    logger.info(f"Starting {cfg.app.name} v{cfg.app.version}")

    app = QApplication(sys.argv)
    app.setApplicationName(cfg.app.name)
    app.setOrganizationName("SmoothLoopStudio")
    apply_dark_glass_theme(app, cfg.ui.accent_color, cfg.ui.secondary_accent)

    win = MainWindow(config=cfg)
    win.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
