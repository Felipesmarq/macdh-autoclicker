"""Nomes de teclas baseados em virtual-key codes do Windows.

Usado tanto pelo listener global (pynput) quanto pelo campo de captura da UI,
garantindo que os dois falem o mesmo idioma ("ctrl+shift+f6").
"""
from __future__ import annotations

MODIFIER_ORDER = ("ctrl", "shift", "alt", "meta")

_MOD_VK = {
    0x10: "shift", 0xA0: "shift", 0xA1: "shift",
    0x11: "ctrl", 0xA2: "ctrl", 0xA3: "ctrl",
    0x12: "alt", 0xA4: "alt", 0xA5: "alt",
    0x5B: "meta", 0x5C: "meta",
}

_SPECIAL_VK = {
    0x08: "backspace", 0x09: "tab", 0x0D: "enter", 0x13: "pause", 0x14: "capslock",
    0x1B: "esc", 0x20: "space", 0x21: "pageup", 0x22: "pagedown", 0x23: "end",
    0x24: "home", 0x25: "left", 0x26: "up", 0x27: "right", 0x28: "down",
    0x2C: "printscreen", 0x2D: "insert", 0x2E: "delete", 0x90: "numlock", 0x91: "scrolllock",
    0x6A: "num*", 0x6B: "num+", 0x6D: "num-", 0x6E: "num.", 0x6F: "num/",
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/",
    0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
}


def modifier_from_vk(vk: int | None) -> str | None:
    return _MOD_VK.get(vk) if vk is not None else None


def vk_to_name(vk: int | None) -> str | None:
    """Nome normalizado da tecla (não-modificadora) ou None se desconhecida."""
    if vk is None:
        return None
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk).lower()
    if 0x60 <= vk <= 0x69:
        return f"num{vk - 0x60}"
    if 0x70 <= vk <= 0x87:
        return f"f{vk - 0x6F}"
    return _SPECIAL_VK.get(vk)


def build_combo(mods, key: str) -> str:
    ordered = [m for m in MODIFIER_ORDER if m in mods]
    return "+".join([*ordered, key])


def parse_combo(text: str):
    """'ctrl+f6' -> (frozenset({'ctrl'}), 'f6'); vazio/inválido -> None."""
    text = (text or "").strip().lower()
    if not text:
        return None
    parts = text.split("+") if not text.endswith("++") else [*text[:-2].split("+"), "+"]
    parts = [p for p in parts if p]
    if not parts:
        return None
    key = parts[-1]
    mods = frozenset(parts[:-1])
    if key in MODIFIER_ORDER or not mods <= set(MODIFIER_ORDER):
        return None
    return mods, key


_PRETTY = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "meta": "Win",
           "esc": "Esc", "pageup": "PgUp", "pagedown": "PgDn", "printscreen": "PrtSc",
           "capslock": "Caps", "numlock": "NumLk", "scrolllock": "ScrLk"}


def pretty_combo(text: str) -> str:
    parsed = parse_combo(text)
    if not parsed:
        return ""
    mods, key = parsed
    names = [_PRETTY[m] for m in MODIFIER_ORDER if m in mods]
    names.append(_PRETTY.get(key, key.upper() if len(key) <= 3 else key.capitalize()))
    return " + ".join(names)
