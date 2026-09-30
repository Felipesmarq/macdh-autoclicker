from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSpinBox, QVBoxLayout

from ..keys import build_combo, modifier_from_vk, pretty_combo, vk_to_name


class Card(QFrame):
    """Bloco com título; adicione conteúdo via self.body (QVBoxLayout)."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 18)
        outer.setSpacing(12)
        head = QLabel(title)
        head.setObjectName("cardTitle")
        outer.addWidget(head)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body)


def make_spin(minimum: int, maximum: int, suffix: str = "", width: int = 84) -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, maximum)
    box.setSuffix(suffix)
    box.setButtonSymbols(QSpinBox.NoButtons)
    box.setAlignment(Qt.AlignCenter)
    box.setFixedWidth(width)
    box.setKeyboardTracking(False)
    return box


def repolish(widget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class HotkeyEdit(QPushButton):
    """Clique, pressione a combinação desejada. Esc cancela."""

    changed = Signal(str)
    capturing = Signal(bool)

    def __init__(self, combo: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("hotkey")
        self.setCursor(Qt.PointingHandCursor)
        self._combo = combo
        self._capturing = False
        self.clicked.connect(self._begin)
        self._refresh()

    @property
    def combo(self) -> str:
        return self._combo

    def set_combo(self, combo: str) -> None:
        self._combo = combo
        self._refresh()

    def _refresh(self) -> None:
        text = "Pressione as teclas…" if self._capturing else (pretty_combo(self._combo) or "— sem atalho —")
        self.setText(text)
        self.setProperty("capturing", self._capturing)
        repolish(self)

    def _begin(self) -> None:
        if self._capturing:
            return
        self._capturing = True
        self.grabKeyboard()
        self.capturing.emit(True)
        self._refresh()

    def _end(self) -> None:
        if not self._capturing:
            return
        self._capturing = False
        self.releaseKeyboard()
        self.capturing.emit(False)
        self._refresh()

    def keyPressEvent(self, event) -> None:
        if not self._capturing:
            return super().keyPressEvent(event)
        if event.isAutoRepeat():
            return
        vk = event.nativeVirtualKey()
        if modifier_from_vk(vk):
            return
        if event.key() == Qt.Key_Escape and event.modifiers() == Qt.NoModifier:
            return self._end()
        name = vk_to_name(vk)
        if not name:
            return
        mods = set()
        m = event.modifiers()
        if m & Qt.ControlModifier:
            mods.add("ctrl")
        if m & Qt.ShiftModifier:
            mods.add("shift")
        if m & Qt.AltModifier:
            mods.add("alt")
        if m & Qt.MetaModifier:
            mods.add("meta")
        self._combo = build_combo(mods, name)
        self._end()
        self.changed.emit(self._combo)

    def focusOutEvent(self, event) -> None:
        self._end()
        super().focusOutEvent(event)
