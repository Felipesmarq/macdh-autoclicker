"""Motor de cliques: SendInput (ctypes) + temporização de alta precisão."""
from __future__ import annotations

import ctypes
import random
import threading
import time
from ctypes import wintypes

from PySide6.QtCore import QObject, Signal

user32 = ctypes.windll.user32
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
winmm = ctypes.windll.winmm

kernel32.GetCurrentProcess.restype = ctypes.c_void_p
kernel32.GetCurrentThread.restype = ctypes.c_void_p
kernel32.SetPriorityClass.argtypes = [ctypes.c_void_p, wintypes.DWORD]
kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
kernel32.SetProcessInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
kernel32.SetThreadInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]

INPUT_MOUSE = 0
_BUTTON_FLAGS = {
    "left": (0x0002, 0x0004),
    "right": (0x0008, 0x0010),
    "middle": (0x0020, 0x0040),
}

HIGH_PRIORITY_CLASS = 0x00000080
THREAD_PRIORITY_TIME_CRITICAL = 15
PROCESS_POWER_THROTTLING = 4   # PROCESS_INFORMATION_CLASS
THREAD_POWER_THROTTLING = 1    # THREAD_INFORMATION_CLASS
THROTTLE_EXECUTION_SPEED = 0x1
THROTTLE_IGNORE_TIMER_RESOLUTION = 0x4

# Preenchido por optimize_process(); lido pela aba Diagnóstico.
OPT_STATUS: dict[str, bool] = {"timer_1ms": False, "priority_high": False, "throttle_off": False}


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


class _PowerThrottling(ctypes.Structure):
    _fields_ = [("Version", wintypes.ULONG), ("ControlMask", wintypes.ULONG), ("StateMask", wintypes.ULONG)]


def _send(flag: int) -> None:
    event = INPUT(INPUT_MOUSE, MOUSEINPUT(0, 0, 0, flag, 0, 0))
    user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))


def cursor_pos() -> tuple[int, int]:
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _no_throttle_state() -> _PowerThrottling:
    # ControlMask liga o controle; StateMask=0 significa "não limitar" (desliga o throttling).
    return _PowerThrottling(1, THROTTLE_EXECUTION_SPEED | THROTTLE_IGNORE_TIMER_RESOLUTION, 0)


def optimize_process() -> dict[str, bool]:
    """Evita que o Windows 11 desacelere o app quando o jogo está em primeiro plano.

    Sem isso, um processo em segundo plano pode ter o timer de 1 ms ignorado (voltando
    para ~15 ms) e ser jogado em núcleos de eficiência (EcoQoS).
    """
    winmm.timeBeginPeriod(1)
    OPT_STATUS["timer_1ms"] = True
    OPT_STATUS["priority_high"] = bool(kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), HIGH_PRIORITY_CLASS))
    state = _no_throttle_state()
    OPT_STATUS["throttle_off"] = bool(
        kernel32.SetProcessInformation(kernel32.GetCurrentProcess(), PROCESS_POWER_THROTTLING,
                                       ctypes.byref(state), ctypes.sizeof(state)))
    return OPT_STATUS


def release_process() -> None:
    winmm.timeEndPeriod(1)


def _optimize_current_thread() -> None:
    kernel32.SetThreadPriority(kernel32.GetCurrentThread(), THREAD_PRIORITY_TIME_CRITICAL)
    state = _no_throttle_state()
    kernel32.SetThreadInformation(kernel32.GetCurrentThread(), THREAD_POWER_THROTTLING,
                                  ctypes.byref(state), ctypes.sizeof(state))


class Clicker(QObject):
    finished = Signal(str)  # motivo: "stopped" | "done"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.count = 0
        self._reset_stats()

    def _reset_stats(self) -> None:
        self.t_start: float | None = None
        self.t_end: float | None = None
        self.late_n = 0
        self.late_sum = 0.0
        self.late_max = 0.0
        self.late_over = 0  # esperas que terminaram > 1 ms depois do previsto

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def snapshot(self) -> dict:
        """Medições do último/atual disparo (lidas pela UI; valores aproximados, sem lock)."""
        if self.t_start is None:
            return {"elapsed": 0.0, "cps": 0.0, "late_avg_ms": 0.0, "late_max_ms": 0.0, "late_pct": 0.0}
        end = self.t_end if self.t_end is not None else time.perf_counter()
        elapsed = max(end - self.t_start, 1e-9)
        n = max(self.late_n, 1)
        return {
            "elapsed": elapsed,
            "cps": self.count / elapsed,
            "late_avg_ms": self.late_sum / n * 1000,
            "late_max_ms": self.late_max * 1000,
            "late_pct": self.late_over / n * 100,
        }

    def start(self, settings: dict) -> bool:
        if self.running:
            return False
        self._stop.clear()
        self.count = 0
        self._reset_stats()
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
        _optimize_current_thread()
        down, up = _BUTTON_FLAGS[s["button"]]
        interval = s["interval_ms"] / 1000
        jitter = s["jitter_ms"] / 1000
        hold = s["hold_ms"] / 1000
        limit = None if s["repeat_forever"] else s["repeat_count"]
        fixed = s["position_mode"] == "fixed"
        perf = time.perf_counter
        reason = "stopped"
        try:
            if s["start_delay_ms"] > 0:
                if not self._wait_until(perf() + s["start_delay_ms"] / 1000):
                    return
            self.t_start = next_t = perf()
            while not self._stop.is_set():
                if fixed:
                    user32.SetCursorPos(int(s["x"]), int(s["y"]))
                for _ in range(s["click_type"]):
                    _send(down)
                    if hold > 0 and not self._wait_until(perf() + hold):
                        _send(up)
                        return
                    _send(up)
                self.count += 1
                if limit is not None and self.count >= limit:
                    reason = "done"
                    return
                delay = max(0.001, interval + random.uniform(-jitter, jitter))
                target = next_t + delay
                if perf() >= target:  # já atrasado: não espera, só registra o atraso
                    next_t = perf()
                    late = next_t - target
                else:
                    next_t = target
                    if not self._wait_until(next_t):
                        return
                    late = perf() - next_t
                self.late_n += 1
                self.late_sum += late
                if late > self.late_max:
                    self.late_max = late
                if late > 0.001:
                    self.late_over += 1
        finally:
            self.t_end = perf()
            self.finished.emit(reason)
