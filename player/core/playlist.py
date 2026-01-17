"""Playlist data structure for managing track collections."""

import random
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal

from player.core.metadata import Track


class Playlist(QObject):
    """Manages a collection of tracks with navigation."""

    current_changed = pyqtSignal(int)  # index of new current track
    tracks_changed = pyqtSignal()  # playlist contents modified
    shuffle_changed = pyqtSignal(bool)  # shuffle mode toggled

    def __init__(self, name: str = "Playlist"):
        super().__init__()
        self.name = name
        self._tracks: list[Track] = []
        self._current_index: int = -1
        self._shuffle_order: list[int] | None = None

    @property
    def tracks(self) -> list[Track]:
        """Get all tracks in the playlist."""
        return self._tracks

    @property
    def current_index(self) -> int:
        """Get current track index."""
        return self._current_index

    def __len__(self) -> int:
        return len(self._tracks)

    def __getitem__(self, index: int) -> Track:
        return self._tracks[index]

    def add_track(self, track: Track) -> None:
        """Add a track to the playlist."""
        self._tracks.append(track)
        self.tracks_changed.emit()

    def add_tracks(self, tracks: list[Track]) -> None:
        """Add multiple tracks to the playlist."""
        self._tracks.extend(tracks)
        self.tracks_changed.emit()

    def remove_track(self, index: int) -> None:
        """Remove track at index."""
        if 0 <= index < len(self._tracks):
            self._tracks.pop(index)
            if self._current_index >= len(self._tracks):
                self._current_index = len(self._tracks) - 1
            elif self._current_index > index:
                self._current_index -= 1
            self.tracks_changed.emit()

    def clear(self) -> None:
        """Remove all tracks."""
        self._tracks.clear()
        self._current_index = -1
        self._shuffle_order = None
        self.tracks_changed.emit()

    def get_current(self) -> Track | None:
        """Get the currently selected track."""
        if 0 <= self._current_index < len(self._tracks):
            return self._tracks[self._current_index]
        return None

    def set_current(self, index: int) -> Track | None:
        """Set current track by index."""
        if 0 <= index < len(self._tracks):
            self._current_index = index
            self.current_changed.emit(index)
            return self._tracks[index]
        return None

    def next(self) -> Track | None:
        """Move to and return next track."""
        if not self._tracks:
            return None

        if self._shuffle_order:
            # Shuffle mode
            try:
                current_shuffle_idx = self._shuffle_order.index(self._current_index)
                next_shuffle_idx = (current_shuffle_idx + 1) % len(self._shuffle_order)
                self._current_index = self._shuffle_order[next_shuffle_idx]
            except ValueError:
                self._current_index = self._shuffle_order[0] if self._shuffle_order else 0
        else:
            # Normal mode
            self._current_index = (self._current_index + 1) % len(self._tracks)

        self.current_changed.emit(self._current_index)
        return self._tracks[self._current_index]

    def previous(self) -> Track | None:
        """Move to and return previous track."""
        if not self._tracks:
            return None

        if self._shuffle_order:
            # Shuffle mode
            try:
                current_shuffle_idx = self._shuffle_order.index(self._current_index)
                prev_shuffle_idx = (current_shuffle_idx - 1) % len(self._shuffle_order)
                self._current_index = self._shuffle_order[prev_shuffle_idx]
            except ValueError:
                self._current_index = self._shuffle_order[0] if self._shuffle_order else 0
        else:
            # Normal mode
            self._current_index = (self._current_index - 1) % len(self._tracks)

        self.current_changed.emit(self._current_index)
        return self._tracks[self._current_index]

    def shuffle(self, enabled: bool = True) -> None:
        """Enable or disable shuffle mode."""
        if enabled:
            self._shuffle_order = list(range(len(self._tracks)))
            random.shuffle(self._shuffle_order)
            # Put current track at start of shuffle
            if self._current_index >= 0 and self._current_index in self._shuffle_order:
                self._shuffle_order.remove(self._current_index)
                self._shuffle_order.insert(0, self._current_index)
        else:
            self._shuffle_order = None
        self.shuffle_changed.emit(enabled)

    def is_shuffled(self) -> bool:
        """Check if shuffle is enabled."""
        return self._shuffle_order is not None

    def get_upcoming_tracks(self, count: int = 10) -> list[Track]:
        """Get next N tracks respecting shuffle order."""
        if not self._tracks or self._current_index < 0:
            return []

        upcoming = []
        total = len(self._tracks)

        if self._shuffle_order:
            try:
                current_pos = self._shuffle_order.index(self._current_index)
            except ValueError:
                current_pos = 0
            for i in range(1, min(count + 1, total)):
                next_pos = (current_pos + i) % len(self._shuffle_order)
                track_idx = self._shuffle_order[next_pos]
                upcoming.append(self._tracks[track_idx])
        else:
            for i in range(1, min(count + 1, total)):
                next_idx = (self._current_index + i) % total
                upcoming.append(self._tracks[next_idx])

        return upcoming

    def sort(self, key: str, reverse: bool = False) -> None:
        """Sort tracks by a given attribute."""
        current_track = self.get_current()

        key_funcs: dict[str, Callable[[Track], any]] = {
            "title": lambda t: t.title.lower(),
            "artist": lambda t: t.artist.lower(),
            "album": lambda t: (t.album.lower(), t.track_number),
            "year": lambda t: t.year,
            "duration": lambda t: t.duration,
            "track_number": lambda t: t.track_number,
        }

        if key in key_funcs:
            self._tracks.sort(key=key_funcs[key], reverse=reverse)

            # Update current index to follow the track
            if current_track:
                try:
                    self._current_index = self._tracks.index(current_track)
                except ValueError:
                    self._current_index = -1

            self.tracks_changed.emit()
