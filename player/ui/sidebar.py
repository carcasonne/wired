"""Sidebar with album art, track metadata, and playlist list."""

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QMouseEvent, QAction, QFontMetrics, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMenu,
    QInputDialog,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from player.core.metadata import Track
from player.core.playlist_manager import SavedPlaylist
from player.theme.lainchan import (
    BG_PRIMARY, BG_SECONDARY, BG_TERTIARY,
    TEXT_NORMAL, TEXT_MUTED, TEXT_DIM,
    ACCENT, ACCENT_DIM, BORDER,
)


class PlaylistItemDelegate(QStyledItemDelegate):
    """Delegate that elides text and handles active item highlighting."""

    # Custom role for active state
    ACTIVE_ROLE = Qt.ItemDataRole.UserRole + 1

    def paint(self, painter, option, index):
        painter.save()

        is_active = index.data(self.ACTIVE_ROLE)

        # Background
        if is_active:
            painter.fillRect(option.rect, QColor(BG_TERTIARY))
            # Draw 2px accent border on left
            painter.fillRect(
                option.rect.left(), option.rect.top(),
                2, option.rect.height(),
                QColor(ACCENT)
            )

        # Text color
        if is_active:
            painter.setPen(QColor(TEXT_NORMAL))
        else:
            painter.setPen(QColor(TEXT_MUTED))

        # Get elided text
        text = index.data(Qt.ItemDataRole.DisplayRole)
        available_width = option.rect.width() - 24  # 12px padding each side
        metrics = QFontMetrics(option.font)
        elided = metrics.elidedText(text, Qt.TextElideMode.ElideRight, available_width)

        # Draw text with padding
        text_rect = option.rect.adjusted(12, 0, -12, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)

        # No bottom border - cleaner look

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 28)


