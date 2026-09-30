"""Temas (QSS) e ícone gerado por código."""
from __future__ import annotations

from pathlib import Path
from string import Template

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

PALETTES = {
    "dark":   dict(bg="#13131a", card="#1b1b25", border="#2a2a39", text="#e9e9f2", muted="#8a8aa0", input="#22222f"),
    "light":  dict(bg="#f2f2f8", card="#ffffff", border="#e0e0ea", text="#1a1a26", muted="#6a6a80", input="#f0f0f6"),
    "amoled": dict(bg="#000000", card="#0a0a0e", border="#1b1b24", text="#ececf4", muted="#7c7c90", input="#121218"),
}

ACCENT_PRESETS = ["#7c5cff", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#14b8a6", "#a3e635"]

_QSS = Template("""
* { font-family: "Segoe UI"; font-size: 13px; color: $text; }
QMainWindow, QWidget#root { background: $bg; }
QWidget#page, QWidget#scrollBody { background: transparent; }
QFrame#card { background: $card; border: 1px solid $border; border-radius: ${radius}px; }
QLabel#cardTitle { font-weight: 600; font-size: 14px; background: transparent; }
QLabel#pageTitle { font-weight: 700; font-size: 20px; }
QLabel#muted { color: $muted; background: transparent; }
QLabel#brand { font-weight: 700; font-size: 16px; }
QLabel { background: transparent; }
QLabel#status { font-weight: 600; font-size: 15px; }
QLabel#stat { font-weight: 600; font-size: 15px; }

QSpinBox, QComboBox, QLineEdit {
    background: $input; border: 1px solid $border; border-radius: 8px;
    padding: 6px 10px; min-height: 20px; selection-background-color: $accent; selection-color: $onaccent;
}
QSpinBox:focus, QComboBox:focus, QLineEdit:focus { border: 1px solid $accent; }
QComboBox QAbstractItemView {
    background: $card; border: 1px solid $border; outline: 0;
    selection-background-color: $accent; selection-color: $onaccent;
}

QPushButton {
    background: $input; border: 1px solid $border; border-radius: 8px; padding: 7px 14px;
}
QPushButton:hover { border: 1px solid $accent; }
QPushButton:pressed { background: $accent_soft; }
QPushButton:disabled { color: $muted; }
QPushButton#primary {
    background: $accent; color: $onaccent; border: none; font-weight: 700; font-size: 15px;
    padding: 12px 30px; border-radius: ${radius}px;
}
QPushButton#primary:hover { background: $accent_hover; }
QPushButton#primary[running="true"] { background: $danger; color: #ffffff; }
QPushButton#hotkey { font-family: Consolas, monospace; font-weight: 600; min-width: 190px; }
QPushButton#hotkey[capturing="true"] { border: 1px solid $accent; color: $accent; background: $accent_soft; }
QPushButton#swatch { border-radius: 13px; min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px; padding: 0; border: 2px solid transparent; }
QPushButton#swatch[selected="true"] { border: 2px solid $text; }

QListWidget#nav { background: transparent; border: none; outline: 0; }
QListWidget#nav::item { padding: 11px 14px; border-radius: 9px; margin: 2px 0; color: $muted; }
QListWidget#nav::item:hover { background: $input; color: $text; }
QListWidget#nav::item:selected { background: $accent_soft; color: $accent; }

QSlider::groove:horizontal { height: 6px; background: $input; border-radius: 3px; }
QSlider::sub-page:horizontal { background: $accent; border-radius: 3px; }
QSlider::handle:horizontal { background: $accent; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }

QComboBox::drop-down { border: none; background: transparent; width: 28px; }
QComboBox::down-arrow { image: url($arrow); width: 12px; height: 12px; }
QRadioButton, QCheckBox { spacing: 9px; background: transparent; }
QRadioButton::indicator { width: 14px; height: 14px; border-radius: 9px; border: 2px solid $muted; background: $input; }
QRadioButton::indicator:hover, QCheckBox::indicator:hover { border-color: $accent; }
QRadioButton::indicator:checked { border: 2px solid $accent; background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 $accent, stop:0.5 $accent, stop:0.6 $input, stop:1 $input); }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 5px; border: 2px solid $muted; background: $input; }
QCheckBox::indicator:checked { border: 2px solid $accent; background: $accent; image: url($check); }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: $border; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: $card; color: $text; border: 1px solid $border; padding: 4px 8px; }
""")


def _luma(c: QColor) -> float:
    return 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()


def _write_glyphs(folder: Path, muted: str, onaccent: str) -> tuple[str, str]:
    """Gera seta (combo) e check (checkbox) em PNG; o QSS só aceita imagens por arquivo."""
    folder.mkdir(parents=True, exist_ok=True)
    arrow, check = folder / "arrow.png", folder / "check.png"
    for path, color, draw in ((arrow, muted, "arrow"), (check, onaccent, "check")):
        pm = QPixmap(48, 48)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(color), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if draw == "arrow":
            p.drawPolyline([QPointF(12, 18), QPointF(24, 30), QPointF(36, 18)])
        else:
            p.drawPolyline([QPointF(10, 25), QPointF(20, 35), QPointF(38, 14)])
        p.end()
        pm.save(str(path), "PNG")
    return arrow.as_posix(), check.as_posix()


def build_qss(appearance: dict, assets_dir: Path) -> str:
    pal = PALETTES.get(appearance["theme"], PALETTES["dark"])
    accent = QColor(appearance["accent"])
    if not accent.isValid():
        accent = QColor("#7c5cff")
    onaccent = "#111111" if _luma(accent) > 170 else "#ffffff"
    arrow, check = _write_glyphs(assets_dir, pal["muted"], onaccent)
    hover = accent.lighter(115) if _luma(accent) < 200 else accent.darker(110)
    soft = f"rgba({accent.red()}, {accent.green()}, {accent.blue()}, 42)"
    return _QSS.substitute(
        **pal,
        accent=accent.name(),
        accent_hover=hover.name(),
        accent_soft=soft,
        onaccent=onaccent,
        arrow=arrow,
        check=check,
        danger="#e5484d",
        radius=int(appearance["radius"]),
    )


def make_icon(accent: str = "#7c5cff", size: int = 256) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(accent))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)
    s = size / 256
    arrow = QPainterPath()
    arrow.moveTo(80 * s, 56 * s)
    arrow.lineTo(80 * s, 192 * s)
    arrow.lineTo(116 * s, 158 * s)
    arrow.lineTo(140 * s, 210 * s)
    arrow.lineTo(164 * s, 199 * s)
    arrow.lineTo(140 * s, 148 * s)
    arrow.lineTo(190 * s, 148 * s)
    arrow.closeSubpath()
    p.setBrush(QColor("#ffffff"))
    p.drawPath(arrow)
    p.end()
    return QIcon(pm)
