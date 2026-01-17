"""Sidebar with album art and track metadata."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
)

from player.core.metadata import Track
from player.theme.lainchan import BG_PRIMARY, TEXT_NORMAL, TEXT_MUTED, ACCENT


class Sidebar(QWidget):
    """Sidebar displaying album art and current track info."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(280)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Album art
        self._art_label = QLabel()
        self._art_label.setFixedSize(248, 248)
        self._art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._art_label.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_PRIMARY};
                border: 1px solid {ACCENT};
            }}
        """)
        self._set_placeholder_art()
        layout.addWidget(self._art_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {ACCENT}; max-height: 2px;")
        layout.addWidget(separator)

        # Album title
        self._album_label = QLabel("")
        self._album_label.setStyleSheet(f"""
            color: {TEXT_NORMAL};
            font-size: 14px;
            font-weight: bold;
        """)
        self._album_label.setWordWrap(True)
        layout.addWidget(self._album_label)

        # Year
        self._year_label = QLabel("")
        self._year_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self._year_label)

        # Format info
        self._format_label = QLabel("")
        self._format_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self._format_label)

        # Bitrate / sample info
        self._quality_label = QLabel("")
        self._quality_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self._quality_label)

        # Push everything up
        layout.addStretch()

        # Right border accent
        self.setStyleSheet(self.styleSheet() + f"""
            Sidebar {{
                border-right: 2px solid {ACCENT};
            }}
        """)

    def _set_placeholder_art(self):
        """Set placeholder when no album art available."""
        self._art_label.setText("No Art")
        self._art_label.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_PRIMARY};
                border: 1px solid {ACCENT};
                color: {TEXT_MUTED};
                font-size: 14px;
            }}
        """)

    def set_track(self, track: Track):
        """Update sidebar with track information."""
        # Album art
        if track.album_art:
            pixmap = QPixmap()
            pixmap.loadFromData(track.album_art)
            scaled = pixmap.scaled(
                248, 248,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._art_label.setPixmap(scaled)
            self._art_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {BG_PRIMARY};
                    border: 1px solid {ACCENT};
                }}
            """)
        else:
            self._set_placeholder_art()

        # Metadata
        self._album_label.setText(track.album if track.album != "Unknown" else "")
        self._year_label.setText(track.year if track.year else "")
        self._format_label.setText(track.codec if track.codec != "Unknown" else "")

        # Quality info
        quality_parts = []
        if track.sample_rate > 0:
            sr = track.sample_rate / 1000
            if sr == int(sr):
                quality_parts.append(f"{int(sr)} kHz")
            else:
                quality_parts.append(f"{sr:.1f} kHz")
        if track.bit_depth > 0:
            quality_parts.append(f"{track.bit_depth}-bit")
        if track.bitrate > 0:
            quality_parts.append(f"{track.bitrate} kbps")

        self._quality_label.setText(" / ".join(quality_parts))

    def clear(self):
        """Clear all track information."""
        self._set_placeholder_art()
        self._album_label.setText("")
        self._year_label.setText("")
        self._format_label.setText("")
        self._quality_label.setText("")
