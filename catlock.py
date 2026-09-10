#!/usr/bin/env python3
"""
CatLock GUI - Bloqueador de Teclado e Mouse para Wayland / KDE Plasma
Cria uma tela cheia elegante que captura todas as entradas do teclado e mouse.
Atalho exclusivo para destravar: Super + Del (ou Command + Del)
Suporta múltiplos idiomas: Português e Inglês (com alternância fácil).
"""

import os
import sys
import json
import signal
import atexit
import argparse
from pathlib import Path
import dbus
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)

PID_FILE = "/tmp/catlock.pid"
CONFIG_DIR = Path.home() / ".config" / "catlock"
CONFIG_FILE = CONFIG_DIR / "config.json"

TRANSLATIONS = {
    "pt": {
        "status": "● PROTEÇÃO ATIVADA",
        "description": "O teclado e o mouse estão protegidos contra gatos e toques acidentais. Nenhum programa receberá comandos.",
        "unlock_title": "Para desbloquear e voltar:",
        "super_key": "Super / Command",
        "del_key": "Del",
        "feedback_blocked": "Entrada bloqueada",
        "feedback_mouse": "Clique do mouse bloqueado",
        "feedback_double_click": "Clique duplo bloqueado",
        "sec_label": "🐱 CatLock Ativo\n(Pressione Super + Del na tela principal)",
        "switch_lang_text": "🌐 English",
    },
    "en": {
        "status": "● PROTECTION ACTIVE",
        "description": "Keyboard and mouse are protected against cats and accidental touches. No program will receive input.",
        "unlock_title": "To unlock and return:",
        "super_key": "Super / Command",
        "del_key": "Del",
        "feedback_blocked": "Input blocked",
        "feedback_mouse": "Mouse click blocked",
        "feedback_double_click": "Double-click blocked",
        "sec_label": "🐱 CatLock Active\n(Press Super + Del on main screen)",
        "switch_lang_text": "🌐 Português",
    }
}


def load_language_preference(cli_arg=None):
    """Carrega o idioma preferido a partir de CLI, config.json ou locale do sistema."""
    if cli_arg in ("pt", "en"):
        return cli_arg
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("language") in ("pt", "en"):
                    return data["language"]
        except Exception:
            pass
    sys_lang = os.environ.get("LANG", "").lower()
    if sys_lang.startswith("pt"):
        return "pt"
    return "en"


