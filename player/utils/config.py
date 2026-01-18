"""Settings persistence for the player."""

import configparser
from pathlib import Path
from dataclasses import dataclass, field


CONFIG_DIR = Path.home() / ".config" / "wired"
CONFIG_FILE = CONFIG_DIR / "config.ini"


@dataclass
class PlayerConfig:
    """Player configuration settings."""

    # Window
    window_x: int = 100
    window_y: int = 100
    window_width: int = 1200
    window_height: int = 700

    # Audio
    volume: int = 75

    # Library
    last_library_path: str = ""

    # Playback state
    last_track_index: int = -1
    shuffle_enabled: bool = False

    # Queue (pipe-separated file paths)
    queue_paths: list[str] = field(default_factory=list)
    queue_panel_visible: bool = False


def load_config() -> PlayerConfig:
    """Load configuration from file."""
    config = PlayerConfig()

    if not CONFIG_FILE.exists():
        return config

    parser = configparser.ConfigParser()
    try:
        parser.read(CONFIG_FILE)

        # Window section
        if "Window" in parser:
            window = parser["Window"]
            config.window_x = int(window.get("x", config.window_x))
            config.window_y = int(window.get("y", config.window_y))
            config.window_width = int(window.get("width", config.window_width))
            config.window_height = int(window.get("height", config.window_height))

        # Audio section
        if "Audio" in parser:
            audio = parser["Audio"]
            config.volume = int(audio.get("volume", config.volume))

        # Library section
        if "Library" in parser:
            library = parser["Library"]
            config.last_library_path = library.get("last_path", config.last_library_path)

        # Playback section
        if "Playback" in parser:
            playback = parser["Playback"]
            config.last_track_index = int(playback.get("last_track_index", config.last_track_index))
            config.shuffle_enabled = playback.get("shuffle_enabled", "false").lower() == "true"

        # Queue section
        if "Queue" in parser:
            queue_section = parser["Queue"]
            paths = queue_section.get("paths", "")
            if paths:
                config.queue_paths = paths.split("|")
            config.queue_panel_visible = queue_section.get("panel_visible", "false").lower() == "true"

    except Exception:
        # Return defaults on any error
        pass

    return config


def save_config(config: PlayerConfig) -> None:
    """Save configuration to file."""
    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    parser = configparser.ConfigParser()

    # Window section
    parser["Window"] = {
        "x": str(config.window_x),
        "y": str(config.window_y),
        "width": str(config.window_width),
        "height": str(config.window_height),
    }

    # Audio section
    parser["Audio"] = {
        "volume": str(config.volume),
    }

    # Library section
    parser["Library"] = {
        "last_path": config.last_library_path,
    }

    # Playback section
    parser["Playback"] = {
        "last_track_index": str(config.last_track_index),
        "shuffle_enabled": str(config.shuffle_enabled).lower(),
    }

    # Queue section
    parser["Queue"] = {
        "paths": "|".join(config.queue_paths),
        "panel_visible": str(config.queue_panel_visible).lower(),
    }

    try:
        with open(CONFIG_FILE, "w") as f:
            parser.write(f)
    except Exception:
        # Silently fail on write errors
        pass
