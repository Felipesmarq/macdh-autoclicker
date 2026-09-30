"""Hotkeys globais editáveis (pynput) com suporte a 'segurar para clicar'."""
from __future__ import annotations

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

from .keys import modifier_from_vk, parse_combo, vk_to_name


def _vk(key) -> int | None:
    code = key.value if isinstance(key, keyboard.Key) else key
    return getattr(code, "vk", None)


class HotkeyManager(QObject):
    triggered = Signal(str)  # nome da ação
    released = Signal(str)   # soltou a tecla principal da ação

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bindings: dict[str, tuple[frozenset, str]] = {}
        self._mods: set[str] = set()
        self._held: set[str] = set()
        self._active: dict[str, str] = {}  # tecla -> ação disparada (para o release)
        self.suspended = False
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()

    def set_bindings(self, hotkeys: dict[str, str]) -> None:
        bindings = {}
        for action, text in hotkeys.items():
            parsed = parse_combo(text)
            if parsed:
                bindings[action] = parsed
        self._bindings = bindings

    def set_suspended(self, value: bool) -> None:
        self.suspended = value
        self._mods.clear()
        self._held.clear()

    def _on_press(self, key) -> None:
        vk = _vk(key)
        mod = modifier_from_vk(vk)
        if mod:
            self._mods.add(mod)
            return
        name = vk_to_name(vk)
        if not name or name in self._held:  # ignora auto-repeat
            return
        self._held.add(name)
        if self.suspended:
            return
        for action, (mods, bound) in list(self._bindings.items()):
            if bound == name and mods == self._mods:
                self._active[name] = action
                self.triggered.emit(action)
                return

    def _on_release(self, key) -> None:
        vk = _vk(key)
        mod = modifier_from_vk(vk)
        if mod:
            self._mods.discard(mod)
            return
        name = vk_to_name(vk)
        if not name:
            return
        self._held.discard(name)
        action = self._active.pop(name, None)
        if action and not self.suspended:
            self.released.emit(action)
