from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from styles import Style
from utils import s
from widgets.avatar import AVATAR_COUNT, AvatarButton


class AvatarPickerDialog(QDialog):
    def __init__(self, parent, current=-1):
        super().__init__(parent)
        self.settings = parent.settings if hasattr(parent, "settings") else parent.app.settings
        self.selected_avatar = int(current)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedWidth(s(500, self.settings.app_scale))
        self.build()

    def build(self):
        sc = self.settings.app_scale
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame(); shell.setObjectName("Shell"); root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, sc), s(18, sc), s(22, sc), s(22, sc))
        layout.setSpacing(s(14, sc))
        top = QHBoxLayout()
        title = QLabel("Выберите аватар"); title.setObjectName("SectionTitle")
        close = QPushButton("×"); close.setObjectName("Close"); close.setFixedSize(s(34, sc), s(32, sc)); close.clicked.connect(self.reject)
        top.addWidget(title); top.addStretch(1); top.addWidget(close); layout.addLayout(top)

        grid_host = QFrame(); grid_host.setObjectName("AvatarGrid")
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(s(10, sc), s(10, sc), s(10, sc), s(10, sc))
        grid.setHorizontalSpacing(s(8, sc)); grid.setVerticalSpacing(s(8, sc))
        self.buttons = []
        for avatar_id in range(AVATAR_COUNT):
            button = AvatarButton(avatar_id, s(58, sc), grid_host)
            button.set_selected(avatar_id == self.selected_avatar)
            button.clicked.connect(lambda checked=False, value=avatar_id: self.choose(value))
            grid.addWidget(button, avatar_id // 5, avatar_id % 5, Qt.AlignCenter)
            self.buttons.append(button)
        layout.addWidget(grid_host)

    def choose(self, avatar_id):
        self.selected_avatar = int(avatar_id)
        for button in self.buttons:
            button.set_selected(button.avatar_id == self.selected_avatar)
        self.accept()

    def avatar_id(self):
        return self.selected_avatar

