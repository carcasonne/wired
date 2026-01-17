"""Telescope-style filter overlay for filtering tracks."""

from dataclasses import dataclass
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QRect
from PyQt6.QtGui import QKeyEvent, QColor, QPainter
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
    QPushButton,
    QScrollArea,
)

from player.core.metadata import Track
from player.theme.lainchan import (
    BG_PRIMARY, BG_SECONDARY, BG_TERTIARY,
    TEXT_NORMAL, TEXT_MUTED, TEXT_DIM,
    ACCENT, ACCENT_DIM, BORDER,
)


@dataclass
class Filter:
    """Represents a single filter."""
    field: str  # artist, album, year, codec
    value: str

    def matches(self, track: Track) -> bool:
        """Check if track matches this filter."""
        field_value = getattr(track, self.field, "").lower()
        return self.value.lower() in field_value

    def __str__(self) -> str:
        return f"{self.field}: {self.value}"


class FilterChip(QFrame):
    """A removable filter chip widget."""

    remove_clicked = pyqtSignal(object)  # Emits the Filter

    def __init__(self, filter_: Filter, parent=None):
        super().__init__(parent)
        self._filter = filter_
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("filterChip")
        self.setStyleSheet(f"""
            QFrame#filterChip {{
                background-color: {ACCENT_DIM};
                border: 1px solid {ACCENT};
                border-radius: 2px;
                padding: 2px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(6)

        label = QLabel(str(self._filter))
        label.setStyleSheet(f"color: {TEXT_NORMAL}; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(label)

        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_MUTED};
                border: none;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {TEXT_NORMAL};
            }}
        """)
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self._filter))
        layout.addWidget(remove_btn)

    @property
    def filter(self) -> Filter:
        return self._filter


