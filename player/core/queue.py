"""Playback queue for managing upcoming tracks."""

from PyQt6.QtCore import QObject, pyqtSignal

from player.core.metadata import Track


class PlaybackQueue(QObject):
    """
    Manages a queue of tracks to play next.

    The queue is separate from the playlist and takes priority
    when determining what plays after the current track ends.
    """

    queue_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._tracks: list[Track] = []

    @property
    def tracks(self) -> list[Track]:
        """Get all tracks in the queue."""
        return self._tracks.copy()

    def __len__(self) -> int:
        return len(self._tracks)

    def __bool__(self) -> bool:
        return len(self._tracks) > 0

    def __getitem__(self, index: int) -> Track:
        return self._tracks[index]

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._tracks) == 0

    def play_next(self, track: Track) -> None:
        """Add track to front of queue (plays next)."""
        self._tracks.insert(0, track)
        self.queue_changed.emit()

    def add_to_queue(self, track: Track) -> None:
        """Add track to end of queue."""
        self._tracks.append(track)
        self.queue_changed.emit()

    def add_tracks(self, tracks: list[Track]) -> None:
        """Add multiple tracks to end of queue."""
        self._tracks.extend(tracks)
        self.queue_changed.emit()

    def pop_next(self) -> Track | None:
        """Remove and return the next track from queue."""
        if self._tracks:
            track = self._tracks.pop(0)
            self.queue_changed.emit()
            return track
        return None

    def peek_next(self) -> Track | None:
        """Return the next track without removing it."""
        return self._tracks[0] if self._tracks else None

    def remove(self, index: int) -> None:
        """Remove track at specified index."""
        if 0 <= index < len(self._tracks):
            self._tracks.pop(index)
            self.queue_changed.emit()

    def move(self, from_index: int, to_index: int) -> None:
        """Move track from one position to another."""
        if 0 <= from_index < len(self._tracks) and 0 <= to_index < len(self._tracks):
            track = self._tracks.pop(from_index)
            self._tracks.insert(to_index, track)
            self.queue_changed.emit()

    def clear(self) -> None:
        """Remove all tracks from queue."""
        self._tracks.clear()
        self.queue_changed.emit()

    def get_filepaths(self) -> list[str]:
        """Get list of file paths for persistence."""
        return [str(t.filepath) for t in self._tracks]

    def total_duration(self) -> float:
        """Get total duration of queued tracks in seconds."""
        return sum(t.duration for t in self._tracks)
