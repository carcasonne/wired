# WIRED

Local music player for users who value information density over visual minimalism.

```
STATUS .............. OPERATIONAL
VERSION ............. 0.1.0
LICENSE ............. MIT
PLATFORM ............ LINUX
```

---

## OVERVIEW

Wired is a keyboard-driven music player built for local file playback. The interface follows U.S. Graphics Company design principles: explicit labels, dense information display, technical nomenclature, and zero decorative elements.

The application is designed for users who:
- Maintain local music libraries
- Prefer keyboard navigation over mouse interaction
- Want metadata visibility without visual clutter
- Need efficient queue and playlist management

---

## SYSTEM REQUIREMENTS

```
COMPONENT           REQUIREMENT
-------------------------------------------------
Operating System    Linux (tested on Arch/EndeavourOS)
Python              3.11 or higher
VLC                 System installation required
Display             1280x720 minimum resolution
```

---

## INSTALLATION

### 1. Clone Repository

```
git clone <repository-url>
cd wired
```

### 2. Create Virtual Environment

```
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```
pip install -r requirements.txt
```

### 4. Verify VLC Installation

```
vlc --version
```

If VLC is not installed:
```
# Arch/EndeavourOS
sudo pacman -S vlc

# Debian/Ubuntu
sudo apt install vlc

# Fedora
sudo dnf install vlc
```

### 5. Launch Application

```
python main.py
```

---

## INTERFACE LAYOUT

```
+---------------------------+---------------------------------------+
| CURRENT                   | HEADER BAR                            |
|  [Album Art]              +---------------------------------------+
|                           | #  | TITLE      | ARTIST   | ALBUM    |
+---------------------------+ 01 | Track One  | Artist A | Album X  |
| MEDIA INFO                | 02 | Track Two  | Artist B | Album Y  |
|  ALBUM    Album Name      |>03 | Playing    | Artist C | Album Z  |
|  YEAR     2024            | 04 | Track Four | Artist D | Album W  |
|  CODEC    FLAC            |                                       |
|  SAMPLE   16-BIT / 44 KHZ |                                       |
|  BITRATE  1411 KBPS       |                                       |
+---------------------------+---------------------------------------+
| PLAYLISTS            [+]  | TRACK    Currently Playing Track      |
|  LIBRARY  [1,234]         | ARTIST   Artist Name                  |
|  Playlist One  [45]       +---------------------------------------+
|  Playlist Two  [128]      | SOURCE   | POSITION | TRANSPORT| LEVEL|
+---------------------------+---------------------------------------+
```

---

## KEYBOARD REFERENCE

### TRANSPORT CONTROLS

```
KEY             ACTION
-------------------------------------------------
Space           Play / Pause
Left Arrow      Previous track
Right Arrow     Next track
+ / =           Volume up (5%)
-               Volume down (5%)
```

### NAVIGATION

```
KEY             ACTION
-------------------------------------------------
Up / Down       Navigate track list
Enter           Play selected track
f  /  /         Open search overlay
Ctrl+F          Open filter overlay
Escape          Close overlay / Clear filters
q               Toggle queue panel
g               Open artist view
```

### QUEUE OPERATIONS

```
KEY             ACTION
-------------------------------------------------
n               Play next (insert at queue front)
a               Add to queue (append to queue end)
x               Toggle queue status
```

### PLAYLIST OPERATIONS

```
KEY             ACTION
-------------------------------------------------
Delete          Remove from playlist (playlist view only)
```

### APPLICATION

```
KEY             ACTION
-------------------------------------------------
Ctrl+O          Open folder (temporary)
Ctrl+I          Import M3U playlist
Ctrl+Q          Quit application
```

---

## FEATURES

### LIBRARY MANAGEMENT

- SQLite-cached metadata for sub-second startup
- Background scanning with progress indication
- Incremental updates (detects added/removed files)
- Supported formats: MP3, FLAC, OGG, WAV, M4A, OPUS

### SEARCH SYSTEM

Telescope-style fuzzy search accessible via `f` or `/`:
- Searches across title, artist, album fields
- Results ranked by match quality
- Artist results link to artist dossier view

### FILTER SYSTEM

Multi-field filtering accessible via `Ctrl+F`:
- Filter by artist, album, year, codec
- Multiple filters combine with AND logic
- Save filter results as new playlist

### QUEUE SYSTEM

Manual queue for controlling playback order:
- Play Next: Insert track at front of queue
- Add to Queue: Append track to end of queue
- Queue persists when browsing different views
- Queue state saved on application exit

### PLAYLIST MANAGEMENT

- Create, rename, delete playlists
- Bulk add/remove tracks
- M3U import and export
- Track counts displayed in sidebar

### ARTIST DOSSIER

Album grid view for individual artists:
- Discography with cover art
- Statistics (tracks, albums, total duration)
- Keyboard navigation through albums
- Play All functionality

---

## CONFIGURATION

Settings stored at: `~/.config/wired/config.json`

Persisted state includes:
- Window geometry
- Volume level
- Queue contents
- Panel visibility
- Shuffle state
- Library path

---

## FILE SUPPORT

```
FORMAT          EXTENSION       METADATA
-------------------------------------------------
FLAC            .flac           Vorbis Comments
MP3             .mp3            ID3v2
OGG Vorbis      .ogg            Vorbis Comments
WAV             .wav            Limited
M4A/AAC         .m4a            MP4 Tags
Opus            .opus           Vorbis Comments
```

---

## ARCHITECTURE

```
player/
  core/
    audio.py ............. VLC playback engine
    database.py .......... SQLite operations
    library.py ........... Directory scanning
    metadata.py .......... Track data structure
    playlist.py .......... In-memory playlist
    playlist_manager.py .. Saved playlist storage
    queue.py ............. Manual queue

  ui/
    main_window.py ....... Application container
    sidebar.py ........... Album art + info + playlists
    playlist_view.py ..... Track table
    player_bar.py ........ Transport controls
    queue_panel.py ....... Queue display
    search_overlay.py .... Fuzzy search
    filter_overlay.py .... Field filtering
    artist_overlay.py .... Artist dossier

  theme/
    lainchan.py .......... Colors + stylesheet

  utils/
    config.py ............ Settings persistence
    search.py ............ Search algorithms
```

---

## KNOWN LIMITATIONS

```
LIMITATION                  NOTES
-------------------------------------------------
VLC dependency              System VLC installation required
First scan performance      Large libraries may take time
Album art source            Embedded tags only (no folder.jpg)
Gapless playback            Not implemented
Crossfade                   Not implemented
```

---

## TROUBLESHOOTING

### Application fails to start

Verify VLC installation:
```
python -c "import vlc; print(vlc.libvlc_get_version())"
```

### No audio output

Check VLC audio configuration:
```
vlc --aout=pulse  # or alsa, jack
```

### Missing metadata

Ensure files have embedded tags. Use a tool like `kid3` or `picard` to verify and edit metadata.

### Database corruption

Remove the database file to force rescan:
```
rm ~/.local/share/wired/wired.db
```

---

## DEVELOPMENT

### Running from source

```
source venv/bin/activate
python main.py
```

### Project documentation

See `context.md` for detailed development notes, architecture decisions, and implementation status.

---

## LICENSE

MIT License. See LICENSE file for full text.
