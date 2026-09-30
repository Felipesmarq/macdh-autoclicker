from __future__ import annotations

import copy
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFrame, QGridLayout, QHBoxLayout,
    QInputDialog, QLabel, QListWidget, QMainWindow, QMenu, QMessageBox, QPushButton,
    QRadioButton, QScrollArea, QSlider, QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from .. import APP_NAME
from ..clicker import Clicker, cursor_pos
from ..config import DEFAULT_HOTKEYS, HOTKEY_LABELS, Config, config_dir
from ..hotkeys import HotkeyManager
from ..keys import pretty_combo
from .theme import ACCENT_PRESETS, build_qss, make_icon
from .widgets import Card, HotkeyEdit, make_spin, repolish


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    return label


def _page(title: str, subtitle: str = "") -> tuple[QScrollArea, QVBoxLayout]:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    body = QWidget()
    body.setObjectName("scrollBody")
    layout = QVBoxLayout(body)
    layout.setContentsMargins(4, 4, 14, 4)
    layout.setSpacing(14)
    head = QLabel(title)
    head.setObjectName("pageTitle")
    layout.addWidget(head)
    if subtitle:
        layout.addWidget(_muted(subtitle))
    area.setWidget(body)
    return area, layout


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config, clicker: Clicker, hotkeys: HotkeyManager):
        super().__init__()
        self.cfg, self.clicker, self.hotkeys = cfg, clicker, hotkeys
        self._loading = False
        self._quitting = False
        self._last_count, self._last_time = 0, time.perf_counter()
        self._pick_left = 0

        self.setWindowTitle(APP_NAME)
        self.resize(940, 720)
        self.setMinimumSize(860, 640)

        self._save_timer = QTimer(self, singleShot=True, interval=400)
        self._save_timer.timeout.connect(self.cfg.save)
        self._stats_timer = QTimer(self, interval=200)
        self._stats_timer.timeout.connect(self._update_stats)
        self._pick_timer = QTimer(self, interval=1000)
        self._pick_timer.timeout.connect(self._pick_tick)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(14)

        middle = QHBoxLayout()
        middle.setSpacing(16)
        outer.addLayout(middle, 1)
        middle.addWidget(self._build_sidebar())
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_clicker_page())
        self.stack.addWidget(self._build_hotkeys_page())
        self.stack.addWidget(self._build_appearance_page())
        middle.addWidget(self.stack, 1)
        outer.addWidget(self._build_bottom_bar())

        self._build_tray()
        self._load_click()
        self._refresh_profiles()
        self._apply_appearance()
        self._refresh_hotkey_labels()

        self.hotkeys.set_bindings(self.cfg.hotkeys)
        self.hotkeys.triggered.connect(self._on_hotkey)
        self.hotkeys.released.connect(self._on_hotkey_release)
        self.clicker.finished.connect(self._on_finished)
        self._stats_timer.start()

    # ------------------------------------------------------------------ layout
    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setFixedWidth(180)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        brand = QLabel("  MacDH")
        brand.setObjectName("brand")
        lay.addWidget(brand)
        lay.addWidget(_muted("  AutoClicker"))
        lay.addSpacing(10)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        for name in ("Clicker", "Atalhos", "Aparência"):
            self.nav.addItem(name)
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(lambda i: self.stack.setCurrentIndex(i))
        lay.addWidget(self.nav, 1)
        return side

    def _build_bottom_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("card")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 14, 16, 14)
        lay.setSpacing(24)
        self.lbl_status = QLabel("● Parado")
        self.lbl_status.setObjectName("status")
        self.lbl_count = QLabel("0")
        self.lbl_count.setObjectName("stat")
        self.lbl_cps = QLabel("0.0")
        self.lbl_cps.setObjectName("stat")
        lay.addWidget(self.lbl_status)
        for caption, value in (("Cliques", self.lbl_count), ("CPS", self.lbl_cps)):
            col = QVBoxLayout()
            col.setSpacing(0)
            col.addWidget(_muted(caption))
            col.addWidget(value)
            lay.addLayout(col)
        self.lbl_toast = _muted("")
        lay.addWidget(self.lbl_toast, 1)
        self.btn_main = QPushButton()
        self.btn_main.setObjectName("primary")
        self.btn_main.setCursor(Qt.PointingHandCursor)
        self.btn_main.clicked.connect(self.toggle_clicking)
        lay.addWidget(self.btn_main)
        return bar

    # ------------------------------------------------------------ página clicker
    def _build_clicker_page(self) -> QWidget:
        area, lay = _page("Clicker", "Configure como e quando os cliques acontecem. Tudo é salvo automaticamente.")

        # perfis
        prof = Card("Perfis")
        row = QHBoxLayout()
        self.cb_profiles = QComboBox()
        self.cb_profiles.setMinimumWidth(220)
        btn_load = QPushButton("Carregar")
        btn_save = QPushButton("Salvar atual como…")
        btn_del = QPushButton("Excluir")
        btn_load.clicked.connect(self._profile_load)
        btn_save.clicked.connect(self._profile_save)
        btn_del.clicked.connect(self._profile_delete)
        for w in (self.cb_profiles, btn_load, btn_save, btn_del):
            row.addWidget(w)
        row.addStretch(1)
        prof.body.addLayout(row)
        lay.addWidget(prof)

        # intervalo
        iv = Card("Intervalo entre cliques")
        row = QHBoxLayout()
        self.sp_h = make_spin(0, 99, " h", 70)
        self.sp_m = make_spin(0, 59, " min", 78)
        self.sp_s = make_spin(0, 59, " s", 70)
        self.sp_ms = make_spin(0, 999, " ms", 82)
        for w in (self.sp_h, self.sp_m, self.sp_s, self.sp_ms):
            row.addWidget(w)
        row.addStretch(1)
        iv.body.addLayout(row)
        row = QHBoxLayout()
        self.sp_jitter = make_spin(0, 60000, " ms", 90)
        self.sp_hold = make_spin(0, 60000, " ms", 90)
        row.addWidget(_muted("Variação aleatória ±"))
        row.addWidget(self.sp_jitter)
        row.addSpacing(16)
        row.addWidget(_muted("Botão pressionado por"))
        row.addWidget(self.sp_hold)
        row.addStretch(1)
        iv.body.addLayout(row)
        lay.addWidget(iv)

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # clique
        ck = Card("Clique")
        self.cb_button = QComboBox()
        for label, value in (("Esquerdo", "left"), ("Direito", "right"), ("Meio", "middle")):
            self.cb_button.addItem(label, value)
        self.cb_type = QComboBox()
        for label, value in (("Simples", 1), ("Duplo", 2), ("Triplo", 3)):
            self.cb_type.addItem(label, value)
        self.cb_mode = QComboBox()
        self.cb_mode.addItem("Alternar (aperta para ligar/desligar)", "toggle")
        self.cb_mode.addItem("Segurar (clica enquanto segura o atalho)", "hold")
        for caption, widget in (("Botão do mouse", self.cb_button), ("Tipo de clique", self.cb_type), ("Modo de ativação", self.cb_mode)):
            ck.body.addWidget(_muted(caption))
            ck.body.addWidget(widget)
        grid.addWidget(ck, 0, 0)

        # repetição
        rp = Card("Repetição")
        self.rb_forever = QRadioButton("Até eu parar")
        self.rb_count = QRadioButton("Repetir")
        rp.body.addWidget(self.rb_forever)
        row = QHBoxLayout()
        self.sp_count = make_spin(1, 10_000_000, "", 100)
        row.addWidget(self.rb_count)
        row.addWidget(self.sp_count)
        row.addWidget(_muted("vezes"))
        row.addStretch(1)
        rp.body.addLayout(row)
        rp.body.addSpacing(6)
        rp.body.addWidget(_muted("Atraso antes de começar"))
        row = QHBoxLayout()
        self.sp_delay = make_spin(0, 600000, " ms", 100)
        row.addWidget(self.sp_delay)
        row.addStretch(1)
        rp.body.addLayout(row)
        rp.body.addStretch(1)
        grid.addWidget(rp, 0, 1)
        lay.addLayout(grid)

        # posição
        ps = Card("Posição do clique")
        self.rb_cursor = QRadioButton("Onde o cursor estiver")
        self.rb_fixed = QRadioButton("Posição fixa")
        ps.body.addWidget(self.rb_cursor)
        row = QHBoxLayout()
        self.sp_x = make_spin(-32000, 32000, "", 80)
        self.sp_y = make_spin(-32000, 32000, "", 80)
        self.btn_pick = QPushButton("Capturar (3s)")
        self.btn_pick.clicked.connect(self._pick_begin)
        row.addWidget(self.rb_fixed)
        row.addWidget(_muted("X"))
        row.addWidget(self.sp_x)
        row.addWidget(_muted("Y"))
        row.addWidget(self.sp_y)
        row.addWidget(self.btn_pick)
        row.addStretch(1)
        ps.body.addLayout(row)
        self.lbl_pick_hint = _muted("")
        ps.body.addWidget(self.lbl_pick_hint)
        lay.addWidget(ps)
        lay.addStretch(1)

        for spin in (self.sp_h, self.sp_m, self.sp_s, self.sp_ms, self.sp_jitter, self.sp_hold,
                     self.sp_count, self.sp_delay, self.sp_x, self.sp_y):
            spin.valueChanged.connect(self._collect)
        for combo in (self.cb_button, self.cb_type, self.cb_mode):
            combo.currentIndexChanged.connect(self._collect)
        for radio in (self.rb_forever, self.rb_count, self.rb_cursor, self.rb_fixed):
            radio.toggled.connect(self._collect)
        return area

    # ------------------------------------------------------------- página atalhos
    def _build_hotkeys_page(self) -> QWidget:
        area, lay = _page("Atalhos", "Clique em um atalho e pressione a nova combinação. Esc cancela. Funcionam mesmo com o app em segundo plano.")
        card = Card("Atalhos globais")
        self.hk_edits: dict[str, HotkeyEdit] = {}
        for action, label in HOTKEY_LABELS.items():
            row = QHBoxLayout()
            name = QLabel(label)
            name.setMinimumWidth(210)
            edit = HotkeyEdit(self.cfg.hotkeys.get(action, ""))
            edit.changed.connect(lambda combo, a=action: self._hotkey_changed(a, combo))
            edit.capturing.connect(self.hotkeys.set_suspended)
            clear = QPushButton("Limpar")
            clear.clicked.connect(lambda _=False, a=action: self._hotkey_changed(a, ""))
            self.hk_edits[action] = edit
            row.addWidget(name)
            row.addWidget(edit)
            row.addWidget(clear)
            row.addStretch(1)
            card.body.addLayout(row)
        self.lbl_hk_msg = _muted("")
        card.body.addWidget(self.lbl_hk_msg)
        reset = QPushButton("Restaurar padrões")
        reset.clicked.connect(self._hotkeys_reset)
        row = QHBoxLayout()
        row.addWidget(reset)
        row.addStretch(1)
        card.body.addLayout(row)
        lay.addWidget(card)

        tips = Card("Dicas")
        tips.body.addWidget(_muted(
            "• No modo Segurar, o atalho de Iniciar/Parar clica só enquanto estiver pressionado.\n"
            "• Combine Ctrl, Shift e Alt com qualquer tecla (ex.: Ctrl + Shift + F6).\n"
            "• Para clicar em janelas de programas abertos como administrador, abra este app como administrador."))
        lay.addWidget(tips)
        lay.addStretch(1)
        return area

    # ----------------------------------------------------------- página aparência
    def _build_appearance_page(self) -> QWidget:
        area, lay = _page("Aparência", "Personalize o visual do app.")
        ap = self.cfg.appearance

        card = Card("Tema e cor")
        self.cb_theme = QComboBox()
        for label, value in (("Escuro", "dark"), ("Claro", "light"), ("AMOLED (preto)", "amoled")):
            self.cb_theme.addItem(label, value)
        self.cb_theme.setCurrentIndex(max(0, self.cb_theme.findData(ap["theme"])))
        self.cb_theme.currentIndexChanged.connect(self._appearance_changed)
        card.body.addWidget(_muted("Tema"))
        card.body.addWidget(self.cb_theme)
        card.body.addWidget(_muted("Cor de destaque"))
        row = QHBoxLayout()
        self.swatches: list[QPushButton] = []
        for color in ACCENT_PRESETS:
            btn = QPushButton()
            btn.setObjectName("swatch")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("color", color)
            btn.setStyleSheet(f"QPushButton#swatch {{ background: {color}; }}")
            btn.clicked.connect(lambda _=False, c=color: self._set_accent(c))
            self.swatches.append(btn)
            row.addWidget(btn)
        custom = QPushButton("Personalizada…")
        custom.clicked.connect(self._pick_custom_accent)
        row.addWidget(custom)
        row.addStretch(1)
        card.body.addLayout(row)
        lay.addWidget(card)

        win = Card("Janela")
        self.ck_top = QCheckBox("Manter sempre por cima das outras janelas")
        self.ck_top.setChecked(ap["always_on_top"])
        self.ck_top.toggled.connect(self._appearance_changed)
        win.body.addWidget(self.ck_top)
        self.sl_opacity, self.lbl_opacity = self._slider(win, "Opacidade", 40, 100, ap["opacity"], "%")
        self.sl_radius, self.lbl_radius = self._slider(win, "Arredondamento dos cantos", 0, 24, ap["radius"], " px")
        lay.addWidget(win)
        lay.addStretch(1)
        return area

    def _slider(self, card: Card, caption: str, lo: int, hi: int, value: int, suffix: str):
        row = QHBoxLayout()
        title = QLabel(caption)
        title.setMinimumWidth(190)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(lo, hi)
        slider.setValue(value)
        label = _muted(f"{value}{suffix}")
        label.setMinimumWidth(50)
        slider.valueChanged.connect(lambda v: label.setText(f"{v}{suffix}"))
        slider.valueChanged.connect(self._appearance_changed)
        row.addWidget(title)
        row.addWidget(slider, 1)
        row.addWidget(label)
        card.body.addLayout(row)
        return slider, label

    # ------------------------------------------------------------------- bandeja
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        act_show = QAction("Mostrar / Ocultar", self)
        act_show.triggered.connect(self.toggle_visible)
        act_toggle = QAction("Iniciar / Parar", self)
        act_toggle.triggered.connect(self.toggle_clicking)
        act_quit = QAction("Sair", self)
        act_quit.triggered.connect(self._quit)
        for a in (act_show, act_toggle):
            menu.addAction(a)
        menu.addSeparator()
        menu.addAction(act_quit)
        self._tray_menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.toggle_visible() if reason == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def toggle_visible(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _quit(self) -> None:
        self._quitting = True
        self.close()

    # ------------------------------------------------------- config <-> widgets
    def _load_click(self) -> None:
        c = self.cfg.click
        self._loading = True
        try:
            self.sp_h.setValue(c["hours"])
            self.sp_m.setValue(c["minutes"])
            self.sp_s.setValue(c["seconds"])
            self.sp_ms.setValue(c["millis"])
            self.sp_jitter.setValue(c["jitter_ms"])
            self.sp_hold.setValue(c["hold_ms"])
            self.cb_button.setCurrentIndex(max(0, self.cb_button.findData(c["button"])))
            self.cb_type.setCurrentIndex(max(0, self.cb_type.findData(c["click_type"])))
            self.cb_mode.setCurrentIndex(max(0, self.cb_mode.findData(c["mode"])))
            self.rb_forever.setChecked(c["repeat_forever"])
            self.rb_count.setChecked(not c["repeat_forever"])
            self.sp_count.setValue(c["repeat_count"])
            self.rb_fixed.setChecked(c["position_mode"] == "fixed")
            self.rb_cursor.setChecked(c["position_mode"] != "fixed")
            self.sp_x.setValue(c["x"])
            self.sp_y.setValue(c["y"])
            self.sp_delay.setValue(c["start_delay_ms"])
        finally:
            self._loading = False
        self._sync_enabled()

    def _sync_enabled(self) -> None:
        self.sp_count.setEnabled(self.rb_count.isChecked())
        fixed = self.rb_fixed.isChecked()
        for w in (self.sp_x, self.sp_y, self.btn_pick):
            w.setEnabled(fixed)

    def _collect(self, *_) -> None:
        if self._loading:
            return
        self.cfg.click.update(
            hours=self.sp_h.value(), minutes=self.sp_m.value(), seconds=self.sp_s.value(),
            millis=self.sp_ms.value(), jitter_ms=self.sp_jitter.value(), hold_ms=self.sp_hold.value(),
            button=self.cb_button.currentData(), click_type=self.cb_type.currentData(),
            mode=self.cb_mode.currentData(), repeat_forever=self.rb_forever.isChecked(),
            repeat_count=self.sp_count.value(),
            position_mode="fixed" if self.rb_fixed.isChecked() else "cursor",
            x=self.sp_x.value(), y=self.sp_y.value(), start_delay_ms=self.sp_delay.value(),
        )
        self._sync_enabled()
        self._save_timer.start()

    # ------------------------------------------------------------------- perfis
    def _refresh_profiles(self, select: str | None = None) -> None:
        self.cb_profiles.clear()
        self.cb_profiles.addItems(sorted(self.cfg.profiles))
        if select:
            self.cb_profiles.setCurrentText(select)

    def _profile_save(self) -> None:
        name, ok = QInputDialog.getText(self, "Salvar perfil", "Nome do perfil:", text=self.cb_profiles.currentText())
        name = name.strip()
        if not ok or not name:
            return
        self._collect()
        self.cfg.profiles[name] = copy.deepcopy(self.cfg.click)
        self.cfg.save()
        self._refresh_profiles(name)
        self._toast(f"Perfil “{name}” salvo")

    def _profile_load(self) -> None:
        name = self.cb_profiles.currentText()
        profile = self.cfg.profiles.get(name)
        if not profile:
            return
        self.cfg.click.update({k: v for k, v in profile.items() if k in self.cfg.click})
        self._load_click()
        self._collect()
        self._toast(f"Perfil “{name}” carregado")

    def _profile_delete(self) -> None:
        name = self.cb_profiles.currentText()
        if name in self.cfg.profiles and QMessageBox.question(
            self, "Excluir perfil", f"Excluir o perfil “{name}”?") == QMessageBox.Yes:
            del self.cfg.profiles[name]
            self.cfg.save()
            self._refresh_profiles()

    # ------------------------------------------------------------------ atalhos
    def _hotkey_changed(self, action: str, combo: str) -> None:
        edit = self.hk_edits[action]
        if combo:
            for other, existing in self.cfg.hotkeys.items():
                if other != action and existing == combo:
                    edit.set_combo(self.cfg.hotkeys[action])
                    self.lbl_hk_msg.setText(f"⚠ {pretty_combo(combo)} já é usado por “{HOTKEY_LABELS[other]}”.")
                    return
        self.lbl_hk_msg.setText("")
        self.cfg.hotkeys[action] = combo
        edit.set_combo(combo)
        self.hotkeys.set_bindings(self.cfg.hotkeys)
        self._refresh_hotkey_labels()
        self._save_timer.start()

    def _hotkeys_reset(self) -> None:
        self.cfg.hotkeys.update(DEFAULT_HOTKEYS)
        for action, edit in self.hk_edits.items():
            edit.set_combo(self.cfg.hotkeys[action])
        self.lbl_hk_msg.setText("")
        self.hotkeys.set_bindings(self.cfg.hotkeys)
        self._refresh_hotkey_labels()
        self._save_timer.start()

    def _refresh_hotkey_labels(self) -> None:
        self._update_main_button()

    def _on_hotkey(self, action: str) -> None:
        if action == "toggle":
            if self.cfg.click["mode"] == "hold":
                self.start_clicking()
            else:
                self.toggle_clicking()
        elif action == "start":
            self.start_clicking()
        elif action == "stop":
            self.clicker.stop()
        elif action == "pick_position":
            self._capture_now()
        elif action == "show_hide":
            self.toggle_visible()

    def _on_hotkey_release(self, action: str) -> None:
        if action == "toggle" and self.cfg.click["mode"] == "hold":
            self.clicker.stop()

    # ------------------------------------------------------------ clicar / parar
    def start_clicking(self) -> None:
        if self.clicker.running:
            return
        self._collect()
        settings = dict(self.cfg.click)
        settings["interval_ms"] = self.cfg.interval_ms()
        if self.clicker.start(settings):
            self._last_count, self._last_time = 0, time.perf_counter()
            self._set_running(True)

    def toggle_clicking(self) -> None:
        if self.clicker.running:
            self.clicker.stop()
        else:
            self.start_clicking()

    def _on_finished(self, reason: str) -> None:
        self._set_running(False)
        self._update_stats()
        if reason == "done":
            self._toast("Concluído: repetições finalizadas")

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.btn_main.setProperty("running", running)
        repolish(self.btn_main)
        color = "#e5484d" if running else "#8a8aa0"
        self.lbl_status.setStyleSheet(f"color: {color};")
        self.lbl_status.setText("● Clicando…" if running else "● Parado")
        self._update_main_button()

    def _update_main_button(self) -> None:
        running = bool(self.btn_main.property("running"))
        if running:
            self.btn_main.setText("Parar")
        else:
            hk = pretty_combo(self.cfg.hotkeys.get("toggle") or self.cfg.hotkeys.get("start", ""))
            self.btn_main.setText(f"Iniciar  ({hk})" if hk else "Iniciar")

    def _update_stats(self) -> None:
        now = time.perf_counter()
        count = self.clicker.count
        dt = now - self._last_time
        cps = (count - self._last_count) / dt * self.cfg.click["click_type"] if self.clicker.running and dt > 0 else 0.0
        self._last_count, self._last_time = count, now
        self.lbl_count.setText(f"{count:,}".replace(",", "."))
        self.lbl_cps.setText(f"{cps:.1f}")

    def _toast(self, text: str, ms: int = 3500) -> None:
        self.lbl_toast.setText(text)
        QTimer.singleShot(ms, lambda: self.lbl_toast.setText("") if self.lbl_toast.text() == text else None)

    # ------------------------------------------------------- captura de posição
    def _capture_now(self) -> None:
        x, y = cursor_pos()
        self.sp_x.setValue(x)
        self.sp_y.setValue(y)
        self.rb_fixed.setChecked(True)
        self._toast(f"Posição capturada: {x}, {y}")

    def _pick_begin(self) -> None:
        self._pick_left = 3
        self.btn_pick.setEnabled(False)
        self.btn_pick.setText("Mova o mouse… 3")
        self._pick_timer.start()

    def _pick_tick(self) -> None:
        self._pick_left -= 1
        if self._pick_left > 0:
            self.btn_pick.setText(f"Mova o mouse… {self._pick_left}")
            return
        self._pick_timer.stop()
        self.btn_pick.setText("Capturar (3s)")
        self.btn_pick.setEnabled(self.rb_fixed.isChecked())
        self._capture_now()

    # ----------------------------------------------------------------- aparência
    def _set_accent(self, color: str) -> None:
        self.cfg.appearance["accent"] = color
        self._apply_appearance()
        self._save_timer.start()

    def _pick_custom_accent(self) -> None:
        color = QColorDialog.getColor(QColor(self.cfg.appearance["accent"]), self, "Cor de destaque")
        if color.isValid():
            self._set_accent(color.name())

    def _appearance_changed(self, *_) -> None:
        ap = self.cfg.appearance
        ap["theme"] = self.cb_theme.currentData()
        ap["always_on_top"] = self.ck_top.isChecked()
        ap["opacity"] = self.sl_opacity.value()
        ap["radius"] = self.sl_radius.value()
        self._apply_appearance()
        self._save_timer.start()

    def _apply_appearance(self) -> None:
        ap = self.cfg.appearance
        QApplication.instance().setStyleSheet(build_qss(ap, config_dir() / "assets"))
        icon = make_icon(ap["accent"])
        self.setWindowIcon(icon)
        self.tray.setIcon(icon)
        QApplication.instance().setWindowIcon(icon)
        self.setWindowOpacity(ap["opacity"] / 100)
        if bool(self.windowFlags() & Qt.WindowStaysOnTopHint) != ap["always_on_top"]:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, ap["always_on_top"])
            self.show()
        for btn in self.swatches:
            btn.setProperty("selected", btn.property("color").lower() == ap["accent"].lower())
            repolish(btn)

    # ------------------------------------------------------------------ encerrar
    def closeEvent(self, event) -> None:
        self.clicker.stop()
        self._save_timer.stop()
        self._collect()
        self.cfg.save()
        self.hotkeys.stop()
        self.tray.hide()
        event.accept()
        QApplication.instance().quit()