class Sidebar(QWidget):
    """Sidebar displaying album art, current track info, and playlist list."""

    # Signals
    playlist_selected = pyqtSignal(str)  # playlist_id or "library" for full library
    playlist_create_requested = pyqtSignal()
    playlist_rename_requested = pyqtSignal(str, str)  # playlist_id, new_name
    playlist_delete_requested = pyqtSignal(str)  # playlist_id

    def __init__(self):
        super().__init__()
        self._current_playlist_id: str | None = None  # None = library
        self._library_track_count = 0
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(280)
        self.setObjectName("sidebar")
        self.setStyleSheet(f"""
            QWidget#sidebar {{
                background-color: {BG_PRIMARY};
                border-right: 1px solid {BORDER};
            }}
            QWidget {{
                background-color: {BG_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Album art section
        self._setup_album_section(layout)

        # Metadata section
        self._setup_metadata_section(layout)

        # Playlists section
        self._setup_playlist_section(layout)

    def _setup_album_section(self, parent_layout: QVBoxLayout):
        """Setup the album art display section."""
        # Section header - aligned with main header (32px)
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        label = QLabel("CURRENT")
        label.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(label)
        header_layout.addStretch()

        parent_layout.addWidget(header)

        # Album art container
        art_container = QFrame()
        art_container.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
            }}
        """)
        art_layout = QVBoxLayout(art_container)
        art_layout.setContentsMargins(12, 12, 12, 12)
        art_layout.setSpacing(0)

        # Album art
        self._art_label = QLabel()
        self._art_label.setFixedSize(254, 254)
        self._art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._art_label.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_SECONDARY};
                border: 1px solid {BORDER};
            }}
        """)
        self._set_placeholder_art()
        art_layout.addWidget(self._art_label)

        parent_layout.addWidget(art_container)

    def _setup_metadata_section(self, parent_layout: QVBoxLayout):
        """Setup the metadata display section with explicit labels."""
        # Section header
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        label = QLabel("MEDIA INFO")
        label.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(label)
        header_layout.addStretch()

        parent_layout.addWidget(header)

        # Metadata grid
        meta_container = QFrame()
        meta_container.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
            }}
        """)
        meta_layout = QVBoxLayout(meta_container)
        meta_layout.setContentsMargins(12, 8, 12, 8)
        meta_layout.setSpacing(4)

        # Grid for label-value pairs
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(2)

        # Row 0: ALBUM
        album_label = QLabel("ALBUM")
        album_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        grid.addWidget(album_label, 0, 0, Qt.AlignmentFlag.AlignTop)

        self._album_value = QLabel("—")
        self._album_value.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 12px;")
        self._album_value.setWordWrap(True)
        grid.addWidget(self._album_value, 0, 1)

        # Row 1: YEAR
        year_label = QLabel("YEAR")
        year_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        grid.addWidget(year_label, 1, 0)

        self._year_value = QLabel("—")
        self._year_value.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 12px;")
        grid.addWidget(self._year_value, 1, 1)

        # Row 2: CODEC
        codec_label = QLabel("CODEC")
        codec_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        grid.addWidget(codec_label, 2, 0)

        self._codec_value = QLabel("—")
        self._codec_value.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 12px;")
        grid.addWidget(self._codec_value, 2, 1)

        # Row 3: SAMPLE
        sample_label = QLabel("SAMPLE")
        sample_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        grid.addWidget(sample_label, 3, 0)

        self._sample_value = QLabel("—")
        self._sample_value.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 12px;")
        grid.addWidget(self._sample_value, 3, 1)

        # Row 4: BITRATE
        bitrate_label = QLabel("BITRATE")
        bitrate_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        grid.addWidget(bitrate_label, 4, 0)

        self._bitrate_value = QLabel("—")
        self._bitrate_value.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 12px;")
        grid.addWidget(self._bitrate_value, 4, 1)

        # Make value column stretch
        grid.setColumnStretch(1, 1)

        meta_layout.addLayout(grid)
        parent_layout.addWidget(meta_container)

    def _setup_playlist_section(self, parent_layout: QVBoxLayout):
        """Setup the playlist list section."""
        # Section header
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        label = QLabel("PLAYLISTS")
        label.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(label)
        header_layout.addStretch()

        # New playlist button in header
        new_btn = QLabel("[+]")
        new_btn.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-size: 11px;
        """)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.mousePressEvent = lambda e: self.playlist_create_requested.emit()
        header_layout.addWidget(new_btn)

        parent_layout.addWidget(header)

        # Playlist list container
        list_container = QFrame()
        list_container.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SECONDARY};
            }}
        """)
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        # Playlist list
        self._playlist_list = QListWidget()
        self._playlist_list.setItemDelegate(PlaylistItemDelegate(self._playlist_list))
        self._playlist_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._playlist_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_SECONDARY};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                color: {TEXT_MUTED};
                padding: 6px 12px;
                border: none;
            }}
            QListWidget::item:hover {{
                background-color: {BG_TERTIARY};
            }}
        """)
        self._playlist_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._playlist_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._playlist_list.customContextMenuRequested.connect(self._show_playlist_context_menu)
        self._playlist_list.itemClicked.connect(self._on_playlist_clicked)
        self._playlist_list.itemDoubleClicked.connect(self._on_playlist_double_clicked)
        list_layout.addWidget(self._playlist_list, 1)

        parent_layout.addWidget(list_container, 1)

    def _set_placeholder_art(self):
        """Set placeholder when no album art available."""
        self._art_label.setText("NO SIGNAL")
        self._art_label.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_SECONDARY};
                border: 1px solid {BORDER};
                color: {TEXT_DIM};
                font-size: 11px;
                letter-spacing: 2px;
            }}
        """)

    def set_track(self, track: Track):
        """Update sidebar with track information."""
        # Album art
        if track.album_art:
            pixmap = QPixmap()
            pixmap.loadFromData(track.album_art)
            scaled = pixmap.scaled(
                254, 254,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._art_label.setPixmap(scaled)
            self._art_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {BG_SECONDARY};
                    border: 1px solid {BORDER};
                }}
            """)
        else:
            self._set_placeholder_art()

        # Metadata with explicit formatting
        self._album_value.setText(track.album if track.album != "Unknown" else "—")
        self._year_value.setText(track.year if track.year else "—")
        self._codec_value.setText(track.codec.upper() if track.codec != "Unknown" else "—")

        # Sample info
        if track.sample_rate > 0 or track.bit_depth > 0:
            sample_parts = []
            if track.bit_depth > 0:
                sample_parts.append(f"{track.bit_depth}-BIT")
            if track.sample_rate > 0:
                sr = track.sample_rate / 1000
                if sr == int(sr):
                    sample_parts.append(f"{int(sr)} KHZ")
                else:
                    sample_parts.append(f"{sr:.1f} KHZ")
            self._sample_value.setText(" / ".join(sample_parts))
        else:
            self._sample_value.setText("—")

        # Bitrate
        if track.bitrate > 0:
            self._bitrate_value.setText(f"{track.bitrate} KBPS")
        else:
            self._bitrate_value.setText("—")

    def clear(self):
        """Clear all track information."""
        self._set_placeholder_art()
        self._album_value.setText("—")
        self._year_value.setText("—")
        self._codec_value.setText("—")
        self._sample_value.setText("—")
        self._bitrate_value.setText("—")

    def set_library_count(self, count: int):
        """Set the library track count."""
        self._library_track_count = count
        self._refresh_playlist_list()

    def set_playlists(self, playlists: list[SavedPlaylist]):
        """Update the playlist list."""
        self._playlists = playlists
        self._refresh_playlist_list()

    def _refresh_playlist_list(self):
        """Refresh the playlist list display."""
        self._playlist_list.clear()

        # Library item (always first)
        library_item = QListWidgetItem()
        count_str = f"{self._library_track_count:,}" if self._library_track_count else "0"
        library_item.setText(f"LIBRARY  [{count_str}]")
        library_item.setData(Qt.ItemDataRole.UserRole, "library")
        library_item.setData(PlaylistItemDelegate.ACTIVE_ROLE, self._current_playlist_id is None)
        library_item.setToolTip(f"{self._library_track_count:,} tracks")
        self._playlist_list.addItem(library_item)

        # User playlists
        for playlist in getattr(self, "_playlists", []):
            item = QListWidgetItem()
            item.setText(f"{playlist.name}  [{playlist.track_count}]")
            item.setData(Qt.ItemDataRole.UserRole, playlist.id)
            item.setData(PlaylistItemDelegate.ACTIVE_ROLE, self._current_playlist_id == playlist.id)
            item.setToolTip(f"{playlist.track_count:,} tracks")
            self._playlist_list.addItem(item)

    def set_active_playlist(self, playlist_id: str | None):
        """Set the currently active playlist (None for library)."""
        self._current_playlist_id = playlist_id
        self._refresh_playlist_list()

    def _on_playlist_clicked(self, item: QListWidgetItem):
        """Handle playlist item click."""
        playlist_id = item.data(Qt.ItemDataRole.UserRole)
        if playlist_id == "library":
            self.playlist_selected.emit("library")
        else:
            self.playlist_selected.emit(playlist_id)

    def _on_playlist_double_clicked(self, item: QListWidgetItem):
        """Handle playlist item double-click (rename for user playlists)."""
        playlist_id = item.data(Qt.ItemDataRole.UserRole)
        if playlist_id != "library":
            # Get current name (strip count suffix)
            text = item.text()
            # Remove the count suffix like "  [123]"
            if "  [" in text:
                current_name = text.rsplit("  [", 1)[0]
            else:
                current_name = text
            new_name, ok = QInputDialog.getText(
                self, "Rename Playlist", "New name:", text=current_name
            )
            if ok and new_name.strip():
                self.playlist_rename_requested.emit(playlist_id, new_name.strip())

    def _show_playlist_context_menu(self, pos):
        """Show context menu for playlist item."""
        item = self._playlist_list.itemAt(pos)
        if not item:
            return

        playlist_id = item.data(Qt.ItemDataRole.UserRole)
        if playlist_id == "library":
            return  # No context menu for library

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
        """)

        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        action = menu.exec(self._playlist_list.mapToGlobal(pos))
        if action == rename_action:
            text = item.text()
            if "  [" in text:
                current_name = text.rsplit("  [", 1)[0]
            else:
                current_name = text
            new_name, ok = QInputDialog.getText(
                self, "Rename Playlist", "New name:", text=current_name
            )
            if ok and new_name.strip():
                self.playlist_rename_requested.emit(playlist_id, new_name.strip())
        elif action == delete_action:
            self.playlist_delete_requested.emit(playlist_id)
