from __future__ import annotations

import ctypes
import sys

from PySide6.QtWidgets import QApplication

from . import APP_NAME
from .clicker import Clicker, set_timer_resolution
from .config import Config
from .hotkeys import HotkeyManager
from .ui.main_window import MainWindow


def main() -> int:
    # ícone correto na barra de tarefas (em vez do ícone do python.exe)
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("macdh.autoclicker")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")

    set_timer_resolution(True)
    cfg = Config()
    clicker = Clicker()
    hotkeys = HotkeyManager()
    window = MainWindow(cfg, clicker, hotkeys)
    hotkeys.start()
    window.show()

    code = app.exec()
    set_timer_resolution(False)
    return code


if __name__ == "__main__":
    sys.exit(main())
