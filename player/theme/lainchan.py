"""Detective dark theme constants and Qt stylesheet."""

# Backgrounds (darkest to lightest)
BG_PRIMARY = "#0a0a0a"
BG_SECONDARY = "#0f0f0f"
BG_TERTIARY = "#1a1a1a"

# Text
TEXT_NORMAL = "#c0c0c0"
TEXT_MUTED = "#909090"
TEXT_DIM = "#606060"

# Accent (muted green)
ACCENT = "#4a7c59"
ACCENT_DIM = "#2d4a38"

# Borders
BORDER = "#2a2a2a"

# Selection
SELECTION_BG = ACCENT
SELECTION_TEXT = "#ffffff"


def get_stylesheet() -> str:
    """Return the complete Qt stylesheet for the detective theme."""
    return f"""
        * {{
            font-family: "IBM Plex Mono", "Consolas", "Monaco", monospace;
            font-size: 13px;
            border-radius: 0px;
        }}

        QMainWindow {{
            background-color: {BG_PRIMARY};
        }}

        QWidget {{
            background-color: {BG_PRIMARY};
            color: {TEXT_NORMAL};
        }}

        QLabel {{
            background-color: transparent;
            color: {TEXT_NORMAL};
        }}

        QLabel[muted="true"] {{
            color: {TEXT_MUTED};
        }}

        QLabel[dim="true"] {{
            color: {TEXT_DIM};
        }}

        QPushButton {{
            background-color: {BG_SECONDARY};
            color: {TEXT_NORMAL};
            border: 1px solid {BORDER};
            padding: 6px 12px;
            min-width: 30px;
        }}

        QPushButton:hover {{
            background-color: {BG_TERTIARY};
            border-color: {ACCENT_DIM};
        }}

        QPushButton:pressed {{
            background-color: {ACCENT_DIM};
        }}

        QPushButton:disabled {{
            color: {TEXT_DIM};
            background-color: {BG_PRIMARY};
        }}

        QSlider::groove:horizontal {{
            background-color: {BORDER};
            height: 4px;
        }}

        QSlider::handle:horizontal {{
            background-color: {TEXT_NORMAL};
            width: 12px;
            height: 12px;
            margin: -4px 0;
        }}

        QSlider::handle:horizontal:hover {{
            background-color: {ACCENT};
        }}

        QSlider::sub-page:horizontal {{
            background-color: {ACCENT};
        }}

        QTableWidget {{
            background-color: {BG_SECONDARY};
            alternate-background-color: {BG_PRIMARY};
            color: {TEXT_NORMAL};
            border: none;
            gridline-color: {BORDER};
            selection-background-color: {BG_TERTIARY};
            selection-color: {TEXT_NORMAL};
            outline: none;
        }}

        QTableWidget::item {{
            padding: 4px 8px;
            border: none;
        }}

        QTableWidget::item:selected {{
            background-color: {BG_TERTIARY};
        }}

        QTableWidget::item:focus {{
            outline: none;
        }}

        QHeaderView::section {{
            background-color: {BG_PRIMARY};
            color: {TEXT_MUTED};
            border: none;
            border-bottom: 1px solid {BORDER};
            padding: 6px 8px;
            font-weight: bold;
        }}

        QHeaderView::section:hover {{
            color: {TEXT_NORMAL};
        }}

        QScrollBar:vertical {{
            background-color: {BG_PRIMARY};
            width: 10px;
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background-color: {BORDER};
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {TEXT_DIM};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background-color: {BG_PRIMARY};
            height: 10px;
            border: none;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {BORDER};
            min-width: 30px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {TEXT_DIM};
        }}

        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        QLineEdit {{
            background-color: {BG_SECONDARY};
            color: {TEXT_NORMAL};
            border: 1px solid {BORDER};
            padding: 6px 8px;
            selection-background-color: {SELECTION_BG};
            selection-color: {SELECTION_TEXT};
        }}

        QLineEdit:focus {{
            border-color: {ACCENT};
        }}

        QMenuBar {{
            background-color: {BG_PRIMARY};
            color: {TEXT_NORMAL};
            border-bottom: 1px solid {BORDER};
        }}

        QMenuBar::item {{
            padding: 4px 8px;
        }}

        QMenuBar::item:selected {{
            background-color: {BG_TERTIARY};
        }}

        QMenu {{
            background-color: {BG_SECONDARY};
            color: {TEXT_NORMAL};
            border: 1px solid {BORDER};
        }}

        QMenu::item {{
            padding: 6px 20px;
        }}

        QMenu::item:selected {{
            background-color: {ACCENT_DIM};
        }}

        QTabBar::tab {{
            background-color: {BG_PRIMARY};
            color: {TEXT_MUTED};
            padding: 8px 16px;
            border: none;
            border-bottom: 2px solid transparent;
        }}

        QTabBar::tab:selected {{
            color: {TEXT_NORMAL};
            border-bottom: 2px solid {ACCENT};
        }}

        QTabBar::tab:hover {{
            color: {TEXT_NORMAL};
        }}

        QTabWidget::pane {{
            border: none;
            background-color: {BG_SECONDARY};
        }}

        QToolTip {{
            background-color: {BG_TERTIARY};
            color: {TEXT_NORMAL};
            border: 1px solid {BORDER};
            padding: 4px;
        }}
    """
