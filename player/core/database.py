"""SQLite database for caching track metadata and playlists."""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from player.utils.config import CONFIG_DIR


DB_PATH = CONFIG_DIR / "library.db"


class LibraryDatabase:
    """SQLite cache for track metadata."""

    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY,
                    filepath TEXT UNIQUE NOT NULL,
                    mtime REAL NOT NULL,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    year TEXT,
                    genre TEXT,
                    track_number INTEGER,
                    duration REAL,
                    codec TEXT,
                    bitrate INTEGER,
                    sample_rate INTEGER,
                    bit_depth INTEGER
                )
            """)
            # Migration: add genre column if it doesn't exist
            cursor = conn.execute("PRAGMA table_info(tracks)")
            columns = [row[1] for row in cursor.fetchall()]
            if "genre" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN genre TEXT")
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_filepath ON tracks(filepath)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_artist_album ON tracks(artist, album)
            """)
            # Playlists tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    modified_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    id INTEGER PRIMARY KEY,
                    playlist_id TEXT NOT NULL,
                    track_path TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist
                ON playlist_tracks(playlist_id, position)
            """)
            # Favorites table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    filepath TEXT PRIMARY KEY
                )
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Create a database connection."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_all_tracks(self) -> list[dict]:
        """Get all tracks from the database."""
        with self._connect() as conn:
            cursor = conn.execute("""
                SELECT filepath, mtime, title, artist, album, year, genre,
                       track_number, duration, codec, bitrate,
                       sample_rate, bit_depth
                FROM tracks
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_track(self, filepath: str) -> dict | None:
        """Get a single track by filepath."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM tracks WHERE filepath = ?",
                (filepath,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_cached_mtimes(self) -> dict[str, float]:
        """Get filepath -> mtime mapping for all cached tracks."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT filepath, mtime FROM tracks")
            return {row["filepath"]: row["mtime"] for row in cursor.fetchall()}

    def upsert_track(self, track_data: dict[str, Any], mtime: float) -> None:
        """Insert or update a single track."""
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tracks
                (filepath, mtime, title, artist, album, year, genre, track_number,
                 duration, codec, bitrate, sample_rate, bit_depth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                track_data["filepath"],
                mtime,
                track_data.get("title", "Unknown"),
                track_data.get("artist", "Unknown"),
                track_data.get("album", "Unknown"),
                track_data.get("year", ""),
                track_data.get("genre", ""),
                track_data.get("track_number", 0),
                track_data.get("duration", 0.0),
                track_data.get("codec", "Unknown"),
                track_data.get("bitrate", 0),
                track_data.get("sample_rate", 0),
                track_data.get("bit_depth", 0),
            ))
            conn.commit()

    def upsert_tracks(self, tracks: list[tuple[dict[str, Any], float]]) -> None:
        """Batch insert or update tracks. Each tuple is (track_data, mtime)."""
        if not tracks:
            return

        with self._connect() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO tracks
                (filepath, mtime, title, artist, album, year, genre, track_number,
                 duration, codec, bitrate, sample_rate, bit_depth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    data["filepath"],
                    mtime,
                    data.get("title", "Unknown"),
                    data.get("artist", "Unknown"),
                    data.get("album", "Unknown"),
                    data.get("year", ""),
                    data.get("genre", ""),
                    data.get("track_number", 0),
                    data.get("duration", 0.0),
                    data.get("codec", "Unknown"),
                    data.get("bitrate", 0),
                    data.get("sample_rate", 0),
                    data.get("bit_depth", 0),
                )
                for data, mtime in tracks
            ])
            conn.commit()

    def remove_tracks(self, filepaths: list[str]) -> None:
        """Remove tracks by filepath."""
        if not filepaths:
            return

        with self._connect() as conn:
            placeholders = ",".join("?" * len(filepaths))
            conn.execute(
                f"DELETE FROM tracks WHERE filepath IN ({placeholders})",
                filepaths
            )
            conn.commit()

    def remove_tracks_not_in(self, valid_filepaths: set[str]) -> int:
        """Remove tracks whose filepath is not in the given set. Returns count removed."""
        with self._connect() as conn:
            # Get all filepaths in DB
            cursor = conn.execute("SELECT filepath FROM tracks")
            db_paths = {row["filepath"] for row in cursor.fetchall()}

            # Find paths to remove
            to_remove = db_paths - valid_filepaths

            if to_remove:
                placeholders = ",".join("?" * len(to_remove))
                conn.execute(
                    f"DELETE FROM tracks WHERE filepath IN ({placeholders})",
                    list(to_remove)
                )
                conn.commit()

            return len(to_remove)

    def clear(self) -> None:
        """Remove all tracks from the database."""
        with self._connect() as conn:
            conn.execute("DELETE FROM tracks")
            conn.commit()

    def count(self) -> int:
        """Get total number of cached tracks."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM tracks")
            return cursor.fetchone()[0]

    # --- Playlist methods ---

    def get_all_playlists(self) -> list[dict]:
        """Get all playlists (without tracks)."""
        with self._connect() as conn:
            cursor = conn.execute("""
                SELECT id, name, created_at, modified_at
                FROM playlists
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_playlist(self, playlist_id: str) -> dict | None:
        """Get a playlist by ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id, name, created_at, modified_at FROM playlists WHERE id = ?",
                (playlist_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_playlist_tracks(self, playlist_id: str) -> list[str]:
        """Get track paths for a playlist in order."""
        with self._connect() as conn:
            cursor = conn.execute("""
                SELECT track_path FROM playlist_tracks
                WHERE playlist_id = ?
                ORDER BY position
            """, (playlist_id,))
            return [row["track_path"] for row in cursor.fetchall()]

    def get_playlist_track_count(self, playlist_id: str) -> int:
        """Get number of tracks in a playlist."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?",
                (playlist_id,)
            )
            return cursor.fetchone()[0]

    def create_playlist(self, name: str) -> str:
        """Create a new playlist. Returns the playlist ID."""
        playlist_id = str(uuid.uuid4())
        now = datetime.now().timestamp()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO playlists (id, name, created_at, modified_at) VALUES (?, ?, ?, ?)",
                (playlist_id, name, now, now)
            )
            conn.commit()
        return playlist_id

    def rename_playlist(self, playlist_id: str, name: str) -> None:
        """Rename a playlist."""
        now = datetime.now().timestamp()
        with self._connect() as conn:
            conn.execute(
                "UPDATE playlists SET name = ?, modified_at = ? WHERE id = ?",
                (name, now, playlist_id)
            )
            conn.commit()

    def delete_playlist(self, playlist_id: str) -> None:
        """Delete a playlist and its tracks."""
        with self._connect() as conn:
            conn.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
            conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
            conn.commit()

    def add_tracks_to_playlist(self, playlist_id: str, track_paths: list[str]) -> None:
        """Add tracks to the end of a playlist."""
        if not track_paths:
            return
        now = datetime.now().timestamp()
        with self._connect() as conn:
            # Get current max position
            cursor = conn.execute(
                "SELECT COALESCE(MAX(position), -1) FROM playlist_tracks WHERE playlist_id = ?",
                (playlist_id,)
            )
            max_pos = cursor.fetchone()[0]

            # Insert new tracks
            conn.executemany(
                "INSERT INTO playlist_tracks (playlist_id, track_path, position) VALUES (?, ?, ?)",
                [(playlist_id, path, max_pos + 1 + i) for i, path in enumerate(track_paths)]
            )
            conn.execute(
                "UPDATE playlists SET modified_at = ? WHERE id = ?",
                (now, playlist_id)
            )
            conn.commit()

    def remove_tracks_from_playlist(self, playlist_id: str, track_paths: list[str]) -> None:
        """Remove tracks from a playlist."""
        if not track_paths:
            return
        now = datetime.now().timestamp()
        with self._connect() as conn:
            placeholders = ",".join("?" * len(track_paths))
            conn.execute(
                f"DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_path IN ({placeholders})",
                [playlist_id] + track_paths
            )
            # Reorder remaining tracks
            cursor = conn.execute(
                "SELECT id FROM playlist_tracks WHERE playlist_id = ? ORDER BY position",
                (playlist_id,)
            )
            for i, row in enumerate(cursor.fetchall()):
                conn.execute(
                    "UPDATE playlist_tracks SET position = ? WHERE id = ?",
                    (i, row["id"])
                )
            conn.execute(
                "UPDATE playlists SET modified_at = ? WHERE id = ?",
                (now, playlist_id)
            )
            conn.commit()

    def set_playlist_tracks(self, playlist_id: str, track_paths: list[str]) -> None:
        """Replace all tracks in a playlist."""
        now = datetime.now().timestamp()
        with self._connect() as conn:
            conn.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
            if track_paths:
                conn.executemany(
                    "INSERT INTO playlist_tracks (playlist_id, track_path, position) VALUES (?, ?, ?)",
                    [(playlist_id, path, i) for i, path in enumerate(track_paths)]
                )
            conn.execute(
                "UPDATE playlists SET modified_at = ? WHERE id = ?",
                (now, playlist_id)
            )
            conn.commit()

    # --- Favorites methods ---

    def is_favorite(self, filepath: str) -> bool:
        """Check if a track is a favorite."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM favorites WHERE filepath = ?",
                (filepath,)
            )
            return cursor.fetchone() is not None

    def set_favorite(self, filepath: str, favorite: bool) -> None:
        """Set or unset a track as favorite."""
        with self._connect() as conn:
            if favorite:
                conn.execute(
                    "INSERT OR IGNORE INTO favorites (filepath) VALUES (?)",
                    (filepath,)
                )
            else:
                conn.execute(
                    "DELETE FROM favorites WHERE filepath = ?",
                    (filepath,)
                )
            conn.commit()

    def get_all_favorites(self) -> set[str]:
        """Get all favorite track filepaths."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT filepath FROM favorites")
            return {row["filepath"] for row in cursor.fetchall()}

    def get_favorites_count(self) -> int:
        """Get number of favorite tracks."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM favorites")
            return cursor.fetchone()[0]
