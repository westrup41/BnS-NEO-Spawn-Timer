from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from dialogs.avatar_picker_dialog import AvatarPickerDialog
from styles import Style
from utils import s
from widgets.avatar import AvatarButton


class NicknameDialog(QDialog):
    def __init__(self, parent, title="Профиль чата"):
        super().__init__(parent)
        self.settings = parent.settings
        self._avatar_id = int(getattr(self.settings, "chat_avatar_id", -1))
        self._avatar_picker = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedWidth(s(460, self.settings.app_scale))
        self.build(title)

    def build(self, title_text):
        sc = self.settings.app_scale
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame(); shell.setObjectName("Shell"); root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, sc), s(18, sc), s(22, sc), s(20, sc)); layout.setSpacing(s(14, sc))
        top = QHBoxLayout()
        title = QLabel(title_text); title.setObjectName("SectionTitle")
        close = QPushButton("×"); close.setObjectName("Close"); close.setFixedSize(s(34, sc), s(32, sc)); close.clicked.connect(self.reject)
        top.addWidget(title); top.addStretch(1); top.addWidget(close); layout.addLayout(top)

        profile = QHBoxLayout(); profile.setSpacing(s(16, sc))
        self.avatar = AvatarButton(self._avatar_id, s(78, sc))
        self.avatar.clicked.connect(self.choose_avatar)
        profile.addWidget(self.avatar)
        fields = QVBoxLayout(); fields.setSpacing(s(6, sc))
        label = QLabel("Ник в онлайн-чате"); label.setObjectName("FormLabel")
        self.input = QLineEdit(); self.input.setMaxLength(16); self.input.setPlaceholderText("Например: Westrup")
        self.input.setText(self.settings.discord_nickname[:16]); self.input.textChanged.connect(self.update_confirm); self.input.returnPressed.connect(self.confirm)
        fields.addWidget(label); fields.addWidget(self.input); profile.addLayout(fields, 1); layout.addLayout(profile)
        hint = QLabel("Нажмите на круглый профиль, чтобы выбрать аватар."); hint.setObjectName("FormLabel"); layout.addWidget(hint)

        buttons = QHBoxLayout(); buttons.addStretch(1)
        cancel = QPushButton("Отмена"); cancel.setObjectName("Ghost"); cancel.clicked.connect(self.reject)
        self.confirm_btn = QPushButton("Сохранить"); self.confirm_btn.setObjectName("Primary"); self.confirm_btn.clicked.connect(self.confirm)
        buttons.addWidget(cancel); buttons.addWidget(self.confirm_btn); layout.addLayout(buttons)
        self.update_confirm()

    def choose_avatar(self):
        if self._avatar_picker is not None:
            self._avatar_picker.raise_(); self._avatar_picker.activateWindow(); return
        self._avatar_picker = AvatarPickerDialog(self, self._avatar_id)
        result = self._avatar_picker.exec()
        selected = self._avatar_picker.avatar_id()
        picker = self._avatar_picker; self._avatar_picker = None
        picker.setParent(None); picker.deleteLater()
        if result == QDialog.Accepted:
            self._avatar_id = selected
            self.avatar.set_avatar(self._avatar_id)
            self.update_confirm()

    def update_confirm(self):
        self.confirm_btn.setEnabled(bool(self.input.text().strip()) and self._avatar_id >= 0)

    def confirm(self):
        if self.confirm_btn.isEnabled():
            self.accept()

    def nickname(self):
        return self.input.text().strip()[:16]

    def avatar_id(self):
        return self._avatar_id
