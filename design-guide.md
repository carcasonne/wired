**System Setup Summary - Detective Workstation Aesthetic**

**Core Philosophy:**
- 2000s investigator/digital forensics aesthetic (Girl with Dragon Tattoo, True Detective, Mindhunter)
- Functional density over minimalism (US Graphics design principles)
- Mix of 1980s IBM, Serial Experiments Lain, and cosmic horror archival vibes (Excavation of Hob's Barrow)
- NOT ricing/tiling WM autism - tools that work, professionally styled
- Detective uses whatever works efficiently, not keyboard-only obsession

**OS & Desktop:**
- EndeavourOS + KDE Plasma (keeping it, sensible defaults)
- Dark professional theme, not pure minimalism
- Touchpad usage accepted, not full keyboard-driven

**Installed & Configured:**

**VPN:**
- Mullvad via native WireGuard (no app)
- nmcli for management
- Custom rofi menu (~/.local/bin/vpn-menu) with:
  - Alphabetically sorted servers
  - [ACTIVE] indicator in accent color (#4a7c59)
  - Toggle on/off by selecting active connection
  - Keybind: Meta+V
- Configs stored: ~/.config/mullvad/configs/
- Account number in KeePassXC

**Application Launcher:**
- Custom rofi theme (~/.config/rofi/launcher.rasi)
- Script: ~/.local/bin/app-launcher
- Keybind: Meta+Space
- Features:
  - Text-only case file aesthetic (no icons)
  - Status bar: VPN status, memory usage, uptime
  - Frequency-based sorting (learns usage patterns)
  - Two modes: EXECUTE (apps) / COMMAND (raw)
  - 2px left border accent on selection

**Quick Note Capture:**
- Script: ~/.local/bin/quick-note
- Keybind: Meta+N
- Saves to: ~/Dokumenter/Fieldnotes/inbox/
- Format: YYYY-MM-DD_HHMM.md with frontmatter
- Minimal friction: hotkey → text → saved
- Options tested: rofi, yad, terminal (nano/helix), dmenu

**Email:**
- Mailspring with custom theme

**Text Editing:**
- Zed (primary choice)
- Custom theme: Detective Dark (~/.config/zed/themes/detective-dark.json)
- Not using neovim (too sluggish for writing)
- Helix as alternative

**File Management:**
- Ranger (TUI file manager, vim keybinds)
- Dolphin (KDE GUI) for when needed - no shame, it works

**Knowledge Management - Obsidian:**

Vault path: ~/Dokumenter/Fieldnotes/

Structure:
├── inbox/          # quick captures, unsorted
├── articles/       # processed web articles  
├── papers/         # academic
├── books/          # gutenberg notes
├── people/         # person profiles
├── topics/         # subject areas
├── projects/       # investigations
├── journal/        # daily notes
└── templates/      # note templates

**Typography:**
- IBM Plex Mono (primary monospace)
- Berkeley Mono (alternative)
- Cormorant (serif for long-form)

**Rofi Configuration:**
- Default theme: ~/.config/rofi/config.rasi (for VPN, utilities)
- Launcher theme: ~/.config/rofi/launcher.rasi (for app launcher)
- Both use detective color palette
- Sharp corners, monospace, minimal borders

**Not Using:**
- Tiling WMs (i3/sway/hyprland) - unnecessary complexity
- Pure keyboard workflow - touchpad is fine
- Vim for everything - wrong tool obsession
- Transparent terminals - reduces readability

**Core Principle:**
Function over form. Investigator uses efficient tools with professional aesthetic. 2000s corporate forensics workstation, not anime rice screenshots. Information density, clear typography, systematic workflow. The aesthetic comes from consistent color palette + typography + functional density, not from using obscure tools.

**Keybind Summary:**
- Meta+V: VPN menu
- Meta+Space: Application launcher
- Meta+N: Quick note capture

---

**Custom Color Theme:**

**Backgrounds (darkest to lightest):**
- Primary: #0a0a0a
- Secondary: #0f0f0f
- Tertiary: #1a1a1a

**Text:**
- Normal: #c0c0c0
- Muted: #909090
- Dim: #606060

**Accent (muted green):**
- Primary: #4a7c59
- Dim: #2d4a38

**Borders:**
- Standard: #2a2a2a

**Key Design Principles:**
- Monospace fonts everywhere (IBM Plex Mono)
- Zero border radius (sharp corners)
- 2px left border accent (#4a7c59) on active/selected elements
- Minimal borders (1px #2a2a2a)
- 3-level background hierarchy for depth
- Text selection: #4a7c59 background, #ffffff text