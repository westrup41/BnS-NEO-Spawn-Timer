import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from dialogs.message_dialog import MessageDialog
from styles import Style
from utils import s


DAYS = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье")
ROWS_PER_DAY = 10


class EventSettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent; self.settings = parent.settings; self.drag_pos = None; self.editors = []
        sc = self.settings.app_scale
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True); self.setStyleSheet(Style.main(sc))
        screen = self.screen().availableGeometry()
        self.resize(min(screen.width() - 56, s(1180, sc)), min(screen.height() - 56, s(680, sc)))
        self.build()

    def build(self):
        sc = self.settings.app_scale
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame(); shell.setObjectName("Shell"); root.addWidget(shell)
        main = QVBoxLayout(shell); main.setContentsMargins(s(18, sc), s(14, sc), s(18, sc), s(16, sc)); main.setSpacing(s(10, sc))
        top = QFrame(); top.setObjectName("TopBar"); top_row = QHBoxLayout(top); top_row.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Расписание Event"); title.setObjectName("DialogTitle")
        close = QPushButton("×"); close.setObjectName("Close"); close.setFixedSize(s(34, sc), s(32, sc)); close.clicked.connect(self.reject)
        top_row.addWidget(title); top_row.addStretch(1); top_row.addWidget(close); main.addWidget(top)
        top.mousePressEvent = self.mousePressEvent; top.mouseMoveEvent = self.mouseMoveEvent; top.mouseReleaseEvent = self.mouseReleaseEvent

        tools = QHBoxLayout(); tools.setSpacing(s(8, sc))
        tools.addWidget(QLabel("Имя для всех"))
        self.global_name = QLineEdit("Неизвестный босс"); self.global_name.setMaxLength(30); self.global_name.setFixedWidth(s(210, sc)); tools.addWidget(self.global_name)
        fill = QPushButton("Заполнить имена"); fill.setObjectName("Ghost"); fill.clicked.connect(self.apply_name_to_all); tools.addWidget(fill)
        tools.addSpacing(s(18, sc)); tools.addWidget(QLabel("Время появления"))
        self.appearance = QComboBox()
        for minutes in range(1, 60): self.appearance.addItem(f"{minutes} мин.", minutes)
        self.appearance.setCurrentIndex(max(0, min(58, int(self.settings.event_appearance_minutes) - 1)))
        self.appearance.setFixedWidth(s(110, sc)); tools.addWidget(self.appearance)
        tools.addStretch(1); main.addLayout(tools)

        scroll = QScrollArea(); scroll.setObjectName("SettingsScroll"); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        calendar = QWidget(); grid = QGridLayout(calendar); grid.setContentsMargins(0, 0, 0, 0); grid.setHorizontalSpacing(s(6, sc)); grid.setVerticalSpacing(s(5, sc))
        for day, name in enumerate(DAYS):
            label = QLabel(name); label.setObjectName("CalendarDay"); label.setAlignment(Qt.AlignCenter); grid.addWidget(label, 0, day)
        schedule = self.settings.event_schedule if isinstance(self.settings.event_schedule, dict) else {}
        for row_index in range(ROWS_PER_DAY):
            row_editors = []
            for day in range(7):
                values = schedule.get(str(day), []); value = values[row_index] if row_index < len(values) and isinstance(values[row_index], dict) else {}
                cell = QFrame(); cell.setObjectName("ScheduleCell"); cell_box = QVBoxLayout(cell); cell_box.setContentsMargins(s(5, sc), s(4, sc), s(5, sc), s(4, sc)); cell_box.setSpacing(s(3, sc))
                cell.setFixedWidth(s(152, sc))
                boss = QLineEdit(str(value.get("name") or "")); boss.setPlaceholderText(""); boss.setMaxLength(30)
                time_edit = QLineEdit(str(value.get("time") or "")); time_edit.setPlaceholderText("00:00"); time_edit.setMaxLength(5); time_edit.setAlignment(Qt.AlignCenter); time_edit.setMinimumWidth(s(72, sc))
                time_edit.textEdited.connect(lambda text, edit=time_edit: self.normalize_time(edit, text))
                cell_box.addWidget(boss); cell_box.addWidget(time_edit); grid.addWidget(cell, row_index + 1, day); row_editors.append((boss, time_edit))
            self.editors.append(row_editors)
        scroll.setWidget(calendar); main.addWidget(scroll, 1)

        buttons = QHBoxLayout(); clear = QPushButton("Очистить"); clear.setObjectName("Danger"); clear.clicked.connect(self.clear)
        reset = QPushButton("Сбросить"); reset.setObjectName("Ghost"); reset.clicked.connect(self.reset_defaults)
        export_btn = QPushButton("Экспорт"); export_btn.setObjectName("Ghost"); export_btn.clicked.connect(self.export_schedule)
        import_btn = QPushButton("Импорт"); import_btn.setObjectName("Ghost"); import_btn.clicked.connect(self.import_schedule)
        cancel = QPushButton("Отмена"); cancel.setObjectName("Ghost"); cancel.clicked.connect(self.reject)
        apply_btn = QPushButton("Применить"); apply_btn.setObjectName("Primary"); apply_btn.clicked.connect(self.apply)
        save = QPushButton("Сохранить"); save.setObjectName("Success"); save.clicked.connect(self.save_and_close)
        for button in (clear, reset, import_btn, export_btn): buttons.addWidget(button)
        buttons.addStretch(1)
        for button in (save, apply_btn, cancel): buttons.addWidget(button)
        main.addLayout(buttons)

    @staticmethod
    def normalize_time(edit, text):
        digits = "".join(ch for ch in text if ch.isdigit())[:4]
        value = digits if len(digits) <= 2 else f"{digits[:2]}:{digits[2:]}"
        if value != text: edit.blockSignals(True); edit.setText(value); edit.blockSignals(False)

    def apply_name_to_all(self):
        name = self.global_name.text().strip() or "Неизвестный босс"
        for row in self.editors:
            for boss, _ in row: boss.setText(name)

    def clear(self):
        for row in self.editors:
            for boss, time_edit in row: boss.clear(); time_edit.clear()

    def reset_defaults(self):
        if not MessageDialog(self, "Сброс расписания", "Вернуть расписание Event к пустому значению?", ok_text="Сбросить", cancel_text="Отмена").exec_result(): return
        self.clear(); self.global_name.setText("Неизвестный босс"); self.appearance.setCurrentIndex(4)

    def values(self):
        schedule = {str(day): [] for day in range(7)}
        for row in self.editors:
            for day, (boss, time_edit) in enumerate(row):
                name, value = boss.text().strip(), time_edit.text().strip()
                if not value: continue
                try:
                    hour, minute = map(int, value.split(":"))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59): raise ValueError
                except Exception: raise ValueError(f"{DAYS[day]}: неверное время «{value}»")
                schedule[str(day)].append({"name": (name or "Неизвестный босс")[:30], "time": f"{hour:02d}:{minute:02d}"})
        return schedule

    def apply(self):
        try: schedule = self.values()
        except ValueError as exc: MessageDialog(self, "Расписание Event", str(exc)).exec(); return False
        self.settings.event_schedule = schedule; self.settings.event_appearance_minutes = int(self.appearance.currentData()); self.settings.save(); self.app.tick()
        if self.app.overlay_window is not None: self.app.overlay_window.apply_settings()
        return True

    def save_and_close(self):
        if self.apply(): self.accept()

    def export_schedule(self):
        try: schedule = self.values()
        except ValueError as exc: MessageDialog(self, "Расписание Event", str(exc)).exec(); return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт Event", "bns-neo-event.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as file: json.dump({"format":"bns-neo-event","version":2,"appearance_minutes":int(self.appearance.currentData()),"schedule":schedule}, file, ensure_ascii=False, indent=2)

    def import_schedule(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт Event", "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as file: payload = json.load(file)
            schedule = payload.get("schedule") if isinstance(payload, dict) else None
            if not isinstance(schedule, dict): raise ValueError("Неверный формат файла")
            for row_index, row in enumerate(self.editors):
                for day, (boss, time_edit) in enumerate(row):
                    rows = schedule.get(str(day), []); value = rows[row_index] if row_index < len(rows) and isinstance(rows[row_index], dict) else {}
                    boss.setText(str(value.get("name") or "")); time_edit.setText(str(value.get("time") or ""))
            minutes = max(1, min(59, int(payload.get("appearance_minutes", 5))))
            self.appearance.setCurrentIndex(minutes - 1)
        except Exception as exc: MessageDialog(self, "Импорт Event", str(exc)).exec()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event):
        if self.drag_pos is not None: self.move(event.globalPosition().toPoint() - self.drag_pos); event.accept()
    def mouseReleaseEvent(self, event): self.drag_pos = None; event.accept()
