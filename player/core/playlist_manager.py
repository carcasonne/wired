"""Manager for saved playlists."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from player.core.database import LibraryDatabase
from player.core.metadata import Track


@dataclass
class SavedPlaylist:
    """Represents a saved playlist."""

    id: str
    name: str
    created_at: datetime
    modified_at: datetime
    track_count: int = 0

    @classmethod
    def from_db(cls, data: dict, track_count: int = 0) -> "SavedPlaylist":
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=datetime.fromtimestamp(data["created_at"]),
            modified_at=datetime.fromtimestamp(data["modified_at"]),
            track_count=track_count,
        )


class PlaylistManager(QObject):
    """Manages saved playlists stored in SQLite."""

    # Signals
    playlists_changed = pyqtSignal()  # Emitted when playlist list changes
    playlist_updated = pyqtSignal(str)  # Emitted when a playlist's tracks change (playlist_id)

    def __init__(self, database: LibraryDatabase):
        super().__init__()
        self._db = database

    def get_all(self) -> list[SavedPlaylist]:
        """Get all playlists with track counts."""
        playlists = []
        for data in self._db.get_all_playlists():
            count = self._db.get_playlist_track_count(data["id"])
            playlists.append(SavedPlaylist.from_db(data, count))
        return playlists

    def get(self, playlist_id: str) -> SavedPlaylist | None:
        """Get a playlist by ID."""
        data = self._db.get_playlist(playlist_id)
        if data:
            count = self._db.get_playlist_track_count(playlist_id)
            return SavedPlaylist.from_db(data, count)
        return None

    def create(self, name: str) -> SavedPlaylist:
        """Create a new empty playlist."""
        playlist_id = self._db.create_playlist(name)
        self.playlists_changed.emit()
        return self.get(playlist_id)

    def rename(self, playlist_id: str, name: str) -> None:
        """Rename a playlist."""
        self._db.rename_playlist(playlist_id, name)
        self.playlists_changed.emit()

    def delete(self, playlist_id: str) -> None:
        """Delete a playlist."""
        self._db.delete_playlist(playlist_id)
        self.playlists_changed.emit()

    def get_tracks(self, playlist_id: str, library_tracks: list[Track]) -> list[Track]:
        """
        Get tracks for a playlist, resolving paths to Track objects.

        Args:
            playlist_id: The playlist ID
            library_tracks: List of all library tracks (for path lookup)

        Returns:
            List of Track objects in playlist order
        """
        paths = self._db.get_playlist_tracks(playlist_id)
        path_to_track = {str(t.filepath): t for t in library_tracks}

        tracks = []
        for path in paths:
            if path in path_to_track:
                tracks.append(path_to_track[path])
            # Skip missing tracks silently

        return tracks

    def add_tracks(self, playlist_id: str, tracks: list[Track]) -> None:
        """Add tracks to a playlist."""
        paths = [str(t.filepath) for t in tracks]
        self._db.add_tracks_to_playlist(playlist_id, paths)
        self.playlist_updated.emit(playlist_id)

    def remove_tracks(self, playlist_id: str, tracks: list[Track]) -> None:
        """Remove tracks from a playlist."""
        paths = [str(t.filepath) for t in tracks]
        self._db.remove_tracks_from_playlist(playlist_id, paths)
        self.playlist_updated.emit(playlist_id)

    def set_tracks(self, playlist_id: str, tracks: list[Track]) -> None:
        """Replace all tracks in a playlist."""
        paths = [str(t.filepath) for t in tracks]
        self._db.set_playlist_tracks(playlist_id, paths)
        self.playlist_updated.emit(playlist_id)

    def export_m3u(self, playlist_id: str, filepath: Path, library_tracks: list[Track]) -> None:
        """Export a playlist to M3U format."""
        playlist = self.get(playlist_id)
        tracks = self.get_tracks(playlist_id, library_tracks)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            if playlist:
                f.write(f"#PLAYLIST:{playlist.name}\n")

            for track in tracks:
                duration = int(track.duration)
                f.write(f"#EXTINF:{duration},{track.artist} - {track.title}\n")
                f.write(f"{track.filepath}\n")

    def import_m3u(self, filepath: Path, library_tracks: list[Track]) -> SavedPlaylist | None:
        """
        Import a playlist from M3U format.

        Args:
            filepath: Path to the M3U file
            library_tracks: List of all library tracks (for validation)

        Returns:
            The created playlist, or None if import failed
        """
        if not filepath.exists():
            return None

        # Parse M3U
        track_paths = []
        playlist_name = filepath.stem  # Default to filename

        path_to_track = {str(t.filepath): t for t in library_tracks}
        m3u_dir = filepath.parent

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#EXTM3U"):
                    continue
                if line.startswith("#PLAYLIST:"):
                    playlist_name = line[10:].strip()
                    continue
                if line.startswith("#"):
                    continue  # Skip other directives

                # This is a track path
                track_path = line

                # Handle relative paths (including ../ style paths)
                if not Path(track_path).is_absolute():
                    # Join with m3u directory and resolve to get canonical path
                    track_path = str((m3u_dir / track_path).resolve())

                # Only add if track exists in library
                if track_path in path_to_track:
                    track_paths.append(track_path)

        if not track_paths:
            return None

        # Create playlist
        playlist_id = self._db.create_playlist(playlist_name)
        self._db.add_tracks_to_playlist(playlist_id, track_paths)
        self.playlists_changed.emit()

        return self.get(playlist_id)
