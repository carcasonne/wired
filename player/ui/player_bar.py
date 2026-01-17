# -*- coding: utf-8 -*-
"""Bottom player bar with playback controls."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QSlider,
    QLabel,
    QFrame,
)

from player.theme.lainchan import (
    BG_PRIMARY, BG_SECONDARY, BG_TERTIARY,
    TEXT_NORMAL, TEXT_MUTED, TEXT_DIM,
    ACCENT, ACCENT_DIM, BORDER,
)


class PlayerBar(QWidget):
    """Bottom playback control bar."""

    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    seek_requested = pyqtSignal(float)  # 0.0 to 1.0
    volume_changed = pyqtSignal(int)  # 0-100

    def __init__(self):
        super().__init__()
        self._is_playing = False
        self._seeking = False
        self._duration_ms = 0
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(120)
        self.setStyleSheet(f"background-color: {BG_PRIMARY};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top accent border (2px)
        accent_bar = QFrame()
        accent_bar.setFixedHeight(2)
        accent_bar.setStyleSheet(f"background-color: {ACCENT};")
        main_layout.addWidget(accent_bar)

        # Content area
        content = QWidget()
        content.setStyleSheet(f"background-color: {BG_PRIMARY};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(8)

        # Row 1: Track info with labels
        info_grid = QGridLayout()
        info_grid.setContentsMargins(0, 0, 0, 0)
        info_grid.setHorizontalSpacing(12)
        info_grid.setVerticalSpacing(2)

        # Labels column
        track_label = QLabel("TRACK")
        track_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        info_grid.addWidget(track_label, 0, 0)

        artist_label = QLabel("ARTIST")
        artist_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        info_grid.addWidget(artist_label, 1, 0)

        source_label = QLabel("SOURCE")
        source_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        info_grid.addWidget(source_label, 2, 0)

        # Values column
        self._track_value = QLabel("—")
        self._track_value.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 13px;")
        info_grid.addWidget(self._track_value, 0, 1)

        self._artist_value = QLabel("—")
        self._artist_value.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 13px;")
        info_grid.addWidget(self._artist_value, 1, 1)

        self._source_value = QLabel("—")
        self._source_value.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        info_grid.addWidget(self._source_value, 2, 1)

        # Make values column stretch
        info_grid.setColumnStretch(1, 1)

        content_layout.addLayout(info_grid)

        # Row 2: Seek bar with position label
        seek_row = QHBoxLayout()
        seek_row.setSpacing(12)

        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background-color: {BORDER};
                height: 4px;
            }}
            QSlider::handle:horizontal {{
                background-color: {TEXT_NORMAL};
                width: 8px;
                height: 8px;
                margin: -2px 0;
            }}
            QSlider::handle:horizontal:hover {{
                background-color: {ACCENT};
            }}
            QSlider::sub-page:horizontal {{
                background-color: {ACCENT};
            }}
        """)
        self._seek_slider.sliderPressed.connect(self._on_seek_start)
        self._seek_slider.sliderReleased.connect(self._on_seek_end)
        self._seek_slider.sliderMoved.connect(self._on_seek_moved)
        seek_row.addWidget(self._seek_slider, 1)

        position_label = QLabel("POSITION")
        position_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        seek_row.addWidget(position_label)

        self._time_label = QLabel("0:00/0:00")
        self._time_label.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 11px; min-width: 70px;")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        seek_row.addWidget(self._time_label)

        content_layout.addLayout(seek_row)

        # Row 3: Transport controls + Level
        controls_row = QHBoxLayout()
        controls_row.setSpacing(16)

        # Transport label
        transport_label = QLabel("TRANSPORT")
        transport_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        controls_row.addWidget(transport_label)

        # Transport buttons - text only, no backgrounds
        self._prev_btn = QPushButton("|<")
        self._play_btn = QPushButton(">")
        self._next_btn = QPushButton(">|")

        button_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_NORMAL};
                border: 1px solid {BORDER};
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
                min-width: 28px;
            }}
            QPushButton:hover {{
                border-color: {ACCENT};
                color: {ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {ACCENT_DIM};
            }}
        """

        for btn in [self._prev_btn, self._play_btn, self._next_btn]:
            btn.setStyleSheet(button_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._prev_btn.clicked.connect(self.prev_clicked.emit)
        self._play_btn.clicked.connect(self._on_play_clicked)
        self._next_btn.clicked.connect(self.next_clicked.emit)

        controls_row.addWidget(self._prev_btn)
        controls_row.addWidget(self._play_btn)
        controls_row.addWidget(self._next_btn)

        controls_row.addStretch()

        # Level (volume) control
        level_label = QLabel("LEVEL")
        level_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        controls_row.addWidget(level_label)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(75)
        self._volume_slider.setFixedWidth(100)
        self._volume_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background-color: {BORDER};
                height: 4px;
            }}
            QSlider::handle:horizontal {{
                background-color: {TEXT_NORMAL};
                width: 8px;
                height: 8px;
                margin: -2px 0;
            }}
            QSlider::handle:horizontal:hover {{
                background-color: {ACCENT};
            }}
            QSlider::sub-page:horizontal {{
                background-color: {ACCENT_DIM};
            }}
        """)
        self._volume_slider.valueChanged.connect(self.volume_changed.emit)
        controls_row.addWidget(self._volume_slider)

        self._volume_label = QLabel("75%")
        self._volume_label.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 11px; min-width: 32px;")
        self._volume_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._volume_slider.valueChanged.connect(
            lambda v: self._volume_label.setText(f"{v}%")
        )
        controls_row.addWidget(self._volume_label)

        content_layout.addLayout(controls_row)

        main_layout.addWidget(content, 1)

    def _on_play_clicked(self):
        if self._is_playing:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()

    def _on_seek_start(self):
        self._seeking = True

    def _on_seek_end(self):
        self._seeking = False
        position = self._seek_slider.value() / 1000.0
        self.seek_requested.emit(position)

    def _on_seek_moved(self, value: int):
        if self._seeking and self._duration_ms > 0:
            current_ms = int((value / 1000.0) * self._duration_ms)
            self._time_label.setText(
                f"{_format_time(current_ms)}/{_format_time(self._duration_ms)}"
            )

    def set_playing(self, playing: bool):
        """Update play/pause button state."""
        self._is_playing = playing
        self._play_btn.setText("||" if playing else ">")

    def set_position(self, position: float, current_ms: int = 0):
        """Update seek bar position (0.0 to 1.0)."""
        if not self._seeking:
            self._seek_slider.setValue(int(position * 1000))
            if self._duration_ms > 0:
                self._time_label.setText(
                    f"{_format_time(current_ms)}/{_format_time(self._duration_ms)}"
                )

    def set_duration(self, duration_ms: int):
        """Set track duration for time display."""
        self._duration_ms = duration_ms

    def set_track_info(self, title: str, artist: str, album: str, year: str,
                       codec: str, sample_info: str, bitrate: str):
        """Update track info display."""
        self._track_value.setText(title if title else "—")
        self._artist_value.setText(artist if artist else "—")

        # Build source line: Album (Year) | Codec | Sample Info | Bitrate
        source_parts = []
        if album:
            album_text = album
            if year:
                album_text += f" ({year})"
            source_parts.append(album_text)
        if codec:
            source_parts.append(codec.upper())
        if sample_info:
            source_parts.append(sample_info.upper())
        if bitrate:
            source_parts.append(bitrate.upper())

        self._source_value.setText("  │  ".join(source_parts) if source_parts else "—")

    def clear_track_info(self):
        """Clear track info display."""
        self._track_value.setText("—")
        self._artist_value.setText("—")
        self._source_value.setText("—")
        self._time_label.setText("0:00/0:00")
        self._seek_slider.setValue(0)
        self._duration_ms = 0

    def get_volume(self) -> int:
        """Get current volume level."""
        return self._volume_slider.value()

    def set_volume(self, level: int):
        """Set volume level."""
        self._volume_slider.setValue(level)


def _format_time(ms: int) -> str:
    """Format milliseconds as MM:SS or HH:MM:SS."""
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
