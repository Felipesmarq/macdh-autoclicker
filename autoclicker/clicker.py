"""Motor de cliques: SendInput (ctypes) + temporização de alta precisão."""
from __future__ import annotations

import ctypes
import random
import threading
import time
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal

user32 = ctypes.windll.user32
winmm = ctypes.windll.winmm

INPUT_MOUSE = 0
_BUTTON_FLAGS = {
    "left": (0x0002, 0x0004),
    "right": (0x0008, 0x0010),
    "middle": (0x0020, 0x0040),
}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]


def _send(flag: int) -> None:
    event = INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, flag, 0, 0))
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))


def cursor_pos() -> tuple[int, int]:
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_timer_resolution(enable: bool) -> None:
    """Pede timer de 1 ms ao Windows (o padrão é ~15 ms)."""
    (winmm.timeBeginPeriod if enable else winmm.timeEndPeriod)(1)


class Clicker(QObject):
    finished = Signal(str)  # motivo: "stopped" | "done"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.count = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, settings: dict) -> bool:
        if self.running:
            return False
        self._stop.clear()
        self.count = 0
        self._thread = threading.Thread(target=self._run, args=(dict(settings),), daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    # -- interno --------------------------------------------------------
    def _wait_until(self, target: float) -> bool:
        """Dorme até `target` (perf_counter). False se pediram para parar."""
        while True:
            remaining = target - time.perf_counter()
            if remaining <= 0:
                return not self._stop.is_set()
            if remaining > 0.003:
                if self._stop.wait(min(remaining - 0.002, 0.05)):
                    return False
            elif self._stop.is_set():
                return False  # fase final: spin para precisão sub-ms

    def _run(self, s: dict) -> None:
        down, up = _BUTTON_FLAGS[s["button"]]
        interval = s["interval_ms"] / 1000
        jitter = s["jitter_ms"] / 1000
        hold = s["hold_ms"] / 1000
        limit = None if s["repeat_forever"] else s["repeat_count"]
        fixed = s["position_mode"] == "fixed"
        reason = "stopped"
        try:
            if s["start_delay_ms"] > 0:
                if not self._wait_until(time.perf_counter() + s["start_delay_ms"] / 1000):
                    return
            next_t = time.perf_counter()
            while not self._stop.is_set():
                if fixed:
                    user32.SetCursorPos(int(s["x"]), int(s["y"]))
                for _ in range(s["click_type"]):
                    _send(down)
                    if hold > 0 and not self._wait_until(time.perf_counter() + hold):
                        _send(up)
                        return
                    _send(up)
                self.count += 1
                if limit is not None and self.count >= limit:
                    reason = "done"
                    return
                delay = max(0.001, interval + random.uniform(-jitter, jitter))
                next_t = max(next_t + delay, time.perf_counter())
                if not self._wait_until(next_t):
                    return
        finally:
            self.finished.emit(reason)
