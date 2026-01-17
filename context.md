# Detective Music Player - Development Context

## Project Overview
A custom local music player built for personal use with a 2000s digital forensics/detective workstation aesthetic. Focus on information density, professional styling, and efficient workflow over minimalism.

## Design Philosophy
- 2000s investigator/digital forensics aesthetic (Girl with Dragon Tattoo, True Detective, Mindhunter)
- Functional density over minimalism (US Graphics design principles)
- Mix of 1980s IBM, Serial Experiments Lain, and cosmic horror archival vibes
- NOT ricing/tiling WM autism - tools that work, professionally styled
- Detective uses whatever works efficiently

## Color Scheme (Detective Dark)

### Backgrounds (darkest to lightest)
- Primary: `#0a0a0a` (10,10,10)
- Secondary: `#0f0f0f` (15,15,15)
- Tertiary: `#1a1a1a` (26,26,26)

### Text
- Normal: `#c0c0c0` (192,192,192)
- Muted: `#909090` (144,144,144)
- Dim: `#606060` (96,96,96)

### Accent (muted green)
- Primary: `#4a7c59` (74,124,89)
- Dim: `#2d4a38` (45,74,56)

### Borders
- Standard: `#2a2a2a` (42,42,42)

### Design Principles
- Monospace fonts everywhere (IBM Plex Mono)
- Zero border radius (sharp corners)
- 2px left border accent (#4a7c59) on active/selected elements
- Minimal borders (1px #2a2a2a)
- 3-level background hierarchy for depth
- Text selection: #4a7c59 background, #ffffff text

## UI Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ ■ EVIDENCE ARCHIVE                    [≡] [−] [□] [×]          │ #0a0a0a
├─────────────────────────────────────────────────────────────────┤
│ LIBRARY  PLAYLISTS  QUEUE  [SEARCH________________]  ⚙         │ #0f0f0f
├──────────┬──────────────────────────────────────────────────────┤
│          │ ## | TITLE              | ARTIST      | ALBUM    | TIME | CODEC | YEAR │
│ ┌────┐   │────┼────────────────────┼─────────────┼──────────┼──────┼───────┼──────│
│ │    │   │ 01 │ Track Name Here    │ Artist Name │ Album    │ 3:45 │ FLAC  │ 1979 │
│ │ ART│   │ 02 │ Another Track      │ Different   │ Same     │ 4:12 │ MP3   │ 1979 │
│ │    │   │▐03 │ Currently Playing  │ Some Artist │ Record   │ 5:33 │ FLAC  │ 1982 │
│ └────┘   │ 04 │ Next Track Up      │ Next Artist │ Next Alb │ 2:58 │ FLAC  │ 1985 │
│          │                                                                         │
│ Record   │                                                                         │
│ 1982     │                                                                         │
│ FLAC     │                                                                         │
│ 24/96    │                                                                         │
│          │                                                                         │
│ #0a0a0a  │ #0f0f0f                                                                │
├──────────┴──────────────────────────────────────────────────────┤
│ ▶  ⏮ ⏭  ◉━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━●━━━━━━━━  3:24 / 5:33          │
│                                                                                   │
│ Currently Playing - Some Artist                               🔊 ━━━━━━●━━  75%  │
│ Album Record (1982) | FLAC 24/96 | 1,234 kbps                                   │
│ #1a1a1a                                                                          │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### Layout Components

**Left Sidebar (250-300px, collapsible)**
- Album art for currently playing track
- Album metadata below (title, year, format)
- Background: #0a0a0a
- 2px right border in accent color

**Top Bar**
- Tab navigation: LIBRARY | PLAYLISTS | QUEUE
- Active tab: 2px bottom border #4a7c59
- Search box: right-aligned, monospace input
- Settings icon: far right

**Main Playlist Area**
- Spreadsheet/table view (maximum information density)
- Columns: Index | Title | Artist | Album | Time | Codec | Year | Bitrate
- All columns resizable, reorderable
- Monospace font for alignment
- Active track: 2px left border #4a7c59, slightly lighter bg (#1a1a1a)
- Text: #c0c0c0 normal, #909090 for secondary info

**Bottom Player Bar (80px fixed, two-row layout)**
- Row 1: Controls + Seekbar
  - Play/pause, prev/next minimal icons
  - Seek bar: #4a7c59 progress, #2a2a2a background
  - Time elapsed / total
- Row 2: Now playing info + Volume
  - Track - Artist (larger)
  - Album (Year) | Codec details | Bitrate (smaller, muted)
  - Volume slider: right-aligned
- Background: #1a1a1a (lightest of three tiers)

## Core Features

### Must Have (MVP)
- [x] Project structure created
- [ ] Audio playback (play/pause/seek/volume) using python-vlc
- [ ] Playlist view with sortable columns
- [ ] Library scanner (recursively scan music directory)
- [ ] Metadata reading (ID3, FLAC tags) using mutagen
- [ ] Album art display in sidebar
- [ ] Basic keyboard shortcuts (space, arrows, enter)
- [ ] M3U playlist import/export

### Nice to Have (Phase 2)
- [ ] Telescope-style fuzzy search for artists/albums/tracks
- [ ] Queue management
- [ ] Column customization (show/hide, reorder)
- [ ] Settings persistence
- [ ] Multiple playlist support
- [ ] Drag & drop file loading

### Won't Build
- ❌ Streaming services integration
- ❌ Complex DSP/equalizers
- ❌ Social features
- ❌ Mobile sync
- ❌ Online features

## Technical Stack

### Dependencies (requirements.txt)
```
PyQt6>=6.6.0                    # GUI framework
python-vlc>=3.0.0               # Audio playback
mutagen>=1.47.0                 # Metadata reading
thefuzz>=0.22.0                 # Fuzzy search
python-Levenshtein>=0.25.0      # Speedup for thefuzz
python-dotenv>=1.0.0            # Config management
```

### Key Libraries Usage

**PyQt6**
- Main window and all UI components
- QTableWidget for playlist view
- QLabel + QPixmap for album art
- Built-in stylesheets for theming

**python-vlc**
- Audio playback engine
- Handles all formats (MP3, FLAC, OGG, etc.)
- Provides play/pause/seek/volume control
```python
import vlc
player = vlc.MediaPlayer()
player.set_media(vlc.Media("path/to/track.mp3"))
player.play()
```

**mutagen**
- Read metadata from audio files
- Extract album art
- Support for ID3, FLAC, OGG, etc.
```python
from mutagen import File
audio = File("track.mp3")
title = audio.get("title", ["Unknown"])[0]
```

**thefuzz**
- Fuzzy string matching for search
```python
from thefuzz import fuzz, process
score = fuzz.partial_ratio(query, track_title)
```

## Project Structure
```
detective-player/
├── README.md
├── requirements.txt
├── .gitignore
├── main.py                    # Entry point
├── player/
│   ├── __init__.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py     # Main application window
│   │   ├── playlist_view.py   # Table widget for tracks
│   │   ├── player_bar.py      # Bottom playback controls
│   │   ├── sidebar.py         # Album art + info sidebar
│   │   └── search_overlay.py  # Telescope search UI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── audio.py           # VLC wrapper for playback
│   │   ├── library.py         # Scan & organize music files
│   │   ├── playlist.py        # Playlist data structure
│   │   └── metadata.py        # Read tags/album art
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── search.py          # Telescope fuzzy search
│   │   └── config.py          # Settings management
│   └── theme/
│       ├── __init__.py
│       └── detective.py       # Color constants + stylesheet
└── assets/
    └── placeholder.png        # Fallback album art
```

## Development Phases

### Phase 1: Core Playback (Week 1)
1. Create `player/core/audio.py` - VLC wrapper
2. Create `player/ui/player_bar.py` - Basic controls
3. Wire up play/pause/seek functionality
4. Test with hardcoded file path

### Phase 2: Library & Display (Week 2)
1. Create `player/core/library.py` - Recursive directory scanner
2. Create `player/core/metadata.py` - Tag reading with mutagen
3. Create `player/ui/playlist_view.py` - Populate table
4. Create `player/ui/main_window.py` - Assemble layout
5. Click track to play

### Phase 3: Polish (Week 3)
1. Create `player/ui/sidebar.py` - Album art display
2. Create `player/utils/search.py` - Fuzzy search implementation
3. Create `player/ui/search_overlay.py` - Search UI
4. Add keyboard shortcuts
5. M3U import/export

## Keyboard Shortcuts

### Playback
- `Space` - Play/pause
- `Right Arrow` - Next track
- `Left Arrow` - Previous track
- `Up/Down Arrow` - Volume up/down

### Navigation
- `Enter` - Play selected track
- `Tab` - Switch between panels
- `/` - Focus search (vim-style)
- `Esc` - Close search/dialogs

### Application
- `Ctrl+O` - Open file/folder
- `Ctrl+S` - Save playlist
- `Ctrl+Q` - Quit
- `F11` - Fullscreen

## Code Style Guidelines

### Naming Conventions
- Classes: `PascalCase` (e.g., `MainWindow`)
- Functions/methods: `snake_case` (e.g., `load_library`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `BG_PRIMARY`)
- Private methods: `_leading_underscore` (e.g., `_update_ui`)

### Documentation
- Docstrings for all classes and public methods
- Type hints where helpful
- Comments for complex logic only

### File Organization
- One class per file (UI components)
- Related functions grouped in utils
- Keep files under 300 lines when possible

## Example Code Patterns

### Audio Playback (player/core/audio.py)
```python
import vlc

class AudioEngine:
    def __init__(self):
        self.player = vlc.MediaPlayer()
        self.current_track = None
    
    def play(self, filepath):
        """Load and play audio file"""
        media = vlc.Media(filepath)
        self.player.set_media(media)
        self.player.play()
        self.current_track = filepath
    
    def pause(self):
        """Toggle pause state"""
        self.player.pause()
    
    def seek(self, position):
        """Seek to position (0.0 to 1.0)"""
        self.player.set_position(position)
    
    def get_position(self):
        """Get current position (0.0 to 1.0)"""
        return self.player.get_position()
```

### Metadata Reading (player/core/metadata.py)
```python
from mutagen import File
from pathlib import Path

class Track:
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        audio = File(filepath)
        
        self.title = audio.get("title", [self.filepath.stem])[0]
        self.artist = audio.get("artist", ["Unknown"])[0]
        self.album = audio.get("album", ["Unknown"])[0]
        self.year = audio.get("date", [""])[0]
        self.duration = audio.info.length if audio.info else 0
        
        # Album art
        self.album_art = self._extract_album_art(audio)
    
    def _extract_album_art(self, audio):
        """Extract album art as bytes"""
        # Implementation depends on audio format
        # Return None if no art found
        pass
```

### Qt Stylesheet Application
```python
from player.theme.detective import get_stylesheet

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(get_stylesheet())
        # Rest of initialization
```

## Testing Approach

### Manual Testing
- Test with various audio formats (MP3, FLAC, OGG, WAV)
- Test with missing metadata
- Test with missing album art
- Test large libraries (1000+ tracks)
- Test keyboard shortcuts

### No Unit Tests Initially
- Focus on getting it working
- Add tests later if needed
- This is a personal tool, not production software

## Configuration

### Settings to Persist
- Music library path
- Window size/position
- Column visibility/order
- Volume level
- Last playing track/position

### Config File Location
- `~/.config/detective-player/config.ini`
- Use Python's `configparser` module

## Known Limitations

### Intentional Scope Limits
- Local files only (no streaming)
- No network features
- No plugin system
- Single user (no accounts)

### Technical Constraints
- VLC must be installed on system
- Large libraries may be slow to scan initially
- Album art limited by file metadata

## Resources & References

### Documentation
- PyQt6: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- python-vlc: https://www.olivieraubert.net/vlc/python-ctypes/
- mutagen: https://mutagen.readthedocs.io/

### Similar Projects (for reference, not copying)
- Tauon Music Box (inspiration for this project)
- Foobar2000 (information density)
- Clementine (library management)

## Current Status

**Completed:**
- [x] Project structure created
- [x] Dependencies defined
- [x] Theme constants defined
- [x] Basic main.py entry point

**Next Steps:**
1. Implement audio playback engine (`player/core/audio.py`)
2. Create basic player controls UI (`player/ui/player_bar.py`)
3. Test playback with hardcoded file

**Blocked:**
- None currently

## Development Environment

- OS: EndeavourOS (Arch-based)
- Desktop: KDE Plasma
- Python: 3.11+
- IDE: Zed / Helix
- Virtual environment: `venv` in project root

## Notes for Claude Code

- This is a personal project for learning and daily use
- Prioritize functionality over perfect code
- Detective aesthetic is important - sharp corners, monospace, information density
- When unsure about UI decisions, favor more information over less
- Keyboard shortcuts should feel natural but mouse usage is fine
- Don't overengineer - this isn't production software
- Ask for clarification if design decisions are ambiguous

## Additional Context

This player is part of a larger "detective workstation" aesthetic setup including:
- Custom rofi menus with similar color scheme
- Obsidian vault for note-taking (~/Dokumenter/Fieldnotes/)
- Mullvad VPN integration
- IBM Plex Mono typography throughout system

The music player should feel like it belongs to this ecosystem - professional, dense with information, monospace everywhere, muted green accents on active elements.