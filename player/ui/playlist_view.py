"""Playlist table view for displaying tracks."""

from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QColor, QPainter, QPen, QKeyEvent, QAction
from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QMenu,
)

from player.core.metadata import Track
from player.core.playlist import Playlist
from player.core.playlist_manager import SavedPlaylist
from player.theme.lainchan import ACCENT, BG_TERTIARY, BG_SECONDARY, BG_PRIMARY, BORDER, TEXT_NORMAL, ACCENT_DIM


class PlayingTrackDelegate(QStyledItemDelegate):
    """Custom delegate to draw 2px left border on playing/selected track."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playing_row = -1

    def set_playing_row(self, row: int):
        self._playing_row = row

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        # Draw default content first
        super().paint(painter, option, index)

        # Draw 2px left accent border on first column only
        if index.column() == 0:
            is_playing = index.row() == self._playing_row
            is_selected = option.state & QStyle.StateFlag.State_Selected

            if is_playing or is_selected:
                painter.save()
                painter.setPen(QPen(QColor(ACCENT), 2))
                painter.drawLine(
                    option.rect.left() + 1,
                    option.rect.top(),
                    option.rect.left() + 1,
                    option.rect.bottom()
                )
                painter.restore()


class PlaylistView(QTableWidget):
    """Table widget for displaying playlist tracks."""

    track_activated = pyqtSignal(int)  # double-click to play
    track_selected = pyqtSignal(int)  # single-click selection
    play_next_requested = pyqtSignal(list)  # add to front of queue (list of indices)
    add_to_queue_requested = pyqtSignal(list)  # add to end of queue (list of indices)
    add_to_playlist_requested = pyqtSignal(list, str)  # track_indices, playlist_id
    create_playlist_with_tracks_requested = pyqtSignal(list)  # track_indices
    remove_from_playlist_requested = pyqtSignal(list)  # track_indices (only when viewing user playlist)
    view_artist_requested = pyqtSignal(str)  # artist name

    COLUMNS = ["", "Title", "Artist", "Album", "Time", "Codec", "Year"]

    def __init__(self):
        super().__init__()
        self._playlist: Playlist | None = None
        self._current_row: int = -1
        self._current_playlist_index: int = -1
        self._delegate = PlayingTrackDelegate(self)
        self.setItemDelegate(self._delegate)
        self._saved_playlists: list[SavedPlaylist] = []
        self._current_view_playlist_id: str | None = None  # None = library, str = user playlist
        self._setup_ui()

    def _setup_ui(self):
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)

        # Column sizing
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # #
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Artist
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Album
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Time
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Codec
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Year

        self.setColumnWidth(0, 24)   # Playing indicator
        self.setColumnWidth(2, 180)  # Artist
        self.setColumnWidth(3, 200)  # Album
        self.setColumnWidth(4, 55)   # Time
        self.setColumnWidth(5, 50)   # Codec
        self.setColumnWidth(6, 45)   # Year

        # Signals
        self.cellDoubleClicked.connect(self._on_double_click)
        self.cellClicked.connect(self._on_click)

        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_playlist(self, playlist: Playlist):
        """Set the playlist to display."""
        self._playlist = playlist
        self._playlist.tracks_changed.connect(self._refresh)
        self._playlist.current_changed.connect(self.set_current_track)
        self._refresh()

    def _refresh(self):
        """Refresh the table contents from playlist."""
        if not self._playlist:
            return

        # Suspend updates for performance with large playlists
        self.setUpdatesEnabled(False)
        self.setSortingEnabled(False)

        self.setRowCount(len(self._playlist))

        for row, track in enumerate(self._playlist.tracks):
            self._set_row(row, track)

        self.setSortingEnabled(True)
        self.setUpdatesEnabled(True)

        # Restore current track highlight
        if self._current_row >= 0:
            self.set_current_track(self._current_row)

    def _set_row(self, row: int, track: Track):
        """Populate a row with track data."""
        items = [
            "",  # Playing indicator column (empty, delegate draws the border)
            track.title,
            track.artist,
            track.album,
            track.format_duration(),
            track.codec,
            track.year,
        ]

        for col, text in enumerate(items):
            item = QTableWidgetItem(text)

            # Right-align time and year columns
            if col in (4, 6):
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            elif col == 0:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )

            # Store track index for retrieval after sorting
            item.setData(Qt.ItemDataRole.UserRole, row)

            self.setItem(row, col, item)

    def _find_visual_row_for_index(self, playlist_index: int) -> int:
        """Find the visual row that contains the track with given playlist index."""
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == playlist_index:
                return row
        return -1

    def set_current_track(self, playlist_index: int):
        """Highlight the currently playing track with 2px left border."""
        old_playlist_index = self._current_playlist_index
        self._current_playlist_index = playlist_index

        # Find visual rows
        old_row = self._find_visual_row_for_index(old_playlist_index) if old_playlist_index >= 0 else -1
        visual_row = self._find_visual_row_for_index(playlist_index)
        self._current_row = visual_row

        # Update delegate and repaint affected rows
        self._delegate.set_playing_row(visual_row)

        # Clear old row's play indicator
        if old_row >= 0:
            item = self.item(old_row, 0)
            if item:
                item.setText("")
            for col in range(self.columnCount()):
                idx = self.model().index(old_row, col)
                self.update(idx)

        # Set new row's play indicator
        if visual_row >= 0:
            item = self.item(visual_row, 0)
            if item:
                item.setText(">")  # Simple play indicator
            for col in range(self.columnCount()):
                idx = self.model().index(visual_row, col)
                self.update(idx)

            # Scroll to visible
            self.scrollToItem(self.item(visual_row, 0))

    def _on_double_click(self, row: int, col: int):
        """Handle double-click to play track."""
        item = self.item(row, 0)
        if item:
            original_index = item.data(Qt.ItemDataRole.UserRole)
            if original_index is not None:
                self.track_activated.emit(original_index)

    def _on_click(self, row: int, col: int):
        """Handle single-click selection."""
        item = self.item(row, 0)
        if item:
            original_index = item.data(Qt.ItemDataRole.UserRole)
            if original_index is not None:
                self.track_selected.emit(original_index)

    def get_selected_index(self) -> int:
        """Get the currently selected track index (first selected if multiple)."""
        selected = self.selectedItems()
        if selected:
            item = selected[0]
            original_index = item.data(Qt.ItemDataRole.UserRole)
            return original_index if original_index is not None else -1
        return -1

    def get_selected_indices(self) -> list[int]:
        """Get all selected track indices."""
        indices = set()
        for item in self.selectedItems():
            original_index = item.data(Qt.ItemDataRole.UserRole)
            if original_index is not None:
                indices.add(original_index)
        return sorted(indices)

    def select_row(self, index: int):
        """Select a row by visual row index."""
        if 0 <= index < self.rowCount():
            self.selectRow(index)

    def select_by_playlist_index(self, playlist_index: int):
        """Select a row by playlist index (handles sorting)."""
        visual_row = self._find_visual_row_for_index(playlist_index)
        if visual_row >= 0:
            self.selectRow(visual_row)
            self.scrollToItem(self.item(visual_row, 0))

    def set_saved_playlists(self, playlists: list[SavedPlaylist]):
        """Update the list of saved playlists for context menu."""
        self._saved_playlists = playlists

    def set_current_view(self, playlist_id: str | None):
        """Set the current view (None for library, playlist_id for user playlist)."""
        self._current_view_playlist_id = playlist_id

    def _show_context_menu(self, position):
        """Show right-click context menu for tracks."""
        item = self.itemAt(position)
        if not item:
            return

        # Get all selected indices
        selected_indices = self.get_selected_indices()
        if not selected_indices:
            return

        # For display purposes
        count = len(selected_indices)
        suffix = f" ({count} tracks)" if count > 1 else ""

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {BG_PRIMARY};
                border: 1px solid {BORDER};
                padding: 4px;
            }}
            QMenu::item {{
                color: {TEXT_NORMAL};
                padding: 6px 20px;
            }}
            QMenu::item:selected {{
                background-color: {ACCENT_DIM};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {BORDER};
                margin: 4px 8px;
            }}
        """)

        play_next_action = QAction(f"Play Next{suffix}  [n]", self)
        play_next_action.triggered.connect(lambda: self.play_next_requested.emit(selected_indices))
        menu.addAction(play_next_action)

        add_queue_action = QAction(f"Add to Queue{suffix}  [a]", self)
        add_queue_action.triggered.connect(lambda: self.add_to_queue_requested.emit(selected_indices))
        menu.addAction(add_queue_action)

        menu.addSeparator()

        # Add to Playlist submenu
        playlist_menu = menu.addMenu(f"Add to Playlist{suffix}")
        playlist_menu.setStyleSheet(menu.styleSheet())

        for playlist in self._saved_playlists:
            action = playlist_menu.addAction(playlist.name)
            action.triggered.connect(
                lambda checked, pid=playlist.id: self.add_to_playlist_requested.emit(selected_indices, pid)
            )

        if self._saved_playlists:
            playlist_menu.addSeparator()

        new_playlist_action = playlist_menu.addAction("+ New Playlist...")
        new_playlist_action.triggered.connect(
            lambda: self.create_playlist_with_tracks_requested.emit(selected_indices)
        )

        # Remove from Playlist (only when viewing a user playlist)
        if self._current_view_playlist_id is not None:
            menu.addSeparator()
            remove_action = QAction(f"Remove from Playlist{suffix}  [Del]", self)
            remove_action.triggered.connect(
                lambda: self.remove_from_playlist_requested.emit(selected_indices)
            )
            menu.addAction(remove_action)

        # View Artist option (only for single selection)
        if count == 1:
            menu.addSeparator()
            artist_item = self.item(item.row(), 2)  # Column 2 is Artist
            if artist_item:
                artist_name = artist_item.text()
                if artist_name and artist_name != "Unknown":
                    view_artist_action = QAction(f"View Artist: {artist_name}", self)
                    view_artist_action.triggered.connect(
                        lambda: self.view_artist_requested.emit(artist_name)
                    )
                    menu.addAction(view_artist_action)

        menu.exec(self.mapToGlobal(position))

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts for queue actions."""
        if event.key() == Qt.Key.Key_N:
            indices = self.get_selected_indices()
            if indices:
                self.play_next_requested.emit(indices)
        elif event.key() == Qt.Key.Key_A:
            indices = self.get_selected_indices()
            if indices:
                self.add_to_queue_requested.emit(indices)
        elif event.key() == Qt.Key.Key_Delete:
            # Remove from playlist (only when viewing a user playlist)
            if self._current_view_playlist_id is not None:
                indices = self.get_selected_indices()
                if indices:
                    self.remove_from_playlist_requested.emit(indices)
        elif event.key() == Qt.Key.Key_G:
            # Go to artist view (single selection only)
            indices = self.get_selected_indices()
            if len(indices) == 1:
                row = self._find_visual_row_for_index(indices[0])
                if row >= 0:
                    artist_item = self.item(row, 2)  # Column 2 is Artist
                    if artist_item:
                        artist_name = artist_item.text()
                        if artist_name and artist_name != "Unknown":
                            self.view_artist_requested.emit(artist_name)
        else:
            super().keyPressEvent(event)
