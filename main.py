#!/usr/bin/env python3
"""Detective Music Player - Entry point."""

import sys

from PyQt6.QtWidgets import QApplication

from player.ui.main_window import MainWindow


DEFAULT_MUSIC_PATH = "/home/sonne/Musik/Bob Dylan/"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(" Archive")

    window = MainWindow(initial_path=DEFAULT_MUSIC_PATH)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
