import threading
import webbrowser

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QCursor

from config import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    GITHUB_URL,
    TELEGRAM_URL,
    DISCORD_NAME,
)
from utils import s
from styles import Style


class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent_window = parent
        self.drag_pos = None

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)

        self.setStyleSheet(Style.main(parent.settings.app_scale))
        self.setFixedSize(
            s(450, parent.settings.app_scale),
            s(390, parent.settings.app_scale),
        )

        self.build()

    def build(self):
        sc = self.parent_window.settings.app_scale

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)

        layout = QVBoxLayout(shell)
        layout.setContentsMargins(
            s(22, sc),
            s(18, sc),
            s(22, sc),
            s(20, sc),
        )
        layout.setSpacing(s(12, sc))

        top = QHBoxLayout()

        title = QLabel("О программе")
        title.setObjectName("SectionTitle")

        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.clicked.connect(self.close)

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)

        layout.addLayout(top)

        name = QLabel(APP_NAME)
        name.setObjectName("SectionTitle")
        name.setAlignment(Qt.AlignCenter)
        layout.addWidget(name)

        version = QLabel(f"Версия {APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(s(6, sc))

        dev_title = QLabel("Разработчик")
        dev_title.setObjectName("FormLabel")
        layout.addWidget(dev_title)

        layout.addWidget(QLabel(AUTHOR))

        github_title = QLabel("GitHub")
        github_title.setObjectName("FormLabel")
        layout.addWidget(github_title)

        github = QLabel(GITHUB_URL)
        github.setObjectName("FormLabel")
        github.setCursor(QCursor(Qt.PointingHandCursor))
        github.mousePressEvent = lambda e: webbrowser.open(GITHUB_URL)
        github.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(github)

        layout.addSpacing(s(6, sc))

        contacts = QLabel("Контакты")
        contacts.setObjectName("FormLabel")
        layout.addWidget(contacts)

        discord = QLabel(f"Discord: {DISCORD_NAME}")
        discord.setTextInteractionFlags(Qt.TextSelectableByMouse)

        telegram = QLabel(f"Telegram: {TELEGRAM_URL}")
        telegram.setObjectName("FormLabel")
        telegram.setCursor(QCursor(Qt.PointingHandCursor))
        telegram.mousePressEvent = self.copy_telegram

        layout.addWidget(discord)
        layout.addWidget(telegram)

        layout.addStretch(1)

        buttons = QHBoxLayout()

        check_btn = QPushButton("Проверить обновления")
        check_btn.setObjectName("Primary")
        check_btn.clicked.connect(self.check_updates)

        buttons.addWidget(check_btn)
        buttons.addStretch(1)

        layout.addLayout(buttons)

    def check_updates(self):
        threading.Thread(
            target=self.parent_window.check_updates_now,
            daemon=True,
        ).start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            self.move(
                event.globalPosition().toPoint() - self.drag_pos
            )
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        event.accept()

    def closeEvent(self, event):
        self.parent().about_dialog = None
        super().closeEvent(event)
        
    def copy_telegram(self, event):
        QGuiApplication.clipboard().setText(TELEGRAM_URL)
        self.parent_window.show_notification(
            "Telegram",
            "Ссылка скопирована."
        )