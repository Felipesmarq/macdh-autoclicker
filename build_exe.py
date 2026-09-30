"""Gera dist/MacDH-AutoClicker.exe (um único arquivo, sem console).

Uso:  uv run python build_exe.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication

from autoclicker.ui.theme import make_icon

ROOT = Path(__file__).parent
ICON = ROOT / "build" / "icon.ico"


def make_ico() -> Path:
    ICON.parent.mkdir(exist_ok=True)
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    pixmap = make_icon("#7c5cff", 256).pixmap(256, 256)
    if not pixmap.save(str(ICON), "ICO"):
        raise SystemExit("Falha ao gerar icon.ico")
    del app
    return ICON


def main() -> None:
    icon = make_ico()
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "MacDH-AutoClicker",
        "--icon", str(icon),
        "--paths", str(ROOT),
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "tkinter",
        str(ROOT / "main.py"),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    print("\nPronto:", ROOT / "dist" / "MacDH-AutoClicker.exe")


if __name__ == "__main__":
    main()
