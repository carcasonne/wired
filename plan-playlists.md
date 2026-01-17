# Playlists, M3U, and Smart Filters - Design Plan

## Current State
- Single playlist view showing all library tracks
- Search overlay for finding tracks (modal, temporary)
- Queue panel for "up next" tracks
- Sidebar shows current track info + album art

## Design Goals
1. **Named Playlists** - Create, save, load custom playlists
2. **M3U Import/Export** - Standard playlist file support
3. **Smart Filters / Views** - Dynamic playlists based on metadata (artist, album, genre, year)

---

## UI Layout Proposal

```
┌─────────────────────────────────────────────────────────────────────────┐
│ WIRED                                              [scan status] [stats]│
├────────────┬────────────────────────────────────────────┬───────────────┤
│            │                                            │               │
│  SIDEBAR   │              PLAYLIST VIEW                 │  QUEUE PANEL  │
│  (280px)   │              (flex)                        │  (280px)      │
│            │                                            │               │
│ ┌────────┐ │  ┌─────────────────────────────────────┐   │               │
│ │Album   │ │  │ Filter Bar (when active)            │   │               │
│ │Art     │ │  │ [Artist ▼] [Album ▼] [x clear]      │   │               │
│ │        │ │  └─────────────────────────────────────┘   │               │
│ └────────┘ │                                            │               │
│            │  ┌─────────────────────────────────────┐   │               │
│ Album      │  │ Track table (filtered or full)      │   │               │
│ Year       │  │                                     │   │               │
│ Codec      │  │                                     │   │               │
│ Quality    │  │                                     │   │               │
│            │  └─────────────────────────────────────┘   │               │
│────────────│                                            │               │
│            │                                            │               │
│ PLAYLISTS  │                                            │               │
│ ┌────────┐ │                                            │               │
│ │▸ Library│ │                                            │               │
│ │  Rock   │ │                                            │               │
│ │  Chill  │ │                                            │               │
│ │  + New  │ │                                            │               │
│ └────────┘ │                                            │               │
│            │                                            │               │
├────────────┴────────────────────────────────────────────┴───────────────┤
│ [Player Bar]                                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Sidebar Enhancement - Playlist List

Add a collapsible section below the album art/metadata:

```
─── PLAYLISTS ───────────────
▸ Library            (12,847)   <- Full library (special, always first)
  Rock Favorites        (156)   <- User playlist
  Late Night Chill       (42)   <- User playlist
  2024 Releases          (89)   <- User playlist
  + New Playlist               <- Create new
```

**Interactions:**
- Click playlist name → switch view to that playlist
- Right-click → context menu: Rename, Delete, Export M3U
- Drag track from playlist view → drop on playlist name to add
- Double-click "Library" → return to full library view
- "▸" indicator shows currently active playlist

**Styling:**
- Monospace, compact list
- Accent color for active playlist
- Muted track count on right
- Subtle hover highlight

---

### 2. Filter Bar (Above Playlist View)

A horizontal bar that appears when filtering is active:

```
┌─────────────────────────────────────────────────────────────────┐
│ FILTER: [Artist: Blondie ▼] [Album: Parallel Lines ▼] [× Clear]│
└─────────────────────────────────────────────────────────────────┘
```

**Filter Types:**
- **Artist** - Dropdown with all artists in current view
- **Album** - Dropdown with albums (filtered by artist if set)
- **Year** - Dropdown or range picker
- **Genre** - If metadata available (many files don't have this)
- **Codec** - FLAC, MP3, etc.

**Activation:**
- Click column header dropdown arrow → filter by that column
- Or use keyboard: `f` to open filter mode, type to search
- Filters are additive (AND logic)

**Behavior:**
- Filtering creates a **temporary view**, not a new playlist
- "Save as Playlist" button appears when filter is active
- Clear button removes all filters, returns to full view

---

### 3. Playlist Data Model

```python
@dataclass
class SavedPlaylist:
    id: str              # UUID
    name: str
    track_paths: list[str]  # File paths (not Track objects)
    created_at: datetime
    modified_at: datetime

class PlaylistManager:
    """Manages saved playlists, stored in SQLite."""

    def get_all() -> list[SavedPlaylist]
    def create(name: str) -> SavedPlaylist
    def rename(id: str, name: str)
    def delete(id: str)
    def add_tracks(id: str, paths: list[str])
    def remove_tracks(id: str, paths: list[str])
    def reorder_tracks(id: str, new_order: list[str])
    def export_m3u(id: str, filepath: Path)
    def import_m3u(filepath: Path) -> SavedPlaylist
```

**Storage:** New table in existing SQLite database:
```sql
CREATE TABLE playlists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at REAL,
    modified_at REAL
);

