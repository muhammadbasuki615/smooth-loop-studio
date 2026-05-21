"""Dark glassmorphism QSS stylesheet."""

from __future__ import annotations


def build_stylesheet(accent: str = "#00E5FF", secondary: str = "#FF4ECD") -> str:
    return f"""
* {{
    color: #E6F0FA;
    font-family: "Segoe UI", "Inter", "SF Pro Text", Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: #0B0F1A;
}}

QWidget#GlassPanel {{
    background-color: rgba(20, 24, 38, 200);
    border: 1px solid rgba(255, 255, 255, 18);
    border-radius: 14px;
}}

QWidget#TitleBar {{
    background-color: rgba(8, 11, 22, 220);
    border-bottom: 1px solid rgba(255, 255, 255, 18);
}}

QLabel#H1 {{
    font-size: 22px;
    font-weight: 700;
    color: #FFFFFF;
}}
QLabel#H2 {{
    font-size: 16px;
    font-weight: 600;
    color: #FFFFFF;
}}
QLabel#Muted {{
    color: #8A95B0;
}}
QLabel#Accent {{
    color: {accent};
    font-weight: 600;
}}

QPushButton {{
    background-color: rgba(255, 255, 255, 14);
    color: #E6F0FA;
    border: 1px solid rgba(255, 255, 255, 24);
    border-radius: 10px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: rgba(255, 255, 255, 26);
    border: 1px solid {accent};
}}
QPushButton:pressed {{
    background-color: rgba(255, 255, 255, 8);
}}
QPushButton:disabled {{
    color: #5D6478;
    background-color: rgba(255, 255, 255, 8);
}}

QPushButton#PrimaryButton {{
    background-color: {accent};
    color: #0A0F1A;
    border: 1px solid {accent};
}}
QPushButton#PrimaryButton:hover {{
    background-color: #29F0FF;
}}
QPushButton#SecondaryButton {{
    background-color: {secondary};
    color: #0A0F1A;
    border: 1px solid {secondary};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background-color: rgba(255, 255, 255, 10);
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: {accent};
    selection-color: #0A0F1A;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {accent};
}}

QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: #11162A;
    border: 1px solid rgba(255, 255, 255, 30);
    selection-background-color: {accent};
    selection-color: #0A0F1A;
}}

QSlider::groove:horizontal {{
    height: 5px;
    background: rgba(255, 255, 255, 20);
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {accent};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 3px;
}}

QProgressBar {{
    background: rgba(255, 255, 255, 12);
    border: 1px solid rgba(255, 255, 255, 22);
    border-radius: 8px;
    text-align: center;
    color: #FFFFFF;
    padding: 1px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {secondary});
    border-radius: 7px;
}}

QListWidget, QTreeView, QTableView {{
    background-color: rgba(255, 255, 255, 5);
    border: 1px solid rgba(255, 255, 255, 18);
    border-radius: 10px;
    alternate-background-color: rgba(255, 255, 255, 10);
}}

QHeaderView::section {{
    background-color: rgba(255, 255, 255, 8);
    color: #C7D1E5;
    border: none;
    padding: 6px 8px;
}}

QTabWidget::pane {{
    border: 1px solid rgba(255, 255, 255, 18);
    border-radius: 12px;
    top: -1px;
}}
QTabBar::tab {{
    background-color: rgba(255, 255, 255, 6);
    color: #C7D1E5;
    padding: 8px 18px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(0, 229, 255, 80),
        stop:1 rgba(0, 229, 255, 30));
    color: #FFFFFF;
}}
QTabBar::tab:hover {{
    background-color: rgba(255, 255, 255, 16);
}}

QScrollBar:vertical, QScrollBar:horizontal {{
    background: rgba(255, 255, 255, 5);
    border: none;
    width: 10px;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 40);
    border-radius: 5px;
    min-height: 30px;
    min-width: 30px;
}}
QScrollBar::handle:hover {{
    background: {accent};
}}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}

QToolTip {{
    background-color: #11162A;
    color: #FFFFFF;
    border: 1px solid {accent};
    padding: 6px 10px;
    border-radius: 6px;
}}

QMenuBar {{
    background-color: #0B0F1A;
}}
QMenuBar::item:selected {{ background-color: rgba(255, 255, 255, 14); }}
QMenu {{
    background-color: #11162A;
    border: 1px solid rgba(255, 255, 255, 22);
    border-radius: 8px;
}}
QMenu::item:selected {{ background-color: {accent}; color: #0A0F1A; }}

QStatusBar {{
    background-color: rgba(8, 11, 22, 220);
    border-top: 1px solid rgba(255, 255, 255, 18);
}}
"""


def apply_dark_glass_theme(app, accent: str = "#00E5FF", secondary: str = "#FF4ECD") -> None:
    """Apply the global dark glassmorphism stylesheet."""
    app.setStyleSheet(build_stylesheet(accent=accent, secondary=secondary))
