"""SQLite database for caching track metadata."""

import sqlite3
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
                    track_number INTEGER,
                    duration REAL,
                    codec TEXT,
                    bitrate INTEGER,
                    sample_rate INTEGER,
                    bit_depth INTEGER
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_filepath ON tracks(filepath)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_artist_album ON tracks(artist, album)
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
                SELECT filepath, mtime, title, artist, album, year,
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
                (filepath, mtime, title, artist, album, year, track_number,
                 duration, codec, bitrate, sample_rate, bit_depth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                track_data["filepath"],
                mtime,
                track_data.get("title", "Unknown"),
                track_data.get("artist", "Unknown"),
                track_data.get("album", "Unknown"),
                track_data.get("year", ""),
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
                (filepath, mtime, title, artist, album, year, track_number,
                 duration, codec, bitrate, sample_rate, bit_depth)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    data["filepath"],
                    mtime,
                    data.get("title", "Unknown"),
                    data.get("artist", "Unknown"),
                    data.get("album", "Unknown"),
                    data.get("year", ""),
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
