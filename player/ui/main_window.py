"""Main application window."""

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QFileDialog,
    QApplication,
    QLabel,
    QFrame,
)

from player.core.audio import AudioEngine
from player.core.database import LibraryDatabase
from player.core.library import LibraryScanner
from player.core.playlist import Playlist
from player.core.playlist_manager import PlaylistManager
from player.core.queue import PlaybackQueue
from player.core.metadata import Track
from player.theme.lainchan import get_stylesheet, BG_PRIMARY, BG_SECONDARY, TEXT_NORMAL, TEXT_MUTED, TEXT_DIM, ACCENT, BORDER
from player.ui.player_bar import PlayerBar
from player.ui.playlist_view import PlaylistView
from player.ui.sidebar import Sidebar
from player.ui.search_overlay import SearchOverlay
from player.ui.filter_overlay import FilterOverlay, Filter
from player.ui.artist_overlay import ArtistOverlay
from player.ui.queue_panel import QueuePanel
from player.utils.config import PlayerConfig, load_config, save_config


class LibraryScanWorker(QObject):
    """Worker for background library scanning."""

    progress = pyqtSignal(int, int, str)  # current, total, status
    finished = pyqtSignal(list, int, int)  # tracks, added, removed
    cache_loaded = pyqtSignal(list)  # tracks from cache

    def __init__(self, database: LibraryDatabase):
        super().__init__()
        self._scanner = LibraryScanner(database)
        self._path: str | None = None

    def set_path(self, path: str):
        self._path = path

    def load_cache(self):
        """Fast load from cache - no file I/O."""
        tracks = self._scanner.load_from_cache()
        self.cache_loaded.emit(tracks)

    def scan(self):
        """Incremental scan for changes."""
        if not self._path:
            return
        tracks, added, removed = self._scanner.scan_for_changes(
            self._path,
            lambda cur, tot, status: self.progress.emit(cur, tot, status)
        )
        self.finished.emit(tracks, added, removed)

    def cancel(self):
        self._scanner.cancel()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, initial_path: str | None = None):
        super().__init__()
        self._audio = AudioEngine()
        self._playlist = Playlist()
        self._queue = PlaybackQueue()
        self._config = load_config()
        self._database = LibraryDatabase()
        self._playlist_manager = PlaylistManager(self._database)

        # Library tracks (full library, not filtered)
        self._library_tracks: list[Track] = []

        # Current view mode: None = library, str = playlist_id
        self._current_view: str | None = None

        # Active filters
        self._active_filters: list[Filter] = []

        # Playback state (separate from view)
        self._playback_tracks: list[Track] = []  # Tracks we're playing through
        self._playback_index: int = -1  # Current position in playback
        self._current_track: Track | None = None  # Currently playing track

        # Background scanning thread
        self._scan_thread: QThread | None = None
        self._scan_worker: LibraryScanWorker | None = None

        self._setup_ui()
        self._setup_signals()
        self._setup_shortcuts()
        self._setup_menu()
        self._restore_state()

        # Load initial directory - prefer saved path, then provided path
        load_path = self._config.last_library_path or initial_path
        if load_path:
            QTimer.singleShot(100, lambda: self._load_library(load_path))

    def _setup_ui(self):
        self.setWindowTitle("Wired")
        self.setMinimumSize(1000, 600)
        self.resize(1200, 700)
        self.setStyleSheet(get_stylesheet())

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header = self._create_header()
        main_layout.addWidget(header)

        # Content area (sidebar + playlist)
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        content_layout.addWidget(self._sidebar)

        # Playlist view
        self._playlist_view = PlaylistView()
        self._playlist_view.set_playlist(self._playlist)
        content_layout.addWidget(self._playlist_view, 1)

        # Queue panel (right side, initially collapsed)
        self._queue_panel = QueuePanel(self._queue)
        self._queue_panel.set_playlist(self._playlist)
        content_layout.addWidget(self._queue_panel)

        main_layout.addWidget(content, 1)

        # Player bar at bottom
        self._player_bar = PlayerBar()
        main_layout.addWidget(self._player_bar)

        # Search overlay
        self._search_overlay = SearchOverlay(self)
        self._search_overlay.set_playlist(self._playlist)
        self._search_overlay.track_selected.connect(self._on_search_track_selected)
        self._search_overlay.artist_selected.connect(self._on_view_artist)

        # Filter overlay
        self._filter_overlay = FilterOverlay(self)
        self._filter_overlay.filters_applied.connect(self._on_filters_applied)
        self._filter_overlay.save_as_playlist_requested.connect(self._on_save_filter_as_playlist)

        # Artist overlay
        self._artist_overlay = ArtistOverlay(self)
        self._artist_overlay.album_selected.connect(self._on_artist_album_selected)
        self._artist_overlay.play_all_requested.connect(self._on_artist_play_all)

        # Set initial volume
        self._audio.set_volume(self._player_bar.get_volume())

    def _create_header(self) -> QWidget:
        """Create the header bar with case file aesthetic."""
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
                border-bottom: 1px solid {BORDER};
            }}
            QLabel {{
                background-color: transparent;
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        # Case file title
        title = QLabel("WIRED")
        title.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        layout.addWidget(title)

        layout.addStretch()

        # Scan progress display
        self._scan_label = QLabel("")
        self._scan_label.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
        """)
        layout.addWidget(self._scan_label)

        # Stats display
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-size: 11px;
        """)
        layout.addWidget(self._stats_label)

        return header

    def _update_stats(self):
        """Update the header stats display."""
        total_tracks = len(self._playlist)
        if total_tracks == 0:
            self._stats_label.setText("")
            return

        total_duration = sum(t.duration for t in self._playlist.tracks)
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)

        current_idx = self._playlist.current_index
        if current_idx >= 0:
            pos_text = f"TRACK {current_idx + 1}/{total_tracks}"
        else:
            pos_text = f"{total_tracks} TRACKS"

        if hours > 0:
            duration_text = f"{hours}h {minutes}m"
        else:
            duration_text = f"{minutes}m"

        self._stats_label.setText(f"{pos_text}  |  {duration_text}")

    def _setup_signals(self):
        # Audio engine signals
        self._audio.position_changed.connect(self._on_position_changed)
        self._audio.duration_changed.connect(self._player_bar.set_duration)
        self._audio.state_changed.connect(self._on_state_changed)
        self._audio.track_ended.connect(self._on_track_ended)

        # Player bar signals
        self._player_bar.play_clicked.connect(self._play_current)
        self._player_bar.pause_clicked.connect(self._audio.pause)
        self._player_bar.next_clicked.connect(self._play_next)
        self._player_bar.prev_clicked.connect(self._play_previous)
        self._player_bar.seek_requested.connect(self._audio.seek)
        self._player_bar.volume_changed.connect(self._audio.set_volume)

        # Playlist view signals
        self._playlist_view.track_activated.connect(self._play_track)
        self._playlist_view.play_next_requested.connect(self._on_play_next_requested)
        self._playlist_view.add_to_queue_requested.connect(self._on_add_to_queue_requested)
        self._playlist_view.add_to_playlist_requested.connect(self._on_add_to_playlist)
        self._playlist_view.create_playlist_with_tracks_requested.connect(self._on_create_playlist_with_tracks)
        self._playlist_view.remove_from_playlist_requested.connect(self._on_remove_from_playlist)
        self._playlist_view.view_artist_requested.connect(self._on_view_artist)

        # Queue panel signals
        self._queue_panel.track_activated.connect(self._play_track_from_queue)
        self._queue_panel.shuffle_toggled.connect(self._on_shuffle_toggled)

        # Playlist signals
        self._playlist.current_changed.connect(self._on_current_changed)

        # Sidebar signals (playlist management)
        self._sidebar.playlist_selected.connect(self._on_playlist_selected)
        self._sidebar.playlist_create_requested.connect(self._on_playlist_create)
        self._sidebar.playlist_rename_requested.connect(self._on_playlist_rename)
        self._sidebar.playlist_delete_requested.connect(self._on_playlist_delete)

        # Playlist manager signals
        self._playlist_manager.playlists_changed.connect(self._refresh_playlists)

    def _setup_shortcuts(self):
        # Space - play/pause
        space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        space.setContext(Qt.ShortcutContext.ApplicationShortcut)
        space.activated.connect(self._toggle_play_pause)

        # Right arrow - next
        right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        right.setContext(Qt.ShortcutContext.ApplicationShortcut)
        right.activated.connect(self._play_next)

        # Left arrow - previous
        left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        left.setContext(Qt.ShortcutContext.ApplicationShortcut)
        left.activated.connect(self._play_previous)

        # + key - volume up
        vol_up = QShortcut(QKeySequence(Qt.Key.Key_Plus), self)
        vol_up.setContext(Qt.ShortcutContext.ApplicationShortcut)
        vol_up.activated.connect(lambda: self._adjust_volume(5))

        # = key - volume up (without shift)
        vol_up2 = QShortcut(QKeySequence(Qt.Key.Key_Equal), self)
        vol_up2.setContext(Qt.ShortcutContext.ApplicationShortcut)
        vol_up2.activated.connect(lambda: self._adjust_volume(5))

        # - key - volume down
        vol_down = QShortcut(QKeySequence(Qt.Key.Key_Minus), self)
        vol_down.setContext(Qt.ShortcutContext.ApplicationShortcut)
        vol_down.activated.connect(lambda: self._adjust_volume(-5))

        # Enter - play selected
        enter = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        enter.setContext(Qt.ShortcutContext.ApplicationShortcut)
        enter.activated.connect(self._play_selected)

        # Ctrl+O - open folder (stateless)
        open_folder = QShortcut(QKeySequence.StandardKey.Open, self)
        open_folder.setContext(Qt.ShortcutContext.ApplicationShortcut)
        open_folder.activated.connect(self._open_folder_stateless)

        # Ctrl+Q - quit
        quit_app = QShortcut(QKeySequence.StandardKey.Quit, self)
        quit_app.setContext(Qt.ShortcutContext.ApplicationShortcut)
        quit_app.activated.connect(self.close)

        # f - open search (fast access)
        search = QShortcut(QKeySequence(Qt.Key.Key_F), self)
        search.setContext(Qt.ShortcutContext.ApplicationShortcut)
        search.activated.connect(self._open_search)

        # / - open search (vim-style)
        search_slash = QShortcut(QKeySequence(Qt.Key.Key_Slash), self)
        search_slash.setContext(Qt.ShortcutContext.ApplicationShortcut)
        search_slash.activated.connect(self._open_search)

        # Ctrl+F - open filter
        filter_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        filter_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        filter_shortcut.activated.connect(self._open_filter)

        # q - toggle queue panel
        queue_toggle = QShortcut(QKeySequence(Qt.Key.Key_Q), self)
        queue_toggle.setContext(Qt.ShortcutContext.ApplicationShortcut)
        queue_toggle.activated.connect(self._toggle_queue)

        # s - toggle shuffle
        shuffle_toggle = QShortcut(QKeySequence(Qt.Key.Key_S), self)
        shuffle_toggle.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shuffle_toggle.activated.connect(self._toggle_shuffle)

        # Escape - clear filters (when not in overlay)
        clear_filter = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        clear_filter.setContext(Qt.ShortcutContext.ApplicationShortcut)
        clear_filter.activated.connect(self._clear_filters_if_active)

    def _open_search(self):
        """Open the search overlay."""
        self._search_overlay.set_library_tracks(self._library_tracks)
        self._search_overlay.show_search()

    def _on_search_track_selected(self, index: int):
        """Handle track selection from search - play directly without switching view."""
        if 0 <= index < len(self._playlist):
            track = self._playlist[index]
            self._play_track_direct(track)
            # Select the track in the view so arrow keys work from here
            self._playlist_view.select_by_playlist_index(index)

    def _open_filter(self):
        """Open the filter overlay."""
        self._filter_overlay.set_tracks(self._library_tracks)
        self._filter_overlay.set_filters(self._active_filters)
        self._filter_overlay.show_filter()

    def _clear_filters_if_active(self):
        """Clear filters if any are active."""
        if self._active_filters:
            self._active_filters = []
            self._apply_current_view()

    def _toggle_queue(self):
        """Toggle queue panel visibility."""
        self._queue_panel.toggle()

    def _toggle_shuffle(self):
        """Toggle shuffle mode."""
        enabled = not self._playlist.is_shuffled()
        self._playlist.shuffle(enabled)

    def _on_shuffle_toggled(self, enabled: bool):
        """Handle shuffle toggle from queue panel."""
        self._playlist.shuffle(enabled)

    def _on_play_next_requested(self, indices: list[int]):
        """Handle 'Play Next' request from playlist view."""
        # Add in reverse order so first selected plays first
        for index in reversed(indices):
            if 0 <= index < len(self._playlist):
                track = self._playlist[index]
                self._queue.play_next(track)

    def _on_add_to_queue_requested(self, indices: list[int]):
        """Handle 'Add to Queue' request from playlist view."""
        for index in indices:
            if 0 <= index < len(self._playlist):
                track = self._playlist[index]
                self._queue.add_to_queue(track)

    def _play_track_direct(self, track):
        """Play a specific track directly (from queue or search)."""
        self._current_track = track
        self._audio.play(str(track.filepath))
        self._update_ui_for_track(track)
        self._sync_view_highlight()
        # Update queue panel (queued track was consumed, so upcoming preview updates)
        self._update_queue_panel_playback()

    def _sync_view_highlight(self):
        """Sync the view highlight with the currently playing track."""
        if self._current_track:
            # Try to find track in current view to update highlight
            for i, t in enumerate(self._playlist.tracks):
                if t.filepath == self._current_track.filepath:
                    self._playlist.set_current(i)
                    return
            # Track not in current view - clear highlight
            self._playlist.set_current(-1)

    def _update_queue_panel_playback(self):
        """Update the queue panel with current playback state."""
        self._queue_panel.set_playback_state(self._playback_tracks, self._playback_index)

    def _play_track_from_queue(self, track):
        """Play a track activated from the queue panel."""
        # Remove from queue
        for i, t in enumerate(self._queue.tracks):
            if t.filepath == track.filepath:
                self._queue.remove(i)
                break
        self._play_track_direct(track)

    def _setup_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open Folder...  [Ctrl+O]", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_folder_stateless)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        import_m3u_action = QAction("Import Playlist (M3U)...  [Ctrl+I]", self)
        import_m3u_action.setShortcut(QKeySequence("Ctrl+I"))
        import_m3u_action.triggered.connect(self._import_m3u)
        file_menu.addAction(import_m3u_action)

        export_m3u_action = QAction("Export Current as M3U...", self)
        export_m3u_action.triggered.connect(self._export_m3u)
        file_menu.addAction(export_m3u_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Library menu
        library_menu = menubar.addMenu("Library")

        set_library_action = QAction("Set Library Folder...", self)
        set_library_action.triggered.connect(self._set_library_folder)
        library_menu.addAction(set_library_action)

        refresh_action = QAction("Refresh Library  [F5]", self)
        refresh_action.setShortcut(QKeySequence(Qt.Key.Key_F5))
        refresh_action.triggered.connect(self._refresh_library)
        library_menu.addAction(refresh_action)

        # Playback menu
        playback_menu = menubar.addMenu("Playback")

        play_action = QAction("Play/Pause  [Space]", self)
        play_action.triggered.connect(self._toggle_play_pause)
        playback_menu.addAction(play_action)

        next_action = QAction("Next Track  [Right]", self)
        next_action.triggered.connect(self._play_next)
        playback_menu.addAction(next_action)

        prev_action = QAction("Previous Track  [Left]", self)
        prev_action.triggered.connect(self._play_previous)
        playback_menu.addAction(prev_action)

    def _load_library(self, path: str):
        """Load library - fast cache load, then background scan for changes."""
        self._config.last_library_path = path

        # Setup worker and thread
        self._scan_thread = QThread()
        self._scan_worker = LibraryScanWorker(self._database)
        self._scan_worker.set_path(path)
        self._scan_worker.moveToThread(self._scan_thread)

        # Connect signals
        self._scan_worker.cache_loaded.connect(self._on_cache_loaded)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_thread.started.connect(self._scan_worker.load_cache)

        # Start the thread
        self._scan_thread.start()

    def _on_cache_loaded(self, tracks: list[Track]):
        """Handle fast cache load completion."""
        if tracks:
            self._library_tracks = tracks
            self._playlist.clear()
            self._playlist.add_tracks(tracks)
            self._playlist.sort("album")
            self._update_stats()
            self._restore_queue()
            self._restore_shuffle()
            self._refresh_playlists()
            self._scan_label.setText(f"Loaded {len(tracks)} tracks from cache")

        # Now start the incremental scan for changes
        if self._scan_worker:
            QTimer.singleShot(100, self._scan_worker.scan)

    def _on_scan_progress(self, current: int, total: int, status: str):
        """Handle scan progress update."""
        if total > 0:
            self._scan_label.setText(status)
        else:
            self._scan_label.setText(status)

    def _on_scan_finished(self, tracks: list[Track], added: int, removed: int):
        """Handle scan completion."""
        self._library_tracks = tracks

        # Update playlist with new/modified tracks
        if added > 0 or removed > 0:
            # Only update view if we're showing library
            if self._current_view is None:
                self._playlist.clear()
                self._playlist.add_tracks(tracks)
                self._playlist.sort("album")
            self._scan_label.setText(f"+{added} / -{removed} changes")
            # Clear after a delay
            QTimer.singleShot(3000, lambda: self._scan_label.setText(""))
        else:
            self._scan_label.setText("Library up to date")
            QTimer.singleShot(2000, lambda: self._scan_label.setText(""))

        self._update_stats()
        self._restore_queue()
        self._restore_shuffle()
        self._refresh_playlists()

        # Cleanup thread
        if self._scan_thread:
            self._scan_thread.quit()
            self._scan_thread.wait()
            self._scan_thread = None
            self._scan_worker = None

    def _refresh_library(self):
        """Manually refresh the library."""
        if self._config.last_library_path:
            # If a scan is already running, cancel it
            if self._scan_worker:
                self._scan_worker.cancel()
            if self._scan_thread:
                self._scan_thread.quit()
                self._scan_thread.wait()
                self._scan_thread = None
                self._scan_worker = None

            # Start a fresh scan (not from cache)
            self._scan_thread = QThread()
            self._scan_worker = LibraryScanWorker(self._database)
            self._scan_worker.set_path(self._config.last_library_path)
            self._scan_worker.moveToThread(self._scan_thread)

            self._scan_worker.progress.connect(self._on_scan_progress)
            self._scan_worker.finished.connect(self._on_scan_finished)
            self._scan_thread.started.connect(self._scan_worker.scan)

            self._scan_label.setText("Refreshing...")
            self._scan_thread.start()

    def _set_library_folder(self):
        """Set the library folder (cached in SQLite)."""
        path = QFileDialog.getExistingDirectory(
            self, "Set Library Folder", str(Path.home())
        )
        if path:
            # Clear database when switching libraries
            self._database.clear()
            self._load_library(path)

    def _open_folder_stateless(self):
        """Open a folder temporarily without caching (stateless)."""
        from player.core.library import LibraryScanner
        path = QFileDialog.getExistingDirectory(
            self, "Open Folder", str(Path.home())
        )
        if path:
            # Don't save to config or database - just load directly
            self._scan_label.setText("Loading folder...")
            QApplication.processEvents()

            scanner = LibraryScanner(self._database)
            tracks = scanner.scan_directory(path)

            if tracks:
                self._playlist.clear()
                self._playlist.add_tracks(tracks)
                self._playlist.sort("album")
                self._update_stats()
                self._queue.clear()

            self._scan_label.setText(f"Opened {len(tracks)} tracks (not cached)")
            QTimer.singleShot(3000, lambda: self._scan_label.setText(""))

    def _play_track(self, index: int):
        """Play a specific track by index from current view."""
        if 0 <= index < len(self._playlist):
            track = self._playlist[index]
            # Set up playback from current view
            self._playback_tracks = list(self._playlist.tracks)
            self._playback_index = index
            self._current_track = track
            self._playlist.set_current(index)  # Update view highlight
            self._audio.play(str(track.filepath))
            self._update_ui_for_track(track)
            self._update_queue_panel_playback()

    def _play_current(self):
        """Play or resume current track."""
        if self._audio.get_state() == "paused":
            self._audio.pause()  # Toggle resume
        elif self._current_track:
            self._audio.play(str(self._current_track.filepath))
        elif len(self._playlist) > 0:
            self._play_track(0)

    def _play_next(self):
        """Play next track - check queue first, then playback list."""
        queued_track = self._queue.pop_next()
        if queued_track:
            self._play_track_direct(queued_track)
        elif self._playback_tracks and self._playback_index >= 0:
            # Play next from playback list
            next_index = self._playback_index + 1
            if next_index < len(self._playback_tracks):
                self._playback_index = next_index
                track = self._playback_tracks[next_index]
                self._current_track = track
                self._audio.play(str(track.filepath))
                self._update_ui_for_track(track)
                self._sync_view_highlight()
                self._update_queue_panel_playback()

    def _play_previous(self):
        """Play previous track from playback list."""
        if self._playback_tracks and self._playback_index > 0:
            self._playback_index -= 1
            track = self._playback_tracks[self._playback_index]
            self._current_track = track
            self._audio.play(str(track.filepath))
            self._update_ui_for_track(track)
            self._sync_view_highlight()
            self._update_queue_panel_playback()

    def _play_selected(self):
        """Play currently selected track in playlist."""
        index = self._playlist_view.get_selected_index()
        if index >= 0:
            self._play_track(index)

    def _toggle_play_pause(self):
        """Toggle between play and pause."""
        state = self._audio.get_state()
        if state == "playing":
            self._audio.pause()
        elif state == "paused":
            self._audio.pause()  # Toggle resume
        else:
            self._play_current()

    def _adjust_volume(self, delta: int):
        """Adjust volume by delta."""
        current = self._player_bar.get_volume()
        new_vol = max(0, min(100, current + delta))
        self._player_bar.set_volume(new_vol)

    def _update_ui_for_track(self, track):
        """Update all UI elements for current track."""
        # Load album art on-demand (not stored in cache)
        track.load_album_art()
        self._sidebar.set_track(track)
        self._player_bar.set_track_info(
            track.title,
            track.artist,
            track.album,
            track.year,
            track.codec,
            track.format_sample_info(),
            track.format_bitrate(),
        )

    def _on_position_changed(self, position: float):
        """Handle position update from audio engine."""
        current_ms = self._audio.get_time_ms()
        self._player_bar.set_position(position, current_ms)

    def _on_state_changed(self, state: str):
        """Handle state change from audio engine."""
        self._player_bar.set_playing(state == "playing")

    def _on_track_ended(self):
        """Handle track end - play next (queue or playlist)."""
        self._play_next()

    def _on_current_changed(self, index: int):
        """Handle playlist current track change."""
        self._playlist_view.set_current_track(index)
        self._update_stats()

    def _restore_state(self):
        """Restore saved window state and settings."""
        # Window geometry
        self.setGeometry(
            self._config.window_x,
            self._config.window_y,
            self._config.window_width,
            self._config.window_height,
        )

        # Volume
        self._player_bar.set_volume(self._config.volume)
        self._audio.set_volume(self._config.volume)

        # Queue panel visibility
        if self._config.queue_panel_visible:
            self._queue_panel.expand()

        # Shuffle state (restored after library load triggers it)

    def _restore_shuffle(self):
        """Restore shuffle state from config."""
        if self._config.shuffle_enabled:
            self._playlist.shuffle(True)
            self._queue_panel.set_shuffle_enabled(True)

    def _restore_queue(self):
        """Restore queue from saved file paths."""
        if not self._config.queue_paths:
            return

        # Build a path-to-track lookup from playlist
        path_to_track = {str(t.filepath): t for t in self._playlist.tracks}

        # Restore tracks that still exist in the library
        for path in self._config.queue_paths:
            if path in path_to_track:
                self._queue.add_to_queue(path_to_track[path])

        # Clear saved paths so we don't re-add on next library load
        self._config.queue_paths = []

    def _save_state(self):
        """Save current state to config."""
        # Window geometry
        geo = self.geometry()
        self._config.window_x = geo.x()
        self._config.window_y = geo.y()
        self._config.window_width = geo.width()
        self._config.window_height = geo.height()

        # Volume
        self._config.volume = self._player_bar.get_volume()

        # Current track
        self._config.last_track_index = self._playlist.current_index

        # Queue
        self._config.queue_paths = self._queue.get_filepaths()
        self._config.queue_panel_visible = self._queue_panel.is_expanded()

        # Shuffle
        self._config.shuffle_enabled = self._playlist.is_shuffled()

        save_config(self._config)

    def closeEvent(self, event):
        """Handle window close - save state."""
        # Cancel any ongoing scan
        if self._scan_worker:
            self._scan_worker.cancel()
        if self._scan_thread:
            self._scan_thread.quit()
            self._scan_thread.wait()

        self._save_state()
        self._audio.stop()
        event.accept()

    # --- Playlist management ---

    def _refresh_playlists(self):
        """Refresh the playlist list in sidebar and playlist view."""
        playlists = self._playlist_manager.get_all()
        self._sidebar.set_playlists(playlists)
        self._sidebar.set_library_count(len(self._library_tracks))
        self._sidebar.set_active_playlist(self._current_view)
        self._playlist_view.set_saved_playlists(playlists)

    def _on_playlist_selected(self, playlist_id: str):
        """Handle playlist selection from sidebar."""
        if playlist_id == "library":
            self._switch_to_library()
        else:
            self._switch_to_playlist(playlist_id)

    def _switch_to_library(self):
        """Switch view to full library."""
        self._current_view = None
        self._sidebar.set_active_playlist(None)
        self._playlist_view.set_current_view(None)
        self._apply_current_view()

    def _switch_to_playlist(self, playlist_id: str):
        """Switch view to a saved playlist."""
        self._current_view = playlist_id
        self._sidebar.set_active_playlist(playlist_id)
        self._playlist_view.set_current_view(playlist_id)
        self._active_filters = []  # Clear filters when switching playlists
        self._apply_current_view()

    def _apply_current_view(self):
        """Apply the current view (library or playlist) with filters."""
        # Determine base tracks
        if self._current_view is None:
            base_tracks = self._library_tracks
        else:
            base_tracks = self._playlist_manager.get_tracks(self._current_view, self._library_tracks)

        # Apply filters
        if self._active_filters:
            tracks = [t for t in base_tracks if all(f.matches(t) for f in self._active_filters)]
        else:
            tracks = base_tracks

        # Show loading indicator
        self._playlist.clear()
        if len(tracks) > 1000:
            self._scan_label.setText(f"Loading {len(tracks):,} tracks...")
            QApplication.processEvents()

        # Load after UI updates
        QTimer.singleShot(10, lambda: self._finish_apply_view(tracks))

    def _finish_apply_view(self, tracks: list[Track]):
        """Complete view application."""
        self._playlist.add_tracks(tracks)
        if self._current_view is None and not self._active_filters:
            self._playlist.sort("album")
        self._update_stats()
        self._update_filter_indicator()
        self._scan_label.setText("")
        # Sync highlight with currently playing track
        self._sync_view_highlight()

    def _on_filters_applied(self, filters: list[Filter]):
        """Handle filters from filter overlay."""
        self._active_filters = filters
        self._apply_current_view()

    def _update_filter_indicator(self):
        """Update the filter indicator in the header."""
        if self._active_filters:
            filter_text = ", ".join(str(f) for f in self._active_filters)
            count = len(self._playlist)
            self._scan_label.setText(f"FILTERED: {filter_text}  ({count:,})")
        # Don't clear - let other operations manage the label

    def _on_playlist_create(self):
        """Handle create playlist request."""
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name.strip():
            self._playlist_manager.create(name.strip())

    def _on_playlist_rename(self, playlist_id: str, new_name: str):
        """Handle playlist rename request."""
        self._playlist_manager.rename(playlist_id, new_name)

    def _on_playlist_delete(self, playlist_id: str):
        """Handle playlist delete request."""
        from PyQt6.QtWidgets import QMessageBox
        playlist = self._playlist_manager.get(playlist_id)
        if not playlist:
            return

        reply = QMessageBox.question(
            self,
            "Delete Playlist",
            f"Delete playlist '{playlist.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Switch to library if we're deleting the current view
            if self._current_view == playlist_id:
                self._switch_to_library()
            self._playlist_manager.delete(playlist_id)

    def _on_add_to_playlist(self, track_indices: list[int], playlist_id: str):
        """Handle add tracks to playlist request."""
        tracks = []
        for index in track_indices:
            if 0 <= index < len(self._playlist):
                tracks.append(self._playlist[index])
        if tracks:
            self._playlist_manager.add_tracks(playlist_id, tracks)
            self._refresh_playlists()

    def _on_create_playlist_with_tracks(self, track_indices: list[int]):
        """Handle create new playlist with tracks."""
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name.strip():
            playlist = self._playlist_manager.create(name.strip())
            tracks = []
            for index in track_indices:
                if 0 <= index < len(self._playlist):
                    tracks.append(self._playlist[index])
            if tracks:
                self._playlist_manager.add_tracks(playlist.id, tracks)

    def _on_remove_from_playlist(self, track_indices: list[int]):
        """Handle remove tracks from current playlist."""
        if self._current_view is None:
            return  # Can't remove from library

        tracks = []
        for index in track_indices:
            if 0 <= index < len(self._playlist):
                tracks.append(self._playlist[index])
        if tracks:
            self._playlist_manager.remove_tracks(self._current_view, tracks)
            # Refresh the view
            self._apply_current_view()
            self._refresh_playlists()

    # --- M3U Import/Export ---

    def _import_m3u(self):
        """Import a playlist from M3U file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import Playlist",
            str(Path.home()),
            "M3U Playlists (*.m3u *.m3u8);;All Files (*)"
        )
        if filepath:
            playlist = self._playlist_manager.import_m3u(Path(filepath), self._library_tracks)
            if playlist:
                self._scan_label.setText(f"Imported '{playlist.name}' ({playlist.track_count} tracks)")
                QTimer.singleShot(3000, lambda: self._scan_label.setText(""))
            else:
                self._scan_label.setText("Import failed - no matching tracks found")
                QTimer.singleShot(3000, lambda: self._scan_label.setText(""))

    def _export_m3u(self):
        """Export current view as M3U file."""
        # Determine default filename
        if self._current_view:
            playlist = self._playlist_manager.get(self._current_view)
            default_name = playlist.name if playlist else "playlist"
        else:
            default_name = "library"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Playlist",
            str(Path.home() / f"{default_name}.m3u"),
            "M3U Playlist (*.m3u);;Extended M3U (*.m3u8)"
        )
        if filepath:
            path = Path(filepath)
            # Write M3U directly for current view
            with open(path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                f.write(f"#PLAYLIST:{default_name}\n")
                for track in self._playlist.tracks:
                    duration = int(track.duration)
                    f.write(f"#EXTINF:{duration},{track.artist} - {track.title}\n")
                    f.write(f"{track.filepath}\n")

            self._scan_label.setText(f"Exported {len(self._playlist)} tracks to {path.name}")
            QTimer.singleShot(3000, lambda: self._scan_label.setText(""))

    def _on_save_filter_as_playlist(self, filters: list[Filter]):
        """Handle save filter results as playlist."""
        from PyQt6.QtWidgets import QInputDialog

        # Get filtered tracks
        if self._current_view is None:
            base_tracks = self._library_tracks
        else:
            base_tracks = self._playlist_manager.get_tracks(self._current_view, self._library_tracks)

        tracks = [t for t in base_tracks if all(f.matches(t) for f in filters)]

        if not tracks:
            self._scan_label.setText("No matching tracks to save")
            QTimer.singleShot(2000, lambda: self._scan_label.setText(""))
            return

        # Generate default name from filters
        default_name = " + ".join(str(f) for f in filters)

        name, ok = QInputDialog.getText(
            self, "Save as Playlist", "Playlist name:", text=default_name
        )
        if ok and name.strip():
            playlist = self._playlist_manager.create(name.strip())
            self._playlist_manager.add_tracks(playlist.id, tracks)
            self._scan_label.setText(f"Created playlist '{name.strip()}' with {len(tracks)} tracks")
            QTimer.singleShot(3000, lambda: self._scan_label.setText(""))

    # --- Artist Overlay ---

    def _on_view_artist(self, artist: str):
        """Show artist overlay for the given artist."""
        self._artist_overlay.set_tracks(self._library_tracks)
        self._artist_overlay.show_artist(artist)

    def _on_artist_album_selected(self, artist: str, album: str):
        """Handle album selection from artist overlay - apply filters."""
        self._active_filters = [
            Filter(field="artist", value=artist),
            Filter(field="album", value=album),
        ]
        self._apply_current_view()

    def _on_artist_play_all(self, artist: str):
        """Handle 'Play All' from artist overlay."""
        # Filter to just this artist and play
        self._active_filters = [Filter(field="artist", value=artist)]
        self._apply_current_view()
        # Start playing from the first track
        if len(self._playlist) > 0:
            self._play_track(0)