def save_language_preference(lang):
    """Salva a preferência de idioma em ~/.config/catlock/config.json."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"language": lang}, f, indent=2)
    except Exception as e:
        print(f"Erro ao salvar configuração de idioma: {e}", file=sys.stderr)


def set_global_shortcuts_blocked(blocked: bool):
    """Ativa ou desativa o bloqueio de atalhos globais do KWin via D-Bus."""
    try:
        bus = dbus.SessionBus()
        obj = bus.get_object("org.kde.kglobalaccel", "/kglobalaccel")
        iface = dbus.Interface(obj, "org.kde.KGlobalAccel")
        iface.blockGlobalShortcuts(blocked)
    except Exception as e:
        print(f"[Aviso] Não foi possível alterar blockGlobalShortcuts: {e}", file=sys.stderr)


atexit.register(lambda: set_global_shortcuts_blocked(False))


class CatLockOverlay(QWidget):
    """Janela de sobreposição em tela cheia que absorve todos os inputs."""

    all_instances = []

    def __init__(self, is_primary=True, lang="pt"):
        super().__init__()
        self.is_primary = is_primary
        self.lang = lang
        self.unlocked = False
        CatLockOverlay.all_instances.append(self)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if not self.is_primary:
            # Tela secundária
            bg_frame = QFrame(self)
            bg_frame.setObjectName("secBgFrame")
            bg_frame.setStyleSheet("""
                QFrame#secBgFrame {
                    background-color: rgba(13, 17, 23, 0.95);
                    border: 2px solid rgba(88, 166, 255, 0.25);
                    border-radius: 28px;
                }
            """)
            frame_layout = QVBoxLayout(bg_frame)
            frame_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sec_label = QLabel(TRANSLATIONS[self.lang]["sec_label"], bg_frame)
            self.sec_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sec_label.setStyleSheet("font-size: 24px; color: #8b949e; font-weight: bold; border: none; background: transparent;")
            frame_layout.addWidget(self.sec_label)
            main_layout.addWidget(bg_frame)
            return

        # Fundo escuro com bordas arredondadas na tela inteira
        self.bg_frame = QFrame(self)
        self.bg_frame.setObjectName("mainBgFrame")
        self.bg_frame.setStyleSheet("""
            QFrame#mainBgFrame {
                background-color: rgba(13, 17, 23, 0.96);
                border: 2px solid rgba(88, 166, 255, 0.35);
                border-radius: 28px;
            }
        """)
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Card central
        card = QFrame(self.bg_frame)
        card.setObjectName("centralCard")
        card.setFixedWidth(490)
        card.setStyleSheet("""
            QFrame#centralCard {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 20px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 24, 32, 28)
        card_layout.setSpacing(14)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Barra superior com botão de alternância de idioma
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch()

        self.lang_btn = QPushButton(TRANSLATIONS[self.lang]["switch_lang_text"], card)
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #f0f6fc;
                border-color: #8b949e;
            }
        """)
        self.lang_btn.clicked.connect(self.on_lang_button_clicked)
        top_bar.addWidget(self.lang_btn)
        card_layout.addLayout(top_bar)

        # Ícone do Gato
        cat_icon = QLabel("🐱", card)
        cat_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cat_icon.setStyleSheet("font-size: 70px; border: none; background: transparent;")
        card_layout.addWidget(cat_icon)

        # Título
        title = QLabel("CatLock", card)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 800;
            color: #f0f6fc;
            border: none;
            background: transparent;
            letter-spacing: 1px;
        """)
        card_layout.addWidget(title)

        # Badge de status
        self.badge = QLabel(TRANSLATIONS[self.lang]["status"], card)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet("""
            font-size: 13px;
            font-weight: 700;
            color: #3fb950;
            background-color: rgba(63, 185, 80, 0.12);
            border: 1px solid rgba(63, 185, 80, 0.3);
            border-radius: 12px;
            padding: 4px 14px;
            letter-spacing: 1.5px;
        """)
        card_layout.addWidget(self.badge)

        # Descrição
        self.desc = QLabel(TRANSLATIONS[self.lang]["description"], card)
        self.desc.setWordWrap(True)
        self.desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc.setStyleSheet("""
            font-size: 13.5px;
            color: #8b949e;
            border: none;
            background: transparent;
            line-height: 1.5;
        """)
        card_layout.addWidget(self.desc)

        # Divisor
        divider = QFrame(card)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("border-top: 1px solid #21262d; border-bottom: none; background: transparent;")
        card_layout.addWidget(divider)

        # Instruções de desbloqueio
        unlock_box = QFrame(card)
        unlock_box.setStyleSheet("""
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 12px 16px;
        """)
        unlock_layout = QVBoxLayout(unlock_box)
        unlock_layout.setSpacing(6)
        unlock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.unlock_title = QLabel(TRANSLATIONS[self.lang]["unlock_title"], unlock_box)
        self.unlock_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.unlock_title.setStyleSheet("font-size: 12px; color: #8b949e; border: none; background: transparent;")
        unlock_layout.addWidget(self.unlock_title)

        keys_row = QHBoxLayout()
        keys_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        keys_row.setSpacing(10)

        def make_key_tag(text):
            lbl = QLabel(text, unlock_box)
            lbl.setStyleSheet("""
                background-color: #21262d;
                color: #e6edf3;
                border: 1px solid #484f58;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 14px;
                font-weight: bold;
            """)
            return lbl

        self.super_tag = make_key_tag(TRANSLATIONS[self.lang]["super_key"])
        keys_row.addWidget(self.super_tag)

        plus = QLabel("+", unlock_box)
        plus.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 16px; border: none; background: transparent;")
        keys_row.addWidget(plus)

        self.del_tag = make_key_tag(TRANSLATIONS[self.lang]["del_key"])
        keys_row.addWidget(self.del_tag)

        unlock_layout.addLayout(keys_row)
        card_layout.addWidget(unlock_box)

        # Feedback interativo de pata
        self.feedback_label = QLabel("", card)
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.setStyleSheet("""
            color: #a371f7;
            font-size: 13px;
            font-weight: 600;
            border: none;
            background: transparent;
            min-height: 20px;
        """)
        card_layout.addWidget(self.feedback_label)

        bg_layout.addWidget(card)
        main_layout.addWidget(self.bg_frame)

        self.feedback_timer = QTimer(self)
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(self.clear_feedback)

    def on_lang_button_clicked(self):
        new_lang = "en" if self.lang == "pt" else "pt"
        save_language_preference(new_lang)
        for inst in CatLockOverlay.all_instances:
            inst.set_language(new_lang)

    def set_language(self, lang):
        self.lang = lang
        t = TRANSLATIONS[lang]
        if self.is_primary:
            self.badge.setText(t["status"])
            self.desc.setText(t["description"])
            self.unlock_title.setText(t["unlock_title"])
            self.super_tag.setText(t["super_key"])
            self.del_tag.setText(t["del_key"])
            self.lang_btn.setText(t["switch_lang_text"])
        else:
            if hasattr(self, "sec_label"):
                self.sec_label.setText(t["sec_label"])

    def show_feedback(self, text):
        if hasattr(self, "feedback_label"):
            self.feedback_label.setText(f"🐾 {text}")
            self.feedback_timer.start(1200)

    def clear_feedback(self):
        if hasattr(self, "feedback_label"):
            self.feedback_label.setText("")

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()
        is_meta = bool(modifiers & Qt.KeyboardModifier.MetaModifier)

        # Atalho de desbloqueio exclusivo: Super + Del (ou Super + Backspace)
        if is_meta and key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            print("[CatLock] Atalho de desbloqueio detectado (Super + Del)! Encerrando...")
            self.unlock_and_close()
            return

        key_name = event.text().strip() or f"key {key}"
        prefix = TRANSLATIONS[self.lang]["feedback_blocked"]
        self.show_feedback(f"{prefix} ({key_name})")
        event.accept()

    def keyReleaseEvent(self, event):
        event.accept()

    def mousePressEvent(self, event):
        self.show_feedback(TRANSLATIONS[self.lang]["feedback_mouse"])
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.show_feedback(TRANSLATIONS[self.lang]["feedback_double_click"])
        event.accept()

    def wheelEvent(self, event):
        event.accept()

    def contextMenuEvent(self, event):
        event.accept()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                self.activateWindow()
                self.raise_()
        super().changeEvent(event)

    def closeEvent(self, event):
        if not self.unlocked:
            event.ignore()
        else:
            event.accept()

    def unlock_and_close(self):
        self.unlocked = True
        set_global_shortcuts_blocked(False)
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
        QApplication.quit()


def main():
    parser = argparse.ArgumentParser(description="CatLock - Keyboard & Mouse locker for Wayland")
    parser.add_argument("--lang", choices=["pt", "en"], help="Define o idioma inicial (pt ou en)")
    args, unknown = parser.parse_known_args()

    # Verifica toggle
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, signal.SIGTERM)
            print(f"[CatLock] Instância já rodando (PID {old_pid}). Sinal enviado para fechar.")
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    initial_lang = load_language_preference(args.lang)

    app = QApplication(sys.argv)
    app.setApplicationName("CatLock")

    set_global_shortcuts_blocked(True)

    screens = QGuiApplication.screens()
    windows = []
    for i, screen in enumerate(screens):
        win = CatLockOverlay(is_primary=(i == 0), lang=initial_lang)
        win.setGeometry(screen.geometry())
        win.showFullScreen()
        windows.append(win)

    signal_timer = QTimer()
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(200)

    def sig_handler(sig, frame):
        set_global_shortcuts_blocked(False)
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass
        QApplication.quit()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    if windows:
        windows[0].activateWindow()
        windows[0].raise_()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
