"""MPRIS2 D-Bus interface for system media player integration.

Provides:
- Media key support (play/pause/next/prev)
- Track info in notification daemons and lock screens
- Integration with desktop environments (KDE Plasma, GNOME, etc.)
- Control via playerctl and similar tools

References:
- https://specifications.freedesktop.org/mpris-spec/latest/
- https://wiki.archlinux.org/title/MPRIS
"""

import tempfile
import os
from pathlib import Path

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from player.core.metadata import Track

# MPRIS2 interface names
MPRIS2_INTERFACE = "org.mpris.MediaPlayer2"
MPRIS2_PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
DBUS_PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"

# Bus name for our player
BUS_NAME = "org.mpris.MediaPlayer2.wired"


class MPRIS2Service(dbus.service.Object):
    """
    MPRIS2 D-Bus service implementation.

    Exposes org.mpris.MediaPlayer2 and org.mpris.MediaPlayer2.Player
    interfaces for system integration.
    """

    def __init__(self, app):
        """
        Initialize MPRIS2 service.

        Args:
            app: Reference to main application for callbacks
        """
        # Initialize D-Bus main loop integration
        DBusGMainLoop(set_as_default=True)

        self._app = app
        self._bus = dbus.SessionBus()
        self._bus_name = dbus.service.BusName(BUS_NAME, self._bus)

        # Register object at /org/mpris/MediaPlayer2
        super().__init__(self._bus, "/org/mpris/MediaPlayer2")

        # Current state
        self._current_track: Track | None = None
        self._playback_status = "Stopped"
        self._position = 0  # microseconds
        self._volume = 1.0

        # Temp directory for album art
        self._art_dir = Path(tempfile.gettempdir()) / "wired-mpris"
        self._art_dir.mkdir(exist_ok=True)
        self._current_art_path: Path | None = None

    def update_track(self, track: Track | None):
        """Update current track metadata."""
        self._current_track = track
        self._emit_properties_changed(
            MPRIS2_PLAYER_INTERFACE,
            {"Metadata": self._get_metadata()}
        )

    def update_playback_status(self, status: str):
        """Update playback status (Playing, Paused, Stopped)."""
        # Map internal states to MPRIS states
        status_map = {
            "playing": "Playing",
            "paused": "Paused",
            "stopped": "Stopped",
        }
        new_status = status_map.get(status, "Stopped")
        if new_status != self._playback_status:
            self._playback_status = new_status
            self._emit_properties_changed(
                MPRIS2_PLAYER_INTERFACE,
                {"PlaybackStatus": self._playback_status}
            )

    def update_position(self, position_ms: int):
        """Update playback position in milliseconds."""
        self._position = position_ms * 1000  # Convert to microseconds

    def update_volume(self, volume: float):
        """Update volume (0.0 to 1.0)."""
        self._volume = volume / 100.0  # Convert from percentage
        self._emit_properties_changed(
            MPRIS2_PLAYER_INTERFACE,
            {"Volume": self._volume}
        )

    def _get_metadata(self) -> dbus.Dictionary:
        """Build metadata dictionary for current track."""
        metadata = dbus.Dictionary(signature="sv")

        if self._current_track:
            track = self._current_track
            # Required: track ID (D-Bus object path)
            track_id = f"/org/wired/track/{abs(hash(str(track.filepath)))}"
            metadata["mpris:trackid"] = dbus.ObjectPath(track_id)

            # Track length in microseconds
            if track.duration > 0:
                metadata["mpris:length"] = dbus.Int64(int(track.duration * 1_000_000))

            # Standard metadata fields
            if track.title and track.title != "Unknown":
                metadata["xesam:title"] = track.title

            if track.artist and track.artist != "Unknown":
                metadata["xesam:artist"] = dbus.Array([track.artist], signature="s")

            if track.album and track.album != "Unknown":
                metadata["xesam:album"] = track.album

            if track.year:
                metadata["xesam:contentCreated"] = track.year

            # File URL
            metadata["xesam:url"] = f"file://{track.filepath}"

            # Album art - extract to temp file for MPRIS
            art_url = self._get_album_art_url(track)
            if art_url:
                metadata["mpris:artUrl"] = art_url

        return metadata

    def _get_album_art_url(self, track: Track) -> str | None:
        """Extract album art to temp file and return file:// URL."""
        if not track.album_art:
            return None

        try:
            # Create unique filename based on track path hash
            art_hash = abs(hash(str(track.filepath)))
            art_path = self._art_dir / f"art_{art_hash}.jpg"

            # Only write if not already cached
            if not art_path.exists():
                art_path.write_bytes(track.album_art)

            self._current_art_path = art_path
            return f"file://{art_path}"
        except Exception:
            return None

    def _emit_properties_changed(self, interface: str, changed: dict):
        """Emit PropertiesChanged signal."""
        self.PropertiesChanged(
            interface,
            dbus.Dictionary(changed, signature="sv"),
            dbus.Array([], signature="s")
        )

    # ==================== org.mpris.MediaPlayer2 ====================

    @dbus.service.method(MPRIS2_INTERFACE)
    def Raise(self):
        """Bring player window to front."""
        if self._app:
            self._app.raise_window()

    @dbus.service.method(MPRIS2_INTERFACE)
    def Quit(self):
        """Quit the application."""
        if self._app:
            self._app.quit_app()

    # ==================== org.mpris.MediaPlayer2.Player ====================

    @dbus.service.method(MPRIS2_PLAYER_INTERFACE)
    def Next(self):
        """Skip to next track."""
        if self._app:
            self._app.play_next()

    @dbus.service.method(MPRIS2_PLAYER_INTERFACE)
    def Previous(self):
        """Skip to previous track."""
        if self._app:
            self._app.play_previous()

    @dbus.service.method(MPRIS2_PLAYER_INTERFACE)
    def Pause(self):
        """Pause playback."""
        if self._app:
            self._app.pause()

    @dbus.service.method(MPRIS2_PLAYER_INTERFACE)
    def PlayPause(self):
        """Toggle play/pause."""
        if self._app:
            self._app.toggle_play_pause()

    @dbus.service.method(MPRIS2_PLAYER_INTERFACE)
    def Stop(self):
        """Stop playback."""
        if self._app:
            self._app.stop()

    @dbus.service.method(MPRIS2_PLAYER_INTERFACE)
    def Play(self):
        """Start/resume playback."""
        if self._app:
            self._app.play()

    @dbus.service.method(MPRIS2_PLAYER_INTERFACE, in_signature="x")
    def Seek(self, offset: int):
        """Seek by offset in microseconds."""
        if self._app:
            offset_ms = offset // 1000
            self._app.seek_relative(offset_ms)

    @dbus.service.method(MPRIS2_PLAYER_INTERFACE, in_signature="ox")
    def SetPosition(self, track_id: str, position: int):
        """Set position to absolute value in microseconds."""
        if self._app:
            position_ms = position // 1000
            self._app.seek_absolute(position_ms)

    @dbus.service.method(MPRIS2_PLAYER_INTERFACE, in_signature="s")
    def OpenUri(self, uri: str):
        """Open and play a URI."""
        # Not implemented - we're a library player, not a general media player
        pass

    # ==================== org.freedesktop.DBus.Properties ====================

    @dbus.service.method(DBUS_PROPERTIES_INTERFACE, in_signature="ss", out_signature="v")
    def Get(self, interface: str, prop: str):
        """Get a property value."""
        return self._get_property(interface, prop)

    @dbus.service.method(DBUS_PROPERTIES_INTERFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface: str) -> dbus.Dictionary:
        """Get all properties for an interface."""
        if interface == MPRIS2_INTERFACE:
            return dbus.Dictionary({
                "CanQuit": True,
                "CanRaise": True,
                "CanSetFullscreen": False,
                "Fullscreen": False,
                "HasTrackList": False,
                "Identity": "Wired",
                "DesktopEntry": "wired",
                "SupportedUriSchemes": dbus.Array(["file"], signature="s"),
                "SupportedMimeTypes": dbus.Array([
                    "audio/mpeg",
                    "audio/flac",
                    "audio/ogg",
                    "audio/wav",
                    "audio/x-wav",
                    "audio/mp4",
                    "audio/x-m4a",
                ], signature="s"),
            }, signature="sv")

        elif interface == MPRIS2_PLAYER_INTERFACE:
            return dbus.Dictionary({
                "PlaybackStatus": self._playback_status,
                "LoopStatus": "None",
                "Rate": 1.0,
                "Shuffle": False,
                "Metadata": self._get_metadata(),
                "Volume": self._volume,
                "Position": dbus.Int64(self._position),
                "MinimumRate": 1.0,
                "MaximumRate": 1.0,
                "CanGoNext": True,
                "CanGoPrevious": True,
                "CanPlay": True,
                "CanPause": True,
                "CanSeek": True,
                "CanControl": True,
            }, signature="sv")

        return dbus.Dictionary({}, signature="sv")

    @dbus.service.method(DBUS_PROPERTIES_INTERFACE, in_signature="ssv")
    def Set(self, interface: str, prop: str, value):
        """Set a property value."""
        if interface == MPRIS2_PLAYER_INTERFACE:
            if prop == "Volume" and self._app:
                self._app.set_volume(int(value * 100))

    def _get_property(self, interface: str, prop: str):
        """Get a single property value."""
        props = self.GetAll(interface)
        if prop in props:
            return props[prop]
        raise dbus.exceptions.DBusException(
            f"Property {prop} not found on interface {interface}"
        )

    @dbus.service.signal(DBUS_PROPERTIES_INTERFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface: str, changed: dict, invalidated: list):
        """Signal that properties have changed."""
        pass

    @dbus.service.signal(MPRIS2_PLAYER_INTERFACE, signature="x")
    def Seeked(self, position: int):
        """Signal that playback position was seeked."""
        pass


def create_mpris_service(app) -> MPRIS2Service | None:
    """
    Create and return MPRIS2 service instance.

    Returns None if D-Bus is not available.
    """
    try:
        return MPRIS2Service(app)
    except dbus.exceptions.DBusException as e:
        print(f"MPRIS2: Could not connect to D-Bus: {e}")
        return None
    except Exception as e:
        print(f"MPRIS2: Failed to initialize: {e}")
        return None
