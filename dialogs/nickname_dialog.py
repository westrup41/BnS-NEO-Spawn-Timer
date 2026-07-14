from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from styles import Style
from utils import s


class NicknameDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.settings = parent.settings
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedWidth(s(460, self.settings.app_scale))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, self.settings.app_scale), s(18, self.settings.app_scale), s(22, self.settings.app_scale), s(20, self.settings.app_scale))
        layout.setSpacing(s(14, self.settings.app_scale))

        top = QHBoxLayout()
        title = QLabel("Введите ник для чата")
        title.setObjectName("SectionTitle")
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, self.settings.app_scale), s(32, self.settings.app_scale))
        close.clicked.connect(self.reject)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)
        layout.addLayout(top)

        hint = QLabel("Ник нужен только для чата. Максимум 16 символов.")
        hint.setObjectName("FormLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.input = QLineEdit()
        self.input.setMaxLength(16)
        self.input.setPlaceholderText("Например: Westrup")
        self.input.setText(self.settings.discord_nickname[:16])
        self.input.textChanged.connect(self.update_confirm)
        self.input.returnPressed.connect(self.confirm)
        layout.addWidget(self.input)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.setObjectName("Ghost")
        cancel.setAutoDefault(False)
        cancel.clicked.connect(self.reject)
        self.confirm_btn = QPushButton("Подтвердить")
        self.confirm_btn.setObjectName("Primary")
        self.confirm_btn.setAutoDefault(False)
        self.confirm_btn.clicked.connect(self.confirm)
        buttons.addWidget(cancel)
        buttons.addWidget(self.confirm_btn)
        layout.addLayout(buttons)
        self.update_confirm()

    def update_confirm(self):
        self.confirm_btn.setEnabled(bool(self.input.text().strip()))

    def confirm(self):
        if not self.input.text().strip():
            return
        self.accept()

    def nickname(self):
        return self.input.text().strip()[:16]
