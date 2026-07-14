from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from config import COLORS
from dialogs.event_settings_dialog import EventSettingsDialog
from dialogs.upcoming_events_dialog import UpcomingEventsDialog
from resources import make_settings_icon
from utils import s


class EventBlock(QFrame):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("Card")
        sc = app.settings.app_scale
        layout = QVBoxLayout(self)
        layout.setContentsMargins(s(16, sc), s(10, sc), s(16, sc), s(16, sc))
        layout.setSpacing(s(8, sc))

        header = QHBoxLayout()
        title = QLabel("Event")
        title.setObjectName("SectionTitle")
        settings_btn = QPushButton("")
        settings_btn.setObjectName("Ghost")
        settings_btn.setIcon(make_settings_icon(s(22, sc)))
        settings_btn.setIconSize(QSize(s(22, sc), s(22, sc)))
        settings_btn.setFixedSize(s(36, sc), s(32, sc))
        settings_btn.setToolTip("Настроить расписание Event")
        settings_btn.clicked.connect(self.open_settings)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(settings_btn)
        layout.addLayout(header)

        bubble = QFrame()
        bubble.setObjectName("TimerBubble")
        row = QHBoxLayout(bubble)
        row.setContentsMargins(s(18, sc), s(15, sc), s(18, sc), s(15, sc))
        self.name_label = QLabel("No_Text")
        self.name_label.setObjectName("WorldName")
        self.name_label.setWordWrap(True)
        self.name_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.timer_label = QLabel("--:--:--")
        self.timer_label.setObjectName("WorldTimer")
        self.timer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.day_badge = QLabel("")
        self.day_badge.setObjectName("DayBadge")
        self.day_badge.setAlignment(Qt.AlignCenter)
        self.day_badge.hide()
        row.addWidget(self.name_label, 1)
        row.addWidget(self.day_badge)
        row.addWidget(self.timer_label)
        layout.addWidget(bubble)
        bubble.setCursor(Qt.PointingHandCursor)
        bubble.setToolTip("Показать 5 ближайших событий")
        bubble.mousePressEvent = self.show_upcoming

    def open_settings(self):
        EventSettingsDialog(self.app).exec()

    def show_upcoming(self, event):
        if event.button() == Qt.LeftButton:
            UpcomingEventsDialog(self.app).exec()

    def set_state(self, name: str, timer_text: str, status: str, days: int = 0):
        self.name_label.setText(name or "No_Text")
        self.timer_label.setText(timer_text or "--:--:--")
        self.day_badge.setText(f"{days} сут.")
        self.day_badge.setVisible(days > 0 and status not in ("appearing", "idle"))
        if status == "hot":
            color = COLORS["timer_hot"]
        elif status == "appearing":
            color = COLORS["success"]
        else:
            color = COLORS["text_main"]
        self.timer_label.setStyleSheet(f"color: {color};")
