"""Telescope-style fuzzy search overlay."""

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QRect
from PyQt6.QtGui import QKeyEvent, QColor, QPainter, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QFrame,
    QDialog,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
)

from player.core.metadata import Track
from player.core.playlist import Playlist
from player.utils.search import fuzzy_search, SearchResult
from player.theme.lainchan import (
    BG_PRIMARY, BG_SECONDARY, BG_TERTIARY,
    TEXT_NORMAL, TEXT_MUTED, TEXT_DIM,
    ACCENT, ACCENT_DIM, BORDER,
)


class SearchResultDelegate(QStyledItemDelegate):
    """Custom delegate to render two-line search results."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()

        # Background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(BG_TERTIARY))
            # Draw left accent border
            painter.setPen(QColor(ACCENT))
            painter.drawLine(
                option.rect.left(), option.rect.top(),
                option.rect.left(), option.rect.bottom()
            )
            painter.drawLine(
                option.rect.left() + 1, option.rect.top(),
                option.rect.left() + 1, option.rect.bottom()
            )
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor(BG_TERTIARY))

        # Get the two lines from data
        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text:
            lines = text.split("\n")
            title = lines[0] if len(lines) > 0 else ""
            subtitle = lines[1] if len(lines) > 1 else ""

            # Draw title (primary text)
            painter.setPen(QColor(TEXT_NORMAL))
            title_rect = QRect(
                option.rect.left() + 12,
                option.rect.top() + 6,
                option.rect.width() - 24,
                20
            )
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

            # Draw subtitle (secondary text, muted)
            painter.setPen(QColor(TEXT_MUTED))
            subtitle_rect = QRect(
                option.rect.left() + 12,
                option.rect.top() + 24,
                option.rect.width() - 24,
                18
            )
            font = painter.font()
            new_size = font.pointSize() - 1
            if new_size > 0:
                font.setPointSize(new_size)
            painter.setFont(font)
            painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, subtitle)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(0, 48)


class SearchOverlay(QDialog):
    """Telescope-style search overlay for finding tracks and artists."""

    track_selected = pyqtSignal(int)  # Emits playlist index
    artist_selected = pyqtSignal(str)  # Emits artist name

    # Item types stored in UserRole+1
    ITEM_TYPE_TRACK = 0
    ITEM_TYPE_ARTIST = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlist: Playlist | None = None
        self._library_tracks: list[Track] = []  # Full library for artist search
        self._results: list[SearchResult] = []
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(100)
        self._debounce_timer.timeout.connect(self._perform_search)

        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(600, 400)

        # Main container with border
        container = QFrame(self)
        container.setObjectName("searchContainer")
        container.setFixedSize(600, 400)
        container.setStyleSheet(f"""
            QFrame#searchContainer {{
                background-color: {BG_PRIMARY};
                border: 1px solid {ACCENT};
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
                border: none;
                border-bottom: 1px solid {BORDER};
            }}
            QLabel {{
                border: none;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        title = QLabel("SEARCH")
        title.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
            border: none;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; border: none;")
        header_layout.addWidget(self._count_label)

        layout.addWidget(header)

        # Search input
        input_container = QFrame()
        input_container.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SECONDARY};
                border: none;
                border-bottom: 1px solid {BORDER};
            }}
            QLabel {{
                border: none;
            }}
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 8, 12, 8)

        prompt = QLabel(">")
        prompt.setStyleSheet(f"color: {ACCENT}; font-weight: bold; border: none;")
        input_layout.addWidget(prompt)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Type to search...")
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                border: none;
                color: {TEXT_NORMAL};
                font-size: 14px;
                padding: 4px;
            }}
        """)
        self._input.textChanged.connect(self._on_text_changed)
        self._input.installEventFilter(self)
        input_layout.addWidget(self._input, 1)

        layout.addWidget(input_container)

        # Results list
        self._results_list = QListWidget()
        self._results_list.setItemDelegate(SearchResultDelegate(self._results_list))
        self._results_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_SECONDARY};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                border: none;
            }}
        """)
        self._results_list.itemActivated.connect(self._on_item_activated)
        self._results_list.itemDoubleClicked.connect(self._on_item_activated)
        layout.addWidget(self._results_list, 1)

        # Footer hint
        footer = QFrame()
        footer.setObjectName("searchFooter")
        footer.setFixedHeight(24)
        footer.setStyleSheet(f"""
            QFrame#searchFooter {{
                background-color: {BG_PRIMARY};
                border: none;
                border-top: 1px solid {BORDER};
            }}
            QLabel {{
                border: none;
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 0, 12, 0)

        hint = QLabel("Enter: play  |  Esc: close  |  Up/Down: navigate")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        footer_layout.addWidget(hint)

        layout.addWidget(footer)

        # Main widget layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def set_playlist(self, playlist: Playlist):
        """Set the playlist to search."""
        self._playlist = playlist

    def set_library_tracks(self, tracks: list[Track]):
        """Set the full library tracks for artist search."""
        self._library_tracks = tracks

    def show_search(self):
        """Show the search overlay and focus input."""
        if self.parent():
            # Center on parent
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 3
            self.move(x, y)

        self._input.clear()
        self._results_list.clear()
        self._results = []
        self._count_label.setText("")
        self._input.setFocus()
        self.exec()  # Modal dialog - blocks until closed

    def _on_text_changed(self, text: str):
        """Handle search input changes with debounce."""
        self._debounce_timer.start()

    def _perform_search(self):
        """Execute the search."""
        query = self._input.text().strip()
        self._results_list.clear()
        self._results = []

        if not query or not self._playlist:
            self._count_label.setText("")
            return

        query_lower = query.lower()

        # Search for matching artists first
        artist_matches = self._find_matching_artists(query_lower)

        # Add artist results at the top
        for artist_name, track_count in artist_matches[:5]:  # Limit to 5 artists
            display_text = f"{artist_name}\nARTIST  •  {track_count} tracks"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, artist_name)
            item.setData(Qt.ItemDataRole.UserRole + 1, self.ITEM_TYPE_ARTIST)
            self._results_list.addItem(item)

        # Search for tracks
        self._results = fuzzy_search(query, self._playlist.tracks, limit=50)

        # Count total results
        total = len(artist_matches[:5]) + len(self._results)
        self._count_label.setText(f"{total} results")

        for result in self._results:
            track = result.track
            # Two-line display: Title on top, Artist - Album below
            display_text = f"{track.title}\n{track.artist} - {track.album}"

            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, result.index)
            item.setData(Qt.ItemDataRole.UserRole + 1, self.ITEM_TYPE_TRACK)

            self._results_list.addItem(item)

        if self._results_list.count() > 0:
            self._results_list.setCurrentRow(0)

    def _find_matching_artists(self, query: str) -> list[tuple[str, int]]:
        """Find artists matching the query, returns (artist_name, track_count) tuples."""
        # Use library tracks for comprehensive artist search
        tracks = self._library_tracks if self._library_tracks else (self._playlist.tracks if self._playlist else [])

        # Build artist -> track count mapping
        artist_counts: dict[str, int] = {}
        for track in tracks:
            if track.artist and track.artist != "Unknown":
                artist_counts[track.artist] = artist_counts.get(track.artist, 0) + 1

        # Find matches
        matches = []
        for artist, count in artist_counts.items():
            if query in artist.lower():
                matches.append((artist, count))

        # Sort by relevance: exact start match first, then by track count
        matches.sort(key=lambda x: (not x[0].lower().startswith(query), -x[1]))

        return matches

    def _on_item_activated(self, item: QListWidgetItem):
        """Handle item selection."""
        item_type = item.data(Qt.ItemDataRole.UserRole + 1)
        data = item.data(Qt.ItemDataRole.UserRole)

        if item_type == self.ITEM_TYPE_ARTIST:
            # Artist selected - emit artist name
            if data:
                self.artist_selected.emit(data)
                self.close_search()
        elif item_type == self.ITEM_TYPE_TRACK:
            # Track selected - emit playlist index
            if data is not None:
                self.track_selected.emit(data)
                self.close_search()
        elif data is not None:
            # Fallback for old behavior (no type set)
            self.track_selected.emit(data)
            self.close_search()

    def close_search(self):
        """Close the search overlay."""
        self.reject()  # Close the dialog

    def eventFilter(self, obj, event):
        """Handle keyboard events in the input."""
        if obj == self._input and event.type() == event.Type.KeyPress:
            key = event.key()

            if key == Qt.Key.Key_Escape:
                self.close_search()
                return True
            elif key == Qt.Key.Key_Down:
                self._move_selection(1)
                return True
            elif key == Qt.Key.Key_Up:
                self._move_selection(-1)
                return True
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                current = self._results_list.currentItem()
                if current:
                    self._on_item_activated(current)
                return True

        return super().eventFilter(obj, event)

    def _move_selection(self, delta: int):
        """Move the selection up or down."""
        current = self._results_list.currentRow()
        new_row = max(0, min(self._results_list.count() - 1, current + delta))
        self._results_list.setCurrentRow(new_row)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key presses on the overlay itself."""
        if event.key() == Qt.Key.Key_Escape:
            self.close_search()
        else:
            super().keyPressEvent(event)
