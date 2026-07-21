from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from styles import Style
from utils import s


DAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


class UpcomingEventsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent; self.drag_pos = None; sc = parent.settings.app_scale
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground, True); self.setModal(True)
        self.setStyleSheet(Style.main(sc))
        grouped = []
        for day in range(7):
            rows = parent.settings.event_schedule.get(str(day), []) if isinstance(parent.settings.event_schedule, dict) else []
            grouped.append([row for row in rows if isinstance(row, dict) and str(row.get("time") or "").strip()])
        max_rows = max((len(rows) for rows in grouped), default=0)
        screen = self.screen().availableGeometry()
        wanted_height = max(300, min(650, 150 + max_rows * 58))
        self.resize(min(screen.width() - 64, s(920, sc)), min(screen.height() - 64, s(wanted_height, sc)))

        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame(); shell.setObjectName("Shell"); root.addWidget(shell)
        layout = QVBoxLayout(shell); layout.setContentsMargins(s(18, sc), s(14, sc), s(18, sc), s(18, sc)); layout.setSpacing(s(12, sc))
        top = QFrame(); top.setObjectName("TopBar"); top_row = QHBoxLayout(top); top_row.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Расписание Event"); title.setObjectName("DialogTitle")
        close = QPushButton("×"); close.setObjectName("Close"); close.setFixedSize(s(34, sc), s(32, sc)); close.clicked.connect(self.accept)
        top_row.addWidget(title); top_row.addStretch(1); top_row.addWidget(close); layout.addWidget(top)
        top.mousePressEvent = self.mousePressEvent; top.mouseMoveEvent = self.mouseMoveEvent; top.mouseReleaseEvent = self.mouseReleaseEvent

        scroll = QScrollArea(); scroll.setObjectName("SettingsScroll"); scroll.setWidgetResizable(True)
        host = QWidget(); grid = QGridLayout(host); grid.setSpacing(s(8, sc)); grid.setContentsMargins(0, 0, s(5, sc), 0)
        for day, label_text in enumerate(DAYS):
            head = QLabel(label_text); head.setObjectName("CalendarDay"); head.setAlignment(Qt.AlignCenter); grid.addWidget(head, 0, day)
            cell = QFrame(); cell.setObjectName("CalendarColumn"); box = QVBoxLayout(cell); box.setContentsMargins(s(8, sc), s(9, sc), s(8, sc), s(9, sc)); box.setSpacing(s(7, sc))
            if not grouped[day]:
                empty = QLabel("—"); empty.setObjectName("FormLabel"); empty.setAlignment(Qt.AlignCenter); box.addWidget(empty)
            for row in grouped[day]:
                time = QLabel(str(row.get("time") or "")); time.setObjectName("CalendarTime"); time.setAlignment(Qt.AlignCenter)
                name = QLabel(str(row.get("name") or "Неизвестный босс")); name.setObjectName("CalendarBoss"); name.setAlignment(Qt.AlignCenter); name.setWordWrap(True)
                box.addWidget(time); box.addWidget(name)
            box.addStretch(1); grid.addWidget(cell, 1, day)
        scroll.setWidget(host); layout.addWidget(scroll, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event):
        if self.drag_pos is not None: self.move(event.globalPosition().toPoint() - self.drag_pos); event.accept()
    def mouseReleaseEvent(self, event): self.drag_pos = None; event.accept()
