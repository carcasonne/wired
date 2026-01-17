# -*- coding: utf-8 -*-
"""Bottom player bar with playback controls."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QSlider,
    QLabel,
)

from player.theme.lainchan import BG_TERTIARY, TEXT_MUTED, ACCENT


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
        self.setFixedHeight(80)
        self.setStyleSheet(f"background-color: {BG_TERTIARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(4)

        # Row 1: Controls + Seekbar + Time
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        # Playback buttons - using ASCII text
        self._prev_btn = QPushButton("|<")
        self._play_btn = QPushButton(">")
        self._next_btn = QPushButton(">|")

        for btn in [self._prev_btn, self._play_btn, self._next_btn]:
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self._prev_btn.clicked.connect(self.prev_clicked.emit)
        self._play_btn.clicked.connect(self._on_play_clicked)
        self._next_btn.clicked.connect(self.next_clicked.emit)

        row1.addWidget(self._prev_btn)
        row1.addWidget(self._play_btn)
        row1.addWidget(self._next_btn)

        # Seek bar
        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.sliderPressed.connect(self._on_seek_start)
        self._seek_slider.sliderReleased.connect(self._on_seek_end)
        self._seek_slider.sliderMoved.connect(self._on_seek_moved)
        row1.addWidget(self._seek_slider, 1)

        # Time display
        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setStyleSheet(f"color: {TEXT_MUTED}; min-width: 90px;")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(self._time_label)

        layout.addLayout(row1)

        # Row 2: Track info + Volume
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        # Track info (left side)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)

        self._track_label = QLabel("No track loaded")
        self._track_label.setStyleSheet("font-size: 14px; font-weight: bold;")

        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")

        info_layout.addWidget(self._track_label)
        info_layout.addWidget(self._detail_label)
        row2.addLayout(info_layout, 1)

        # Volume control (right side)
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(8)

        self._volume_icon = QLabel("VOL")
        volume_layout.addWidget(self._volume_icon)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(75)
        self._volume_slider.setFixedWidth(100)
        self._volume_slider.valueChanged.connect(self.volume_changed.emit)
        volume_layout.addWidget(self._volume_slider)

        self._volume_label = QLabel("75%")
        self._volume_label.setStyleSheet(f"color: {TEXT_MUTED}; min-width: 35px;")
        self._volume_slider.valueChanged.connect(
            lambda v: self._volume_label.setText(f"{v}%")
        )
        volume_layout.addWidget(self._volume_label)

        row2.addLayout(volume_layout)
        layout.addLayout(row2)

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
                f"{_format_time(current_ms)} / {_format_time(self._duration_ms)}"
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
                    f"{_format_time(current_ms)} / {_format_time(self._duration_ms)}"
                )

    def set_duration(self, duration_ms: int):
        """Set track duration for time display."""
        self._duration_ms = duration_ms

    def set_track_info(self, title: str, artist: str, album: str, year: str,
                       codec: str, sample_info: str, bitrate: str):
        """Update track info display."""
        self._track_label.setText(f"{title} - {artist}")

        details = []
        if album:
            album_text = f"{album}"
            if year:
                album_text += f" ({year})"
            details.append(album_text)
        if codec:
            details.append(codec)
        if sample_info:
            details.append(sample_info)
        if bitrate:
            details.append(bitrate)

        self._detail_label.setText(" | ".join(details))

    def clear_track_info(self):
        """Clear track info display."""
        self._track_label.setText("No track loaded")
        self._detail_label.setText("")
        self._time_label.setText("0:00 / 0:00")
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
