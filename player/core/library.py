"""Library scanner for discovering audio files."""

from pathlib import Path
from typing import Callable

from player.core.database import LibraryDatabase
from player.core.metadata import Track


SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".opus", ".aac", ".wma"}


class LibraryScanner:
    """Scans directories for audio files and creates Track objects."""

    def __init__(self, database: LibraryDatabase | None = None):
        self._cancel_requested = False
        self._db = database or LibraryDatabase()

    def load_from_cache(self) -> list[Track]:
        """Fast load all tracks from database (no file I/O)."""
        cached = self._db.get_all_tracks()
        return [Track.from_cache(data) for data in cached]

    def scan_for_changes(
        self,
        path: str | Path,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[list[Track], int, int]:
        """
        Incremental scan - only read metadata for new/modified files.

        Args:
            path: Directory path to scan
            progress_callback: Optional callback(current, total, status) for progress

        Returns:
            Tuple of (all_tracks, added_count, removed_count)
        """
        self._cancel_requested = False
        directory = Path(path)

        if not directory.is_dir():
            return [], 0, 0

        # Get cached mtimes
        cached_mtimes = self._db.get_cached_mtimes()

        # Find all audio files on disk
        if progress_callback:
            progress_callback(0, 0, "Discovering files...")
        audio_files = self._find_audio_files(directory)
        current_paths = {str(f) for f in audio_files}

        # Determine what changed
        new_files: list[Path] = []
        modified_files: list[Path] = []
        unchanged_paths: list[str] = []

        for filepath in audio_files:
            if self._cancel_requested:
                break
            path_str = str(filepath)
            if path_str not in cached_mtimes:
                new_files.append(filepath)
            else:
                try:
                    current_mtime = filepath.stat().st_mtime
                    if current_mtime > cached_mtimes[path_str]:
                        modified_files.append(filepath)
                    else:
                        unchanged_paths.append(path_str)
                except OSError:
                    # File disappeared
                    pass

        # Remove deleted files from cache
        removed_count = self._db.remove_tracks_not_in(current_paths)

        # Process new and modified files
        files_to_scan = new_files + modified_files
        total_to_scan = len(files_to_scan)
        tracks_to_upsert: list[tuple[dict, float]] = []

        if progress_callback:
            progress_callback(0, total_to_scan, f"Scanning {total_to_scan} files...")

        for i, filepath in enumerate(files_to_scan):
            if self._cancel_requested:
                break

            try:
                track = Track.from_file(filepath)
                mtime = filepath.stat().st_mtime
                tracks_to_upsert.append((track.to_cache_dict(), mtime))
            except Exception:
                # Skip files that can't be read
                pass

            if progress_callback:
                progress_callback(i + 1, total_to_scan, f"Scanning... ({i + 1}/{total_to_scan})")

        # Batch update database
        if tracks_to_upsert:
            self._db.upsert_tracks(tracks_to_upsert)

        # Load all tracks from cache (now updated)
        all_tracks = self.load_from_cache()

        added_count = len(new_files)
        return all_tracks, added_count, removed_count

    def scan_directory(
        self,
        path: str | Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[Track]:
        """
        Recursively scan a directory for audio files.

        Args:
            path: Directory path to scan
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            List of Track objects
        """
        self._cancel_requested = False
        directory = Path(path)

        if not directory.is_dir():
            return []

        # First pass: collect all audio files
        audio_files = self._find_audio_files(directory)

        if not audio_files:
            return []

        # Second pass: read metadata
        tracks = []
        total = len(audio_files)

        for i, filepath in enumerate(audio_files):
            if self._cancel_requested:
                break

            track = Track.from_file(filepath)
            tracks.append(track)

            if progress_callback:
                progress_callback(i + 1, total)

        return tracks

    def _find_audio_files(self, directory: Path) -> list[Path]:
        """Find all audio files in directory recursively."""
        audio_files = []

        try:
            for item in directory.rglob("*"):
                if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
                    audio_files.append(item)
        except PermissionError:
            pass

        # Sort by path for consistent ordering
        audio_files.sort()
        return audio_files

    def cancel(self) -> None:
        """Request cancellation of ongoing scan."""
        self._cancel_requested = True


def scan_directory(path: str | Path) -> list[Track]:
    """Convenience function to scan a directory."""
    scanner = LibraryScanner()
    return scanner.scan_directory(path)
