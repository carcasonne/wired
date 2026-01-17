"""VLC-based audio playback engine."""

import vlc
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class AudioEngine(QObject):
    """Audio playback engine wrapping python-vlc."""

    position_changed = pyqtSignal(float)  # 0.0 to 1.0
    duration_changed = pyqtSignal(int)  # milliseconds
    state_changed = pyqtSignal(str)  # "playing", "paused", "stopped"
    track_ended = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._instance = vlc.Instance("--no-xlib")
        self._player = self._instance.media_player_new()
        self._current_path: str | None = None
        self._duration_ms: int = 0
        self._is_playing: bool = False

        # Poll position every 100ms during playback
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll_position)

        # Track end detection
        events = self._player.event_manager()
        events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

    def play(self, filepath: str) -> None:
        """Load and play an audio file."""
        media = self._instance.media_new(filepath)
        self._player.set_media(media)
        self._player.play()
        self._current_path = filepath
        self._is_playing = True
        self._timer.start()
        self.state_changed.emit("playing")

        # Get duration after a short delay (VLC needs time to parse)
        QTimer.singleShot(200, self._update_duration)

    def _update_duration(self) -> None:
        """Update duration after media is loaded."""
        self._duration_ms = self._player.get_length()
        if self._duration_ms > 0:
            self.duration_changed.emit(self._duration_ms)

    def pause(self) -> None:
        """Toggle pause state."""
        self._player.pause()
        # Track state ourselves since VLC state may not update immediately
        self._is_playing = not self._is_playing
        if self._is_playing:
            self._timer.start()
            self.state_changed.emit("playing")
        else:
            self._timer.stop()
            self.state_changed.emit("paused")

    def stop(self) -> None:
        """Stop playback."""
        self._player.stop()
        self._timer.stop()
        self._current_path = None
        self._is_playing = False
        self.state_changed.emit("stopped")

    def seek(self, position: float) -> None:
        """Seek to position (0.0 to 1.0)."""
        self._player.set_position(max(0.0, min(1.0, position)))

    def seek_ms(self, ms: int) -> None:
        """Seek to position in milliseconds."""
        self._player.set_time(ms)

    def get_position(self) -> float:
        """Get current position (0.0 to 1.0)."""
        pos = self._player.get_position()
        return pos if pos >= 0 else 0.0

    def get_time_ms(self) -> int:
        """Get current time in milliseconds."""
        time = self._player.get_time()
        return time if time >= 0 else 0

    def get_duration_ms(self) -> int:
        """Get duration in milliseconds."""
        return self._duration_ms

    def get_state(self) -> str:
        """Get current playback state."""
        if self._current_path is None:
            return "stopped"
        return "playing" if self._is_playing else "paused"

    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._player.is_playing()

    def set_volume(self, level: int) -> None:
        """Set volume (0-100)."""
        self._player.audio_set_volume(max(0, min(100, level)))

    def get_volume(self) -> int:
        """Get current volume (0-100)."""
        return self._player.audio_get_volume()

    def _poll_position(self) -> None:
        """Poll and emit position updates."""
        if self._player.is_playing():
            pos = self.get_position()
            self.position_changed.emit(pos)

            # Update duration if we didn't get it earlier
            if self._duration_ms <= 0:
                self._update_duration()

    def _on_end_reached(self, event) -> None:
        """Handle track end."""
        self._timer.stop()
        self._is_playing = False
        self.track_ended.emit()
        self.state_changed.emit("stopped")
