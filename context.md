# Wired - Development Context

## Project Overview

Local music player with a digital forensics/detective workstation aesthetic. Built with PyQt6, python-vlc, and mutagen. Emphasizes information density, keyboard-driven workflow, and professional styling following U.S. Graphics Company design principles.

## Design Philosophy

- U.S. Graphics design principles: explicit labels, dense information, technical nomenclature
- 2000s investigator/digital forensics aesthetic
- Sharp corners, monospace fonts, no decorative elements
- Detective uses whatever works efficiently

## Color Scheme

### Backgrounds (darkest to lightest)
- Primary: `#0a0a0a`
- Secondary: `#0f0f0f`
- Tertiary: `#1a1a1a`

### Text
- Normal: `#c0c0c0`
- Muted: `#909090`
- Dim: `#606060`

### Accent (muted green)
- Primary: `#4a7c59`
- Dim: `#2d4a38`

### Borders
- Standard: `#2a2a2a`

### Design Rules
- Monospace fonts (IBM Plex Mono)
- Zero border radius
- 2px accent border on active elements
- Explicit section labels in uppercase with letter-spacing
- Grid layouts for dense information display

## Technical Stack

### Dependencies
```
PyQt6>=6.6.0          # GUI framework
python-vlc>=3.0.0     # Audio playback
mutagen>=1.47.0       # Metadata reading
thefuzz>=0.22.0       # Fuzzy search
python-Levenshtein    # Speedup for thefuzz
```

### System Requirements
- VLC media player installed
- Python 3.11+

## Project Structure

```
wired/
├── main.py                         # Entry point
├── requirements.txt
├── context.md                      # This file
├── player/
│   ├── core/
│   │   ├── audio.py                # VLC wrapper with Qt signals
│   │   ├── database.py             # SQLite library cache
│   │   ├── library.py              # Directory scanner
│   │   ├── metadata.py             # Track data class
│   │   ├── playlist.py             # In-memory playlist
│   │   ├── playlist_manager.py     # Saved playlists (SQLite)
│   │   └── queue.py                # Manual playback queue
│   ├── ui/
│   │   ├── main_window.py          # Application window
│   │   ├── sidebar.py              # Album art + media info + playlists
│   │   ├── playlist_view.py        # Track table with sorting
│   │   ├── player_bar.py           # Transport controls + track info
│   │   ├── queue_panel.py          # Queue + upcoming tracks
│   │   ├── search_overlay.py       # Telescope-style fuzzy search
│   │   ├── filter_overlay.py       # Multi-field filtering
│   │   └── artist_overlay.py       # Artist dossier view
│   ├── theme/
│   │   └── lainchan.py             # Colors + stylesheet
│   └── utils/
│       ├── config.py               # Settings persistence
│       └── search.py               # Fuzzy search utilities
└── data/
    └── wired.db                    # SQLite database (auto-created)
```

## Implemented Features

### Library Management
- [x] SQLite-cached library for fast startup
- [x] Background scanning with progress indicator
- [x] Incremental scan (detect added/removed files)
- [x] Support for MP3, FLAC, OGG, WAV, M4A, OPUS
- [x] Metadata extraction (title, artist, album, year, codec, bitrate, sample rate, bit depth)
- [x] Album art extraction from tags

### Playback
- [x] VLC-based audio engine
- [x] Play/pause/stop
- [x] Seek bar with position display
- [x] Volume control
- [x] Previous/next track
- [x] Auto-advance to next track
- [x] Separate playback state from view (browse while playing)

### Queue System
- [x] Manual queue (play next / add to queue)
- [x] Queue panel with upcoming tracks preview
- [x] Drag to reorder queued tracks
- [x] Queue persists across view changes
- [x] Queue saved/restored on app restart

### Playlists
- [x] Create/rename/delete playlists
- [x] Add tracks to playlist (single or bulk)
- [x] Remove tracks from playlist
- [x] M3U import/export
- [x] Save filter results as playlist

### Search and Filter
- [x] Telescope-style fuzzy search (f or /)
- [x] Search results show tracks and artists
- [x] Multi-field filter overlay (Ctrl+F)
- [x] Filter by artist, album, year, codec
- [x] Clear filters with Escape
- [x] Enter on empty filter clears all filters

### Artist View
- [x] Artist dossier overlay (g from track)
- [x] Album grid with cover art
- [x] Track/album/duration statistics
- [x] Keyboard navigation (arrows + Enter)
- [x] Play All button

### UI Components

**Sidebar (280px)**
- Section: CURRENT - Album art display
- Section: MEDIA INFO - Grid with ALBUM, YEAR, CODEC, SAMPLE, BITRATE
- Section: PLAYLISTS - List with track counts, active highlight

**Playlist View**
- Sortable columns: #, Title, Artist, Album, Year, Time, Codec
- Multi-select (Ctrl+click, Shift+click)
- Context menu for queue/playlist operations
- Current track highlight with accent border

**Player Bar (120px)**
- Row 1: TRACK, ARTIST labels with values
- Row 2: SOURCE (album, codec, sample, bitrate), POSITION (seek bar), TRANSPORT (controls), LEVEL (volume)
- 2px accent border at top

**Queue Panel (280px, collapsible)**
- Queued tracks section
- Upcoming tracks from playback list
- Shuffle toggle
- Clear queue button

### Keyboard Shortcuts

**Playback**
- Space: Play/pause
- Left/Right: Previous/next track
- +/=/-: Volume up/down

**Navigation**
- Up/Down: Navigate track list
- Enter: Play selected track
- f or /: Open search
- Ctrl+F: Open filter
- Escape: Clear filters / close overlay
- q: Toggle queue panel
- s: Toggle shuffle
- g: Open artist view for selected track

**Track Operations**
- n: Play next (add to front of queue)
- a: Add to queue (add to end)
- x: Toggle queue/remove from queue
- Del: Remove from playlist (when in playlist view)

**Application**
- Ctrl+O: Open folder (temporary, not cached)
- Ctrl+I: Import M3U playlist
- Ctrl+Q: Quit

## Configuration

Settings stored in: `~/.config/wired/config.json`

Persisted state:
- Window geometry
- Volume level
- Queue contents
- Queue panel visibility
- Shuffle state
- Last library path

## Architecture Notes

### Playback vs View Separation

The application maintains separate state for:
- **View**: Current playlist/library being displayed (`_playlist`)
- **Playback**: Tracks being played through (`_playback_tracks`, `_playback_index`)

This allows browsing different playlists while music continues playing. The queue panel shows upcoming tracks from the playback list, not the current view.

### Database Schema

**tracks** - Library cache
- filepath (PRIMARY KEY)
- title, artist, album, year
- duration, codec, bitrate, sample_rate, bit_depth
- mtime (for change detection)

**playlists** - Saved playlists
- id (UUID)
- name
- created_at

**playlist_tracks** - Playlist membership
- playlist_id, filepath, position

## Development Notes

- Theme colors defined in `player/theme/lainchan.py`
- All UI components use explicit labels (U.S. Graphics style)
- Signals/slots for decoupled communication
- Background thread for library scanning
- No unit tests (personal tool, manual testing)

## Known Limitations

- VLC must be installed on system
- Large libraries may be slow on first scan
- Album art limited to embedded tags (no folder.jpg)
- No gapless playback
- No crossfade

## Future Considerations

- Smart playlists (auto-updating based on criteria)
- Column customization (show/hide/reorder)
- Waveform display
- Scrobbling support
- Multiple library paths
