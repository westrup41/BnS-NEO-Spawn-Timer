from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from utils import s
from config import COLORS

class WorldBossBlock(QFrame):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("Card")
        sc = app.settings.app_scale
        layout = QVBoxLayout(self)
        layout.setContentsMargins(s(16, sc), s(2, sc), s(16, sc), s(16, sc))
        layout.setSpacing(s(6, sc))

        title = QLabel("Мировой босс")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        bubble = QFrame()
        bubble.setObjectName("TimerBubble")
        bubble_layout = QHBoxLayout(bubble)
        bubble_layout.setContentsMargins(s(18, sc), s(15, sc), s(18, sc), s(15, sc))
        bubble_layout.setSpacing(s(12, sc))

        left = QVBoxLayout()
        left.setSpacing(2)
        self.name_label = QLabel("—")
        self.name_label.setObjectName("WorldName")
        left.addWidget(self.name_label)
        bubble_layout.addLayout(left, 1)

        self.timer_label = QLabel("--:--:--")
        self.timer_label.setObjectName("WorldTimer")
        self.timer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bubble_layout.addWidget(self.timer_label)
        layout.addWidget(bubble)

    def set_state(self, name: str, timer_text: str, status: str):
        self.name_label.setText(name)
        self.timer_label.setText(timer_text)
        if status == "active":
            color = COLORS["success"]
        elif status == "hot":
            color = COLORS["timer_hot"]
        else:
            color = COLORS["text_main"]
        self.timer_label.setStyleSheet(f"color: {color};")