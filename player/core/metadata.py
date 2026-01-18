"""Track metadata reading using mutagen."""

from dataclasses import dataclass, field
from pathlib import Path

from mutagen import File
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4


@dataclass
class Track:
    """Represents an audio track with metadata."""

    filepath: Path
    title: str = "Unknown"
    artist: str = "Unknown"
    album: str = "Unknown"
    year: str = ""
    genre: str = ""  # semicolon-separated for multiple genres
    track_number: int = 0
    duration: float = 0.0  # seconds
    codec: str = "Unknown"
    bitrate: int = 0  # kbps
    sample_rate: int = 0  # Hz
    bit_depth: int = 0  # bits (for lossless)
    favorite: bool = False  # user favorite flag (not from file metadata)
    album_art: bytes | None = field(default=None, repr=False)

    @classmethod
    def from_cache(cls, data: dict) -> "Track":
        """Create a Track from cached database row (no file I/O)."""
        return cls(
            filepath=Path(data["filepath"]),
            title=data.get("title", "Unknown"),
            artist=data.get("artist", "Unknown"),
            album=data.get("album", "Unknown"),
            year=data.get("year", ""),
            genre=data.get("genre", ""),
            track_number=data.get("track_number", 0),
            duration=data.get("duration", 0.0),
            codec=data.get("codec", "Unknown"),
            bitrate=data.get("bitrate", 0),
            sample_rate=data.get("sample_rate", 0),
            bit_depth=data.get("bit_depth", 0),
            album_art=None,  # Not cached, extracted on-demand
        )

    def to_cache_dict(self) -> dict:
        """Convert Track to dict for database storage."""
        return {
            "filepath": str(self.filepath),
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "year": self.year,
            "genre": self.genre,
            "track_number": self.track_number,
            "duration": self.duration,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "bit_depth": self.bit_depth,
        }

    def load_album_art(self) -> None:
        """Load album art from file on-demand (if not already loaded)."""
        if self.album_art is not None:
            return
        try:
            audio = File(str(self.filepath))
            if audio:
                self.album_art = _extract_album_art(audio)
        except Exception:
            pass

    @classmethod
    def from_file(cls, filepath: str | Path) -> "Track":
        """Create a Track from an audio file path."""
        path = Path(filepath)
        track = cls(filepath=path)

        try:
            audio = File(str(path))
            if audio is None:
                return track

            # Extract common metadata
            track.title = _get_tag(audio, ["title", "TIT2", "\xa9nam"], path.stem)
            track.artist = _get_tag(audio, ["artist", "TPE1", "\xa9ART"], "Unknown")
            track.album = _get_tag(audio, ["album", "TALB", "\xa9alb"], "Unknown")
            track.year = _get_tag(audio, ["date", "TDRC", "\xa9day"], "")[:4]  # Just year
            track.genre = _get_tag(audio, ["genre", "TCON", "\xa9gen"], "")

            # Track number
            track_num = _get_tag(audio, ["tracknumber", "TRCK", "trkn"], "0")
            if isinstance(track_num, tuple):
                track_num = track_num[0]
            track.track_number = _parse_track_number(str(track_num))

            # Duration
            if audio.info:
                track.duration = audio.info.length or 0.0

            # Codec-specific metadata
            track.codec, track.bitrate, track.sample_rate, track.bit_depth = _get_audio_info(audio, path)

            # Album art
            track.album_art = _extract_album_art(audio)

        except Exception:
            # Return track with defaults if metadata extraction fails
            pass

        return track

    def format_duration(self) -> str:
        """Format duration as MM:SS or HH:MM:SS."""
        total_seconds = int(self.duration)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def format_bitrate(self) -> str:
        """Format bitrate for display."""
        if self.bitrate > 0:
            return f"{self.bitrate} kbps"
        return ""

    def format_sample_info(self) -> str:
        """Format sample rate and bit depth for display."""
        parts = []
        if self.bit_depth > 0:
            parts.append(f"{self.bit_depth}-bit")
        if self.sample_rate > 0:
            sr = self.sample_rate / 1000
            if sr == int(sr):
                parts.append(f"{int(sr)} kHz")
            else:
                parts.append(f"{sr:.1f} kHz")
        return " / ".join(parts)


def _get_tag(audio, keys: list[str], default: str) -> str:
    """Get tag value trying multiple possible keys."""
    for key in keys:
        value = audio.get(key)
        if value:
            if isinstance(value, list):
                return str(value[0])
            return str(value)
    return default


def _parse_track_number(value: str) -> int:
    """Parse track number from various formats (e.g., '5', '5/12')."""
    try:
        return int(value.split("/")[0].strip())
    except (ValueError, IndexError):
        return 0


def _get_audio_info(audio, path: Path) -> tuple[str, int, int, int]:
    """Extract codec, bitrate, sample rate, bit depth from audio file."""
    codec = "Unknown"
    bitrate = 0
    sample_rate = 0
    bit_depth = 0

    suffix = path.suffix.lower()

    if isinstance(audio, FLAC):
        codec = "FLAC"
        if audio.info:
            sample_rate = audio.info.sample_rate
            bit_depth = audio.info.bits_per_sample
            # Calculate average bitrate for FLAC
            if audio.info.length > 0:
                bitrate = int((path.stat().st_size * 8) / audio.info.length / 1000)
    elif isinstance(audio, MP3):
        codec = "MP3"
        if audio.info:
            bitrate = int(audio.info.bitrate / 1000)
            sample_rate = audio.info.sample_rate
    elif isinstance(audio, OggVorbis):
        codec = "OGG"
        if audio.info:
            bitrate = int(audio.info.bitrate / 1000)
            sample_rate = audio.info.sample_rate
    elif isinstance(audio, MP4):
        codec = "AAC"
        if audio.info:
            bitrate = int(audio.info.bitrate / 1000) if audio.info.bitrate else 0
            sample_rate = audio.info.sample_rate
    elif suffix == ".wav":
        codec = "WAV"
        if audio and audio.info:
            sample_rate = audio.info.sample_rate
            bit_depth = audio.info.bits_per_sample
    else:
        # Try to determine from extension
        codec_map = {
            ".mp3": "MP3",
            ".flac": "FLAC",
            ".ogg": "OGG",
            ".m4a": "AAC",
            ".wav": "WAV",
            ".opus": "OPUS",
        }
        codec = codec_map.get(suffix, suffix.upper().lstrip("."))

    return codec, bitrate, sample_rate, bit_depth


def _extract_album_art(audio) -> bytes | None:
    """Extract embedded album art from audio file."""
    try:
        # FLAC
        if isinstance(audio, FLAC) and audio.pictures:
            return audio.pictures[0].data

        # MP3 (ID3)
        if isinstance(audio, MP3):
            for key in audio.keys():
                if key.startswith("APIC"):
                    return audio[key].data

        # MP4/M4A
        if isinstance(audio, MP4):
            covers = audio.get("covr")
            if covers:
                return bytes(covers[0])

        # OGG Vorbis (base64 encoded FLAC picture)
        if isinstance(audio, OggVorbis):
            pictures = audio.get("metadata_block_picture")
            if pictures:
                import base64
                from mutagen.flac import Picture
                data = base64.b64decode(pictures[0])
                picture = Picture(data)
                return picture.data

    except Exception:
        pass

    return None
