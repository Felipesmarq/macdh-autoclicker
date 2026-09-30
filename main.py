"""Ponto de entrada (usado pelo PyInstaller e por `uv run python main.py`)."""
import sys

from autoclicker.app import main

if __name__ == "__main__":
    sys.exit(main())