CREATE TABLE playlist_tracks (
    playlist_id TEXT,
    track_path TEXT,
    position INTEGER,
    FOREIGN KEY (playlist_id) REFERENCES playlists(id)
);
```

---

### 4. M3U Import/Export

**Export Format (Extended M3U):**
```m3u
#EXTM3U
#PLAYLIST:Rock Favorites
#EXTINF:213,Blondie - Heart of Glass
/home/user/Music/Blondie/Parallel Lines/01 - Heart of Glass.flac
#EXTINF:186,Blondie - One Way or Another
/home/user/Music/Blondie/Parallel Lines/02 - One Way or Another.flac
```

**Import Behavior:**
- Parse M3U, resolve relative paths to absolute
- Skip missing files with warning
- Create new playlist with M3U filename as name
- Handle both simple (.m3u) and extended (.m3u8) formats

**Menu Integration:**
- File → Import Playlist... (Ctrl+I)
- Right-click playlist → Export as M3U...

---

### 5. Smart Filters vs Static Playlists

Two concepts:

| Feature | Static Playlist | Smart Filter |
|---------|-----------------|--------------|
| Content | Fixed track list | Dynamic query |
| Updates | Manual add/remove | Auto-updates with library |
| Use case | "My favorites" | "All FLAC files" |
| Storage | List of paths | Filter criteria |

**Smart Filter Examples:**
- "All tracks by Blondie"
- "FLAC files from 2020+"
- "Albums with 'Live' in name"

**Implementation:** Start with static playlists + temporary filters. Smart filters can be Phase 4.

---

### 6. Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `f` | Open filter bar / focus filter |
| `Esc` | Clear filter / close filter bar |
| `Ctrl+N` | New playlist |
| `Ctrl+S` | Save current filter as playlist |
| `Ctrl+I` | Import M3U |
| `1-9` | Switch to playlist 1-9 |

---

### 7. Context Menu Enhancements

**Right-click on track(s):**
```
Play Next                    [n]
Add to Queue                 [a]
─────────────────────────────
Add to Playlist            ▸
  Rock Favorites
  Late Night Chill
  + New Playlist...
Remove from Playlist         [Del]  (only if in user playlist)
─────────────────────────────
Filter by Artist: "Blondie"
Filter by Album: "Parallel Lines"
```

---

## Implementation Phases

### Phase A: Playlist Infrastructure
1. Add `playlists` and `playlist_tracks` tables to database.py
2. Create PlaylistManager class
3. Add playlist list UI to sidebar
4. Wire up playlist switching

### Phase B: Playlist Operations
1. Create/rename/delete playlists
2. Add tracks to playlist (context menu + drag-drop)
3. Remove tracks from playlist
4. Reorder tracks in playlist

### Phase C: M3U Support
1. M3U parser (import)
2. M3U writer (export)
3. Menu integration
4. Handle missing files gracefully

### Phase D: Filter Bar
1. Filter bar UI component
2. Column-based filtering (artist, album, year, codec)
3. "Save as Playlist" from filter
4. Keyboard navigation

---

## Visual Mockup - Sidebar with Playlists

```
┌─────────────────────────┐
│      ┌─────────────┐    │
│      │             │    │
│      │  Album Art  │    │
│      │             │    │
│      └─────────────┘    │
│                         │
│  Parallel Lines         │
│  1978                   │
│  FLAC                   │
│  44.1 kHz / 16-bit      │
│                         │
│─────────────────────────│
│  ─── PLAYLISTS ───      │
│                         │
│  ▸ Library      12,847  │  <- green accent = active
│    Rock            156  │
│    Chill            42  │
│    80s Mix          89  │
│                         │
│  + New Playlist         │  <- muted, creates on click
│                         │
└─────────────────────────┘
```

---

## Questions to Resolve

1. **Multi-select tracks?** Currently single-select. Multi-select would help "add 10 tracks to playlist". Recommend: Yes, add Ctrl+click / Shift+click.

2. **Playlist in queue panel?** Should queue panel show which playlist a queued track came from? Probably not necessary.

3. **Genre tag support?** Many files lack genre tags. Should we:
   - Show genre column if available
   - Skip genre filtering entirely
   - Allow user to tag tracks manually (Phase 5+)

4. **Nested folders as pseudo-playlists?** E.g., auto-create "playlists" from folder structure. Could be nice but adds complexity.

---

## Summary

This design adds:
- **Playlist list in sidebar** (always visible, compact)
- **Filter bar above tracks** (temporary, saveable)
- **M3U import/export** (standard format)
- **Context menu integration** (add to playlist)

The aesthetic remains minimal/detective-themed. New UI elements use the same monospace font, accent colors, and spacing patterns.
