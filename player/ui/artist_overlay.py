"""Artist dossier overlay showing artist info and albums."""

from dataclasses import dataclass
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QKeyEvent, QColor, QPainter, QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QWidget,
    QGridLayout,
    QPushButton,
)

from player.core.metadata import Track
from player.theme.lainchan import (
    BG_PRIMARY, BG_SECONDARY, BG_TERTIARY,
    TEXT_NORMAL, TEXT_MUTED, TEXT_DIM,
    ACCENT, ACCENT_DIM, BORDER,
)


@dataclass
class AlbumInfo:
    """Aggregated album information."""
    name: str
    year: str
    track_count: int
    total_duration: float
    album_art: bytes | None
    codecs: set[str]


class AlbumCard(QFrame):
    """Clickable album card with art and info."""

    clicked = pyqtSignal(str)  # Emits album name

    def __init__(self, album: AlbumInfo, parent=None):
        super().__init__(parent)
        self._album = album
        self._selected = False
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(140, 190)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self._create_content()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_TERTIARY};
                    border: 2px solid {ACCENT};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {BG_SECONDARY};
                    border: 1px solid {BORDER};
                }}
                QFrame:hover {{
                    border-color: {ACCENT};
                    background-color: {BG_TERTIARY};
                }}
            """)

    def set_selected(self, selected: bool):
        """Set selection state for keyboard navigation."""
        self._selected = selected
        self._update_style()

    def _create_content(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Album art
        art_label = QLabel()
        art_label.setFixedSize(124, 124)
        art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art_label.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_PRIMARY};
                border: 1px solid {BORDER};
            }}
        """)

        if self._album.album_art:
            pixmap = QPixmap()
            pixmap.loadFromData(self._album.album_art)
            scaled = pixmap.scaled(
                124, 124,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            art_label.setPixmap(scaled)
        else:
            art_label.setText("No Art")
            art_label.setStyleSheet(art_label.styleSheet() + f"""
                color: {TEXT_DIM};
                font-size: 10px;
            """)

        layout.addWidget(art_label)

        # Album name (truncated)
        name_label = QLabel(self._album.name)
        name_label.setStyleSheet(f"""
            color: {TEXT_NORMAL};
            font-size: 11px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        name_label.setWordWrap(False)
        name_label.setMaximumWidth(124)
        # Elide text if too long
        metrics = name_label.fontMetrics()
        elided = metrics.elidedText(self._album.name, Qt.TextElideMode.ElideRight, 120)
        name_label.setText(elided)
        name_label.setToolTip(self._album.name)
        layout.addWidget(name_label)

        # Year and track count
        info_text = f"{self._album.year}" if self._album.year else ""
        if self._album.track_count:
            if info_text:
                info_text += f"  •  {self._album.track_count} tracks"
            else:
                info_text = f"{self._album.track_count} tracks"

        info_label = QLabel(info_text)
        info_label.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-size: 10px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(info_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._album.name)
        super().mousePressEvent(event)


class ArtistOverlay(QDialog):
    """Artist dossier overlay showing artist info and album grid."""

    album_selected = pyqtSignal(str, str)  # artist, album
    play_all_requested = pyqtSignal(str)  # artist

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[Track] = []
        self._artist: str = ""
        self._albums: list[AlbumInfo] = []
        self._album_cards: list[AlbumCard] = []
        self._selected_index: int = 0
        self._cols: int = 4
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(700, 500)

        # Main container
        container = QFrame(self)
        container.setObjectName("artistContainer")
        container.setFixedSize(700, 500)
        container.setStyleSheet(f"""
            QFrame#artistContainer {{
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

        title = QLabel("ARTIST DOSSIER")
        title.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
            border: none;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        layout.addWidget(header)

        # Artist info section
        info_section = QFrame()
        info_section.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SECONDARY};
                border: none;
                border-bottom: 1px solid {BORDER};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        info_layout = QVBoxLayout(info_section)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(8)

        self._artist_label = QLabel("")
        self._artist_label.setStyleSheet(f"""
            color: {TEXT_NORMAL};
            font-size: 20px;
            font-weight: bold;
        """)
        info_layout.addWidget(self._artist_label)

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: 12px;
        """)
        info_layout.addWidget(self._stats_label)

        layout.addWidget(info_section)

        # Albums section header
        albums_header = QFrame()
        albums_header.setFixedHeight(28)
        albums_header.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
                border: none;
            }}
            QLabel {{
                border: none;
            }}
        """)
        albums_header_layout = QHBoxLayout(albums_header)
        albums_header_layout.setContentsMargins(16, 0, 16, 0)

        albums_title = QLabel("DISCOGRAPHY")
        albums_title.setStyleSheet(f"""
            color: {TEXT_DIM};
            font-size: 10px;
            letter-spacing: 1px;
        """)
        albums_header_layout.addWidget(albums_title)
        albums_header_layout.addStretch()

        layout.addWidget(albums_header)

        # Scrollable album grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Prevent scroll area from stealing focus
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {BG_PRIMARY};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {BG_PRIMARY};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {BORDER};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {TEXT_DIM};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self._albums_container = QWidget()
        self._albums_container.setStyleSheet(f"background-color: {BG_PRIMARY};")
        self._albums_layout = QGridLayout(self._albums_container)
        self._albums_layout.setContentsMargins(16, 8, 16, 16)
        self._albums_layout.setSpacing(12)
        self._albums_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._scroll.setWidget(self._albums_container)
        layout.addWidget(self._scroll, 1)

        # Footer with buttons
        footer = QFrame()
        footer.setFixedHeight(48)
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
                border: none;
                border-top: 1px solid {BORDER};
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 16, 8)
        footer_layout.setSpacing(12)

        play_all_btn = QPushButton("Play All")
        play_all_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        play_all_btn.setStyleSheet(f"""
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
        """)
        play_all_btn.clicked.connect(self._on_play_all)
        footer_layout.addWidget(play_all_btn)

        footer_layout.addStretch()

        hint = QLabel("Arrows: navigate  |  Enter: select  |  p: play all  |  Esc: close")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        footer_layout.addWidget(hint)

        close_btn = QPushButton("Close")
        close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_btn.setStyleSheet(f"""
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
        """)
        close_btn.clicked.connect(self.reject)
        footer_layout.addWidget(close_btn)

        layout.addWidget(footer)

        # Main dialog layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def set_tracks(self, tracks: list[Track]):
        """Set the library tracks for lookups."""
        self._tracks = tracks

    def show_artist(self, artist: str):
        """Show the overlay for a specific artist."""
        self._artist = artist
        self._build_artist_data()
        self._populate_ui()

        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 3
            self.move(x, y)

        self.setFocus()
        self.exec()

    def _build_artist_data(self):
        """Build album data from tracks."""
        # Filter tracks by artist
        artist_tracks = [t for t in self._tracks if t.artist.lower() == self._artist.lower()]

        # Group by album
        albums_dict: dict[str, list[Track]] = {}
        for track in artist_tracks:
            album_name = track.album if track.album and track.album != "Unknown" else "(Singles)"
            if album_name not in albums_dict:
                albums_dict[album_name] = []
            albums_dict[album_name].append(track)

        # Build AlbumInfo objects
        self._albums = []
        for album_name, tracks in albums_dict.items():
            # Get album art from first track that has it
            album_art = None
            for t in tracks:
                t.load_album_art()
                if t.album_art:
                    album_art = t.album_art
                    break

            # Get year (use most common or first non-empty)
            years = [t.year for t in tracks if t.year]
            year = years[0] if years else ""

            # Get codecs
            codecs = {t.codec for t in tracks if t.codec and t.codec != "Unknown"}

            self._albums.append(AlbumInfo(
                name=album_name,
                year=year,
                track_count=len(tracks),
                total_duration=sum(t.duration for t in tracks),
                album_art=album_art,
                codecs=codecs,
            ))

        # Sort by year (newest first), then by name
        self._albums.sort(key=lambda a: (a.year or "0000", a.name), reverse=True)

    def _populate_ui(self):
        """Populate the UI with artist data."""
        # Clear existing album cards
        while self._albums_layout.count():
            item = self._albums_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Artist name
        self._artist_label.setText(self._artist)

        # Stats
        total_tracks = sum(a.track_count for a in self._albums)
        total_duration = sum(a.total_duration for a in self._albums)
        all_codecs = set()
        for a in self._albums:
            all_codecs.update(a.codecs)

        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        duration_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        codecs_text = ", ".join(sorted(all_codecs)) if all_codecs else ""
        stats_parts = [
            f"{total_tracks} tracks",
            f"{len(self._albums)} albums",
            duration_text,
        ]
        if codecs_text:
            stats_parts.append(codecs_text)

        self._stats_label.setText("  •  ".join(stats_parts))

        # Album grid (4 columns)
        self._album_cards = []
        self._selected_index = 0
        for i, album in enumerate(self._albums):
            card = AlbumCard(album)
            card.clicked.connect(self._on_album_clicked)
            row = i // self._cols
            col = i % self._cols
            self._albums_layout.addWidget(card, row, col)
            self._album_cards.append(card)

        # Select first album
        if self._album_cards:
            self._album_cards[0].set_selected(True)

    def _on_album_clicked(self, album_name: str):
        """Handle album card click."""
        self.album_selected.emit(self._artist, album_name)
        self.accept()

    def _on_play_all(self):
        """Handle play all button."""
        self.play_all_requested.emit(self._artist)
        self.accept()

    def _select_album(self, index: int):
        """Select an album by index."""
        if not self._album_cards:
            return

        # Clamp index
        index = max(0, min(len(self._album_cards) - 1, index))

        # Deselect old
        if 0 <= self._selected_index < len(self._album_cards):
            self._album_cards[self._selected_index].set_selected(False)

        # Select new
        self._selected_index = index
        self._album_cards[index].set_selected(True)

        # Scroll to make visible
        card = self._album_cards[index]
        self._scroll.ensureWidgetVisible(card)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key presses."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Left:
            self._select_album(self._selected_index - 1)
        elif event.key() == Qt.Key.Key_Right:
            self._select_album(self._selected_index + 1)
        elif event.key() == Qt.Key.Key_Up:
            self._select_album(self._selected_index - self._cols)
        elif event.key() == Qt.Key.Key_Down:
            self._select_album(self._selected_index + self._cols)
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Select current album
            if self._album_cards and 0 <= self._selected_index < len(self._albums):
                album_name = self._albums[self._selected_index].name
                self.album_selected.emit(self._artist, album_name)
                self.accept()
        elif event.key() == Qt.Key.Key_P:
            # Play all
            self._on_play_all()
        else:
            super().keyPressEvent(event)
