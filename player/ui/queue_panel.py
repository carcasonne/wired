"""Up Next panel UI for displaying queue and upcoming tracks."""

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QEvent
from PyQt6.QtGui import QColor, QPainter, QKeyEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
)

from player.core.queue import PlaybackQueue
from player.core.playlist import Playlist
from player.core.metadata import Track
from player.theme.lainchan import (
    BG_PRIMARY, BG_SECONDARY, BG_TERTIARY,
    TEXT_NORMAL, TEXT_MUTED, TEXT_DIM,
    ACCENT, BORDER,
)


# Item types for the list
ITEM_TYPE_QUEUED = 1
ITEM_TYPE_UPCOMING = 2
ITEM_TYPE_DIVIDER = 3


class UpNextItemDelegate(QStyledItemDelegate):
    """Custom delegate for Up Next items with two-line display."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()

        item_type = index.data(Qt.ItemDataRole.UserRole + 1)

        # Handle divider
        if item_type == ITEM_TYPE_DIVIDER:
            painter.setPen(QColor(TEXT_DIM))
            text_rect = QRect(
                option.rect.left() + 12,
                option.rect.top(),
                option.rect.width() - 24,
                option.rect.height()
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                "── PLAYING NEXT ──"
            )
            painter.restore()
            return

        # Background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(BG_TERTIARY))
            # Left accent border for queued items only
            if item_type == ITEM_TYPE_QUEUED:
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

        # Get track data
        track: Track = index.data(Qt.ItemDataRole.UserRole)
        if track:
            is_upcoming = item_type == ITEM_TYPE_UPCOMING

            # Colors based on type
            title_color = TEXT_DIM if is_upcoming else TEXT_NORMAL
            subtitle_color = TEXT_DIM if is_upcoming else TEXT_MUTED

            # Draw position number (stored in UserRole + 2)
            queue_pos = index.data(Qt.ItemDataRole.UserRole + 2)
            if queue_pos is None:
                queue_pos = index.row() + 1
            painter.setPen(QColor(TEXT_DIM))
            pos_rect = QRect(option.rect.left() + 8, option.rect.top() + 6, 20, 20)
            painter.drawText(pos_rect, Qt.AlignmentFlag.AlignCenter, str(queue_pos))

            # Draw title
            painter.setPen(QColor(title_color))
            title_rect = QRect(
                option.rect.left() + 32,
                option.rect.top() + 6,
                option.rect.width() - 80,
                20
            )
            painter.drawText(
                title_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                track.title
            )

            # Draw duration
            painter.setPen(QColor(subtitle_color))
            duration_rect = QRect(
                option.rect.right() - 50,
                option.rect.top() + 6,
                45,
                20
            )
            painter.drawText(
                duration_rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                track.format_duration()
            )

            # Draw artist - album (secondary line)
            painter.setPen(QColor(subtitle_color))
            font = painter.font()
            new_size = font.pointSize() - 1
            if new_size > 0:
                font.setPointSize(new_size)
            painter.setFont(font)
            subtitle_rect = QRect(
                option.rect.left() + 32,
                option.rect.top() + 24,
                option.rect.width() - 44,
                18
            )
            subtitle = f"{track.artist} - {track.album}"
            painter.drawText(
                subtitle_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                subtitle
            )

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        item_type = index.data(Qt.ItemDataRole.UserRole + 1)
        if item_type == ITEM_TYPE_DIVIDER:
            return QSize(0, 24)
        return QSize(0, 48)


class QueuePanel(QWidget):
    """
    Collapsible panel showing queued tracks and upcoming playlist tracks.

    Signals:
        track_activated: Emitted when user double-clicks a track (with Track object)
        visibility_changed: Emitted when panel is shown/hidden
        shuffle_toggled: Emitted when shuffle button is clicked
    """

    track_activated = pyqtSignal(object)  # Track
    visibility_changed = pyqtSignal(bool)
    shuffle_toggled = pyqtSignal(bool)

    COLLAPSED_WIDTH = 0
    EXPANDED_WIDTH = 280
    UPCOMING_COUNT = 10

    def __init__(self, queue: PlaybackQueue):
        super().__init__()
        self._queue = queue
        self._playlist: Playlist | None = None
        self._is_expanded = False
        self._shuffle_enabled = False
        # Playback state (separate from view playlist)
        self._playback_tracks: list[Track] = []
        self._playback_index: int = -1
        self._setup_ui()
        self._connect_signals()

    def set_playback_state(self, tracks: list[Track], index: int):
        """Update the playback state for upcoming tracks preview."""
        self._playback_tracks = tracks
        self._playback_index = index
        self._refresh()

    def _setup_ui(self):
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("queueHeader")
        header.setFixedHeight(32)
        header.setStyleSheet(f"""
            QFrame#queueHeader {{
                background-color: {BG_PRIMARY};
                border: none;
                border-bottom: 1px solid {BORDER};
                border-left: 1px solid {BORDER};
            }}
            QLabel {{ border: none; }}
            QPushButton {{ border: none; }}
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 8, 0)
        header_layout.setSpacing(8)

        title = QLabel("UP NEXT")
        title.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Queue count
        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        header_layout.addWidget(self._count_label)

        # Shuffle button
        self._shuffle_btn = QPushButton("S")
        self._shuffle_btn.setFixedSize(24, 24)
        self._shuffle_btn.setToolTip("Toggle shuffle [s]")
        self._shuffle_btn.clicked.connect(self._on_shuffle_clicked)
        self._update_shuffle_button()
        header_layout.addWidget(self._shuffle_btn)

        # Clear button
        self._clear_btn = QPushButton("CLR")
        self._clear_btn.setFixedSize(32, 24)
        self._clear_btn.setToolTip("Clear queue")
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_DIM};
                font-size: 10px;
            }}
            QPushButton:hover {{
                color: {TEXT_NORMAL};
                background-color: {BG_TERTIARY};
            }}
        """)
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        header_layout.addWidget(self._clear_btn)

        layout.addWidget(header)

        # Track list
        self._list = QListWidget()
        self._list.setItemDelegate(UpNextItemDelegate(self._list))
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_SECONDARY};
                border: none;
                border-left: 1px solid {BORDER};
                outline: none;
            }}
            QListWidget::item {{
                border: none;
            }}
        """)
        self._list.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.installEventFilter(self)
        layout.addWidget(self._list, 1)

        # Footer with total duration
        footer = QFrame()
        footer.setObjectName("queueFooter")
        footer.setFixedHeight(24)
        footer.setStyleSheet(f"""
            QFrame#queueFooter {{
                background-color: {BG_PRIMARY};
                border: none;
                border-top: 1px solid {BORDER};
                border-left: 1px solid {BORDER};
            }}
            QLabel {{ border: none; }}
        """)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 0, 12, 0)

        self._duration_label = QLabel("")
        self._duration_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        footer_layout.addWidget(self._duration_label)

        footer_layout.addStretch()

        hint = QLabel("x: queue/remove")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        footer_layout.addWidget(hint)

        layout.addWidget(footer)

    def _connect_signals(self):
        self._queue.queue_changed.connect(self._refresh)

    def set_playlist(self, playlist: Playlist):
        """Set the playlist for shuffle state sync."""
        self._playlist = playlist
        self._playlist.shuffle_changed.connect(self._on_playlist_shuffle_changed)

    def set_shuffle_enabled(self, enabled: bool):
        """Update shuffle state from external source."""
        self._shuffle_enabled = enabled
        self._update_shuffle_button()
        self._refresh()

    def _update_shuffle_button(self):
        """Update shuffle button appearance."""
        if self._shuffle_enabled:
            self._shuffle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT};
                    color: {BG_PRIMARY};
                    font-size: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {ACCENT};
                }}
            """)
        else:
            self._shuffle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {TEXT_DIM};
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    color: {TEXT_NORMAL};
                    background-color: {BG_TERTIARY};
                }}
            """)

    def _on_shuffle_clicked(self):
        """Handle shuffle button click."""
        self._shuffle_enabled = not self._shuffle_enabled
        self._update_shuffle_button()
        self.shuffle_toggled.emit(self._shuffle_enabled)

    def _on_playlist_shuffle_changed(self, enabled: bool):
        """Handle external shuffle state change."""
        self._shuffle_enabled = enabled
        self._update_shuffle_button()
        self._refresh()

    def _refresh(self):
        """Refresh the list showing queue and upcoming tracks."""
        self._list.clear()

        queue_count = len(self._queue)
        total_duration = 0.0
        position = 1

        # Add queued tracks
        for track in self._queue.tracks:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, track)
            item.setData(Qt.ItemDataRole.UserRole + 1, ITEM_TYPE_QUEUED)
            item.setData(Qt.ItemDataRole.UserRole + 2, position)
            item.setData(Qt.ItemDataRole.DisplayRole, track.title)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
            self._list.addItem(item)
            total_duration += track.duration
            position += 1

        # Get upcoming tracks from playback state (not view playlist)
        upcoming = []
        if self._playback_tracks and self._playback_index >= 0:
            # Get tracks after current playback position
            start_idx = self._playback_index + 1
            end_idx = min(start_idx + self.UPCOMING_COUNT, len(self._playback_tracks))
            upcoming = self._playback_tracks[start_idx:end_idx]

        # Add divider if we have both queued and upcoming
        if queue_count > 0 and upcoming:
            divider = QListWidgetItem()
            divider.setData(Qt.ItemDataRole.UserRole + 1, ITEM_TYPE_DIVIDER)
            divider.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(divider)

        # Add upcoming playlist tracks (continue numbering from queue)
        for track in upcoming:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, track)
            item.setData(Qt.ItemDataRole.UserRole + 1, ITEM_TYPE_UPCOMING)
            item.setData(Qt.ItemDataRole.UserRole + 2, position)
            item.setData(Qt.ItemDataRole.DisplayRole, track.title)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            self._list.addItem(item)
            total_duration += track.duration
            position += 1

        # Update labels
        total_count = queue_count + len(upcoming)
        if queue_count > 0:
            self._count_label.setText(f"{queue_count} queued")
        elif total_count > 0:
            self._count_label.setText(f"{total_count} tracks")
        else:
            self._count_label.setText("")

        if total_duration > 0:
            mins = int(total_duration // 60)
            self._duration_label.setText(f"Total: {mins}m")
        else:
            self._duration_label.setText("")

    def _on_clear_clicked(self):
        self._queue.clear()

    def _on_item_double_clicked(self, item: QListWidgetItem):
        item_type = item.data(Qt.ItemDataRole.UserRole + 1)
        if item_type == ITEM_TYPE_DIVIDER:
            return

        track = item.data(Qt.ItemDataRole.UserRole)
        if track:
            self.track_activated.emit(track)

    def toggle(self):
        """Toggle panel visibility."""
        if self._is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        """Show the panel."""
        self._is_expanded = True
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self._refresh()
        self.visibility_changed.emit(True)

    def collapse(self):
        """Hide the panel."""
        self._is_expanded = False
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self.visibility_changed.emit(False)

    def is_expanded(self) -> bool:
        return self._is_expanded

    def eventFilter(self, obj, event):
        """Filter events from the list widget."""
        if obj == self._list and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_X or key == Qt.Key.Key_Delete:
                self._handle_remove_or_queue()
                return True
            elif key == Qt.Key.Key_S:
                self._on_shuffle_clicked()
                return True
            elif key == Qt.Key.Key_Escape:
                self.collapse()
                return True
        return super().eventFilter(obj, event)

    def _handle_remove_or_queue(self):
        """Handle x key - remove queued item or promote upcoming to queue."""
        current = self._list.currentRow()
        if current < 0:
            return

        item = self._list.item(current)
        item_type = item.data(Qt.ItemDataRole.UserRole + 1)
        track = item.data(Qt.ItemDataRole.UserRole)

        if item_type == ITEM_TYPE_QUEUED:
            # Remove from queue - find actual queue index
            queue_idx = 0
            for i in range(current):
                prev_item = self._list.item(i)
                if prev_item.data(Qt.ItemDataRole.UserRole + 1) == ITEM_TYPE_QUEUED:
                    queue_idx += 1
            self._queue.remove(queue_idx)
        elif item_type == ITEM_TYPE_UPCOMING and track:
            # Promote to queue
            self._queue.add_to_queue(track)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation on the panel itself."""
        if event.key() == Qt.Key.Key_Escape:
            self.collapse()
        else:
            super().keyPressEvent(event)
