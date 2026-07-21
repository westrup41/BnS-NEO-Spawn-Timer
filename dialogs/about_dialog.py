import webbrowser

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer, QPoint, QSize

from config import APP_NAME, APP_VERSION, GITHUB_URL, TELEGRAM_URL, DISCORD_NAME
from resources import make_github_icon, make_telegram_icon, make_discord_icon
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
        self.setFixedSize(s(450, parent.settings.app_scale), s(245, parent.settings.app_scale))
        self.build()

    def build(self):
        sc = self.parent_window.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, sc), s(18, sc), s(22, sc), s(20, sc))
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

        contacts = QHBoxLayout()
        contacts.addStretch(1)
        github = self.contact_button("GitHub", make_github_icon(s(72, sc)), lambda: webbrowser.open(GITHUB_URL))
        telegram = self.contact_button("Telegram", make_telegram_icon(s(72, sc)), lambda: webbrowser.open(TELEGRAM_URL))
        self.discord_btn = self.contact_button("Discord", make_discord_icon(s(72, sc)), self.toggle_discord_popover)
        contacts.addWidget(github)
        contacts.addWidget(telegram)
        contacts.addWidget(self.discord_btn)
        contacts.addStretch(1)
        layout.addLayout(contacts)
        layout.addSpacing(s(2, sc))

        update_btn = QPushButton("Проверить обновления")
        update_btn.setObjectName("Ghost")
        update_btn.clicked.connect(lambda: self.parent_window.updater.check(silent=False))
        layout.addWidget(update_btn, 0, Qt.AlignCenter)

        self.discord_popover = QFrame(self)
        self.discord_popover.setObjectName("ContactPopover")
        pop_layout = QVBoxLayout(self.discord_popover)
        pop_layout.setContentsMargins(s(14, sc), s(9, sc), s(14, sc), s(9, sc))
        pop_label = QLabel(DISCORD_NAME)
        pop_label.setObjectName("ChatNick")
        pop_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        pop_layout.addWidget(pop_label)
        self.discord_popover.adjustSize()
        self.discord_popover.hide()

    def contact_button(self, text, icon, callback):
        sc = self.parent_window.settings.app_scale
        button = QPushButton(text)
        button.setObjectName("SocialButton")
        button.setIcon(icon)
        button.setIconSize(QSize(s(25, sc), s(25, sc)))
        button.setAutoDefault(False)
        button.clicked.connect(callback)
        return button

    def toggle_discord_popover(self):
        if self.discord_popover.isVisible():
            self.discord_popover.hide()
            return
        point = self.discord_btn.mapTo(self, QPoint(0, self.discord_btn.height() + s(6, self.parent_window.settings.app_scale)))
        self.discord_popover.move(point.x(), point.y())
        self.discord_popover.show()
        self.discord_popover.raise_()
        QTimer.singleShot(5000, self.discord_popover.hide)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        event.accept()

    def closeEvent(self, event):
        self.parent().about_dialog = None
        super().closeEvent(event)
