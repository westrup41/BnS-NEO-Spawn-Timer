from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from styles import Style
from utils import s, upcoming_custom_events


class UpcomingEventsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("StandaloneDialog")
        self.app = parent
        self.setWindowTitle("Ближайшие Event")
        self.setModal(False)
        self.setStyleSheet(Style.main(parent.settings.app_scale))
        self.resize(s(500, parent.settings.app_scale), s(330, parent.settings.app_scale))
        layout = QVBoxLayout(self)
        title = QLabel("Ближайшие события")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        events = upcoming_custom_events(parent.settings.event_schedule, 5)
        if not events:
            empty = QLabel("Расписание пусто")
            empty.setObjectName("FormLabel")
            layout.addWidget(empty)
        for index, item in enumerate(events, 1):
            card = QFrame()
            card.setObjectName("SettingsGroup")
            row = QHBoxLayout(card)
            row.addWidget(QLabel(f"{index}. {item['name']}"), 1)
            row.addWidget(QLabel(item["target"].strftime("%a, %d.%m • %H:%M")))
            layout.addWidget(card)
        layout.addStretch(1)
        close = QPushButton("Готово")
        close.setObjectName("Primary")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
