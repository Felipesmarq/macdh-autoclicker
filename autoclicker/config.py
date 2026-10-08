"""Configuração persistente (JSON em %APPDATA%) com perfis e hotkeys editáveis."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

DEFAULT_HOTKEYS = {
    "toggle": "f6",
    "start": "",
    "stop": "",
    "pick_position": "f7",
    "show_hide": "ctrl+shift+f6",
}

HOTKEY_LABELS = {
    "toggle": "Iniciar / Parar",
    "start": "Iniciar",
    "stop": "Parar",
    "pick_position": "Capturar posição do cursor",
    "show_hide": "Mostrar / Ocultar janela",
}

DEFAULT_CLICK = {
    "button": "left",           # left | right | middle
    "click_type": 1,            # 1 simples, 2 duplo, 3 triplo
    "hours": 0,
    "minutes": 0,
    "seconds": 0,
    "millis": 100,
    "jitter_ms": 0,             # variação aleatória +/- em ms
    "hold_ms": 0,               # tempo que o botão fica pressionado
    "mode": "toggle",           # toggle | hold (clica enquanto segura a hotkey)
    "repeat_forever": True,
    "repeat_count": 100,
    "position_mode": "cursor",  # cursor | fixed
    "x": 0,
    "y": 0,
    "start_delay_ms": 0,
    "game_cap_cps": 0,          # teto de CPS aceito pelo jogo (0 = sem teto conhecido)
}

# Perfis prontos (somente leitura). O Cookie Clicker descarta cliques com menos de 20 ms
# entre si (teto de 50 CPS); ~5 ms garante que o primeiro clique após os 20 ms sempre passe.
BUILTIN_PROFILES = {
    "★ Cookie Clicker (teto 50 CPS)": {
        "hours": 0, "minutes": 0, "seconds": 0, "millis": 5, "jitter_ms": 0, "hold_ms": 0,
        "click_type": 1, "button": "left", "mode": "toggle", "repeat_forever": True,
        "position_mode": "cursor", "start_delay_ms": 0, "game_cap_cps": 50,
    },
}

DEFAULT_APPEARANCE = {
    "theme": "dark",            # dark | light | amoled
    "accent": "#7c5cff",
    "always_on_top": False,
    "opacity": 100,
    "radius": 12,
}


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    path = Path(base) / "macdh-autoclicker"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Config:
    def __init__(self, path: Path | None = None):
        self.path = path or config_dir() / "config.json"
        self.data = {
            "click": copy.deepcopy(DEFAULT_CLICK),
            "hotkeys": copy.deepcopy(DEFAULT_HOTKEYS),
            "appearance": copy.deepcopy(DEFAULT_APPEARANCE),
            "profiles": {},
        }
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for section, defaults in (
            ("click", DEFAULT_CLICK),
            ("hotkeys", DEFAULT_HOTKEYS),
            ("appearance", DEFAULT_APPEARANCE),
        ):
            value = raw.get(section)
            if isinstance(value, dict):
                self.data[section].update({k: v for k, v in value.items() if k in defaults})
        profiles = raw.get("profiles")
        if isinstance(profiles, dict):
            self.data["profiles"] = profiles

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    @property
    def click(self) -> dict:
        return self.data["click"]

    @property
    def hotkeys(self) -> dict:
        return self.data["hotkeys"]

    @property
    def appearance(self) -> dict:
        return self.data["appearance"]

    @property
    def profiles(self) -> dict:
        return self.data["profiles"]

    def interval_ms(self) -> float:
        c = self.click
        total = (c["hours"] * 3600 + c["minutes"] * 60 + c["seconds"]) * 1000 + c["millis"]
        return max(1.0, float(total))