class SuggestionDelegate(QStyledItemDelegate):
    """Custom delegate to render filter suggestions."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()

        # Background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(BG_TERTIARY))
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

        text = index.data(Qt.ItemDataRole.DisplayRole)
        if text:
            painter.setPen(QColor(TEXT_NORMAL))
            text_rect = QRect(
                option.rect.left() + 12,
                option.rect.top(),
                option.rect.width() - 24,
                option.rect.height()
            )
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(0, 32)


class FilterOverlay(QDialog):
    """Telescope-style filter overlay for filtering tracks."""

    filters_applied = pyqtSignal(list)  # Emits list of Filter objects
    save_as_playlist_requested = pyqtSignal(list)  # Emits list of Filter objects for saving

    FILTER_FIELDS = ["artist", "album", "year", "codec"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[Track] = []
        self._filters: list[Filter] = []
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(100)
        self._debounce_timer.timeout.connect(self._update_suggestions)

        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(600, 450)

        # Main container with border
        container = QFrame(self)
        container.setObjectName("filterContainer")
        container.setFixedSize(600, 450)
        container.setStyleSheet(f"""
            QFrame#filterContainer {{
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

        title = QLabel("FILTER")
        title.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
            border: none;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._match_label = QLabel("")
        self._match_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; border: none;")
        header_layout.addWidget(self._match_label)

        layout.addWidget(header)

        # Active filters section
        filters_section = QFrame()
        filters_section.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SECONDARY};
                border: none;
                border-bottom: 1px solid {BORDER};
            }}
            QLabel {{
                border: none;
            }}
        """)
        filters_layout = QVBoxLayout(filters_section)
        filters_layout.setContentsMargins(12, 8, 12, 8)
        filters_layout.setSpacing(6)

        filters_label = QLabel("ACTIVE FILTERS:")
        filters_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 1px;")
        filters_layout.addWidget(filters_label)

        # Chips container with flow layout
        self._chips_container = QWidget()
        self._chips_container.setStyleSheet(f"background-color: {BG_SECONDARY};")
        self._chips_layout = QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(6)
        self._chips_layout.addStretch()

        self._no_filters_label = QLabel("No filters active")
        self._no_filters_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; font-style: italic; background: transparent;")
        filters_layout.addWidget(self._no_filters_label)
        filters_layout.addWidget(self._chips_container)

        layout.addWidget(filters_section)

        # Input section
        input_section = QFrame()
        input_section.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SECONDARY};
                border: none;
                border-bottom: 1px solid {BORDER};
            }}
            QLabel {{
                border: none;
            }}
        """)
        input_layout = QVBoxLayout(input_section)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(4)

        add_label = QLabel("ADD FILTER:")
        add_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 1px;")
        input_layout.addWidget(add_label)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        prompt = QLabel(">")
        prompt.setStyleSheet(f"color: {ACCENT}; font-weight: bold; border: none;")
        input_row.addWidget(prompt)

        self._input = QLineEdit()
        self._input.setPlaceholderText("artist:name  album:name  year:2020  codec:flac")
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
        input_row.addWidget(self._input, 1)

        input_layout.addLayout(input_row)
        layout.addWidget(input_section)

        # Suggestions list
        self._suggestions_list = QListWidget()
        self._suggestions_list.setItemDelegate(SuggestionDelegate(self._suggestions_list))
        self._suggestions_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_SECONDARY};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                border: none;
            }}
        """)
        self._suggestions_list.itemActivated.connect(self._on_suggestion_activated)
        self._suggestions_list.itemDoubleClicked.connect(self._on_suggestion_activated)
        layout.addWidget(self._suggestions_list, 1)

        # Action buttons
        button_section = QFrame()
        button_section.setFixedHeight(48)
        button_section.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
                border: none;
                border-top: 1px solid {BORDER};
            }}
        """)
        button_layout = QHBoxLayout(button_section)
        button_layout.setContentsMargins(12, 8, 12, 8)
        button_layout.setSpacing(12)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setStyleSheet(self._get_button_style(primary=True))
        self._apply_btn.clicked.connect(self._apply_filters)
        button_layout.addWidget(self._apply_btn)

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.setStyleSheet(self._get_button_style())
        self._clear_btn.clicked.connect(self._clear_filters)
        button_layout.addWidget(self._clear_btn)

        button_layout.addStretch()

        self._save_btn = QPushButton("Save as Playlist...")
        self._save_btn.setStyleSheet(self._get_button_style())
        self._save_btn.clicked.connect(self._save_as_playlist)
        button_layout.addWidget(self._save_btn)

        layout.addWidget(button_section)

        # Footer hint
        footer = QFrame()
        footer.setObjectName("filterFooter")
        footer.setFixedHeight(24)
        footer.setStyleSheet(f"""
            QFrame#filterFooter {{
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

        hint = QLabel("Enter: add/apply  |  Tab: complete  |  Backspace: remove  |  Esc: cancel")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        footer_layout.addWidget(hint)

        layout.addWidget(footer)

        # Main widget layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def _get_button_style(self, primary: bool = False) -> str:
        if primary:
            return f"""
                QPushButton {{
                    background-color: {ACCENT_DIM};
                    color: {TEXT_NORMAL};
                    border: 1px solid {ACCENT};
                    padding: 6px 16px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {ACCENT};
                }}
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_MUTED};
                border: 1px solid {BORDER};
                padding: 6px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {TEXT_NORMAL};
                border-color: {TEXT_MUTED};
            }}
        """

    def set_tracks(self, tracks: list[Track]):
        """Set the tracks to filter."""
        self._tracks = tracks

    def set_filters(self, filters: list[Filter]):
        """Set current filters."""
        self._filters = list(filters)
        self._refresh_chips()
        self._update_match_count()

    def get_filters(self) -> list[Filter]:
        """Get current filters."""
        return list(self._filters)

    def show_filter(self):
        """Show the filter overlay."""
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 3
            self.move(x, y)

        self._input.clear()
        self._refresh_chips()
        self._update_match_count()
        self._update_suggestions()
        self._input.setFocus()
        self.exec()

    def _refresh_chips(self):
        """Refresh the filter chips display."""
        # Clear existing chips
        while self._chips_layout.count() > 1:  # Keep the stretch
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._filters:
            self._no_filters_label.hide()
            for f in self._filters:
                chip = FilterChip(f)
                chip.remove_clicked.connect(self._on_remove_filter)
                self._chips_layout.insertWidget(self._chips_layout.count() - 1, chip)
        else:
            self._no_filters_label.show()

    def _on_remove_filter(self, filter_: Filter):
        """Handle filter chip removal."""
        if filter_ in self._filters:
            self._filters.remove(filter_)
            self._refresh_chips()
            self._update_match_count()

    def _on_text_changed(self, text: str):
        """Handle input changes with debounce."""
        self._debounce_timer.start()

    def _update_suggestions(self):
        """Update the suggestions list based on input."""
        self._suggestions_list.clear()
        text = self._input.text().strip().lower()

        if not text:
            # Show field hints
            for field in self.FILTER_FIELDS:
                item = QListWidgetItem(f"{field}:")
                self._suggestions_list.addItem(item)
            return

        # Parse input for field:value
        if ":" in text:
            field, value = text.split(":", 1)
            field = field.strip()
            value = value.strip()

            if field in self.FILTER_FIELDS:
                # Get unique values for this field
                values = self._get_unique_values(field)
                # Filter by partial match
                matches = [v for v in values if value.lower() in v.lower()][:20]

                for v in matches:
                    item = QListWidgetItem(f"{field}:{v}")
                    self._suggestions_list.addItem(item)
        else:
            # Show matching fields
            for field in self.FILTER_FIELDS:
                if text in field:
                    item = QListWidgetItem(f"{field}:")
                    self._suggestions_list.addItem(item)

        if self._suggestions_list.count() > 0:
            self._suggestions_list.setCurrentRow(0)

    def _get_unique_values(self, field: str) -> list[str]:
        """Get unique values for a field from tracks."""
        values = set()
        for track in self._tracks:
            val = getattr(track, field, "")
            if val and val != "Unknown":
                values.add(str(val))
        return sorted(values)

    def _on_suggestion_activated(self, item: QListWidgetItem):
        """Handle suggestion selection."""
        text = item.text()

        if text.endswith(":"):
            # Just a field, put it in input
            self._input.setText(text)
            self._input.setFocus()
        else:
            # Full filter, add it
            self._add_filter_from_text(text)

    def _add_filter_from_text(self, text: str):
        """Parse and add a filter from text like 'artist:Blondie'."""
        if ":" not in text:
            return

        field, value = text.split(":", 1)
        field = field.strip().lower()
        value = value.strip()

        if field in self.FILTER_FIELDS and value:
            new_filter = Filter(field=field, value=value)
            # Don't add duplicates
            if new_filter not in self._filters:
                self._filters.append(new_filter)
                self._refresh_chips()
                self._update_match_count()

        self._input.clear()
        self._update_suggestions()

    def _update_match_count(self):
        """Update the matching tracks count."""
        if not self._filters:
            self._match_label.setText(f"{len(self._tracks):,} tracks")
            return

        count = sum(1 for t in self._tracks if self._track_matches(t))
        self._match_label.setText(f"Matching: {count:,} tracks")

    def _track_matches(self, track: Track) -> bool:
        """Check if track matches all filters."""
        return all(f.matches(track) for f in self._filters)

    def get_filtered_tracks(self) -> list[Track]:
        """Get tracks matching all filters."""
        if not self._filters:
            return self._tracks
        return [t for t in self._tracks if self._track_matches(t)]

    def _apply_filters(self):
        """Apply filters and close."""
        self.filters_applied.emit(self._filters)
        self.accept()

    def _clear_filters(self):
        """Clear all filters."""
        self._filters = []
        self._refresh_chips()
        self._update_match_count()

    def _save_as_playlist(self):
        """Signal to save current filter results as playlist."""
        if self._filters:
            self.save_as_playlist_requested.emit(self._filters)
            self.accept()

    def eventFilter(self, obj, event):
        """Handle keyboard events in the input."""
        if obj == self._input and event.type() == event.Type.KeyPress:
            key = event.key()

            if key == Qt.Key.Key_Escape:
                self.reject()
                return True
            elif key == Qt.Key.Key_Down:
                self._move_selection(1)
                return True
            elif key == Qt.Key.Key_Up:
                self._move_selection(-1)
                return True
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                text = self._input.text().strip()
                # If input has a complete filter, add it
                if text and ":" in text and not text.endswith(":"):
                    self._add_filter_from_text(text)
                    return True
                # If input has partial text, try to use suggestion
                if text:
                    current = self._suggestions_list.currentItem()
                    if current:
                        self._on_suggestion_activated(current)
                    return True
                # If input is empty, apply current filters (even if empty - clears filters)
                if not text:
                    self._apply_filters()
                    return True
                return True
            elif key == Qt.Key.Key_Backspace and not self._input.text():
                # Remove last filter
                if self._filters:
                    self._filters.pop()
                    self._refresh_chips()
                    self._update_match_count()
                return True
            elif key == Qt.Key.Key_Tab:
                # Autocomplete from suggestion
                current = self._suggestions_list.currentItem()
                if current:
                    self._input.setText(current.text())
                return True

        return super().eventFilter(obj, event)

    def _move_selection(self, delta: int):
        """Move the selection up or down."""
        current = self._suggestions_list.currentRow()
        new_row = max(0, min(self._suggestions_list.count() - 1, current + delta))
        self._suggestions_list.setCurrentRow(new_row)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key presses on the overlay itself."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
