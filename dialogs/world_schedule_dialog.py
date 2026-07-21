from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from config import WORLD_BOSS_SCHEDULE
from styles import Style
from utils import s


DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


class WorldScheduleDialog(QDialog):
    def __init__(self, app):
        super().__init__(app); self.app = app; self.drag_pos = None; sc = app.settings.app_scale
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint); self.setAttribute(Qt.WA_TranslucentBackground, True); self.setModal(True)
        self.setStyleSheet(Style.main(sc))
        screen = self.screen().availableGeometry()
        self.resize(min(screen.width() - 64, s(900, sc)), min(screen.height() - 64, s(320, sc)))
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame(); shell.setObjectName("Shell"); root.addWidget(shell)
        layout = QVBoxLayout(shell); layout.setContentsMargins(s(18, sc), s(14, sc), s(18, sc), s(18, sc)); layout.setSpacing(s(12, sc))
        top = QFrame(); top.setObjectName("TopBar"); top_row = QHBoxLayout(top); top_row.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Расписание мировых боссов"); title.setObjectName("DialogTitle"); close = QPushButton("×"); close.setObjectName("Close"); close.setFixedSize(s(34, sc), s(32, sc)); close.clicked.connect(self.accept)
        top_row.addWidget(title); top_row.addStretch(1); top_row.addWidget(close); layout.addWidget(top)
        grid = QGridLayout(); grid.setSpacing(s(8, sc)); grouped = {day: [] for day in range(7)}
        for day, hour, minute, name in WORLD_BOSS_SCHEDULE: grouped[day].append((hour, minute, name))
        for day, day_name in enumerate(DAYS):
            head = QLabel(("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")[day]); head.setToolTip(day_name); head.setObjectName("CalendarDay"); head.setAlignment(Qt.AlignCenter); grid.addWidget(head, 0, day)
            cell = QFrame(); cell.setObjectName("CalendarColumn"); box = QVBoxLayout(cell); box.setContentsMargins(s(8, sc), s(10, sc), s(8, sc), s(10, sc)); box.setSpacing(s(8, sc))
            for hour, minute, name in grouped[day]:
                time = QLabel(f"{hour:02d}:{minute:02d}"); time.setObjectName("CalendarTime"); time.setAlignment(Qt.AlignCenter)
                boss = QLabel(name); boss.setObjectName("CalendarBoss"); boss.setAlignment(Qt.AlignCenter); boss.setWordWrap(True)
                box.addWidget(time); box.addWidget(boss)
            box.addStretch(1); grid.addWidget(cell, 1, day)
        layout.addLayout(grid, 1)
        top.mousePressEvent = self.mousePressEvent; top.mouseMoveEvent = self.mouseMoveEvent; top.mouseReleaseEvent = self.mouseReleaseEvent

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event):
        if self.drag_pos is not None: self.move(event.globalPosition().toPoint() - self.drag_pos); event.accept()
    def mouseReleaseEvent(self, event): self.drag_pos = None; event.accept()
