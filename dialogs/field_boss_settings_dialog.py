import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)

from dialogs.message_dialog import MessageDialog
from styles import Style
from utils import s


DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
ROWS_PER_DAY = 20  # 16 спавнов при интервале 1.5 часа + 4 строки запаса.
FIELD_LOCATIONS = ("Остров хранителей", "Белые горы")


class FieldBossSettingsDialog(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.settings = app.settings
        self.editors = []
        self.drag_pos = None
        self.setWindowTitle("Расписание полевых боссов")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        screen = self.screen().availableGeometry()
        self.resize(min(screen.width() - 48, s(1340, self.settings.app_scale)), min(screen.height() - 48, s(760, self.settings.app_scale)))
        self.build()

    def build(self):
        sc = self.settings.app_scale
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        shell = QFrame(); shell.setObjectName("Shell"); outer.addWidget(shell)
        root = QVBoxLayout(shell)
        root.setContentsMargins(s(18, sc), s(14, sc), s(18, sc), s(16, sc))
        root.setSpacing(s(12, sc))
        top = QFrame(); top.setObjectName("TopBar"); top_row = QHBoxLayout(top); top_row.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("Расписание полевых боссов"); heading.setObjectName("DialogTitle")
        close = QPushButton("×"); close.setObjectName("Close"); close.setFixedSize(s(34, sc), s(32, sc)); close.clicked.connect(self.reject)
        top_row.addWidget(heading); top_row.addStretch(1); top_row.addWidget(close); root.addWidget(top)
        top.mousePressEvent = self.mousePressEvent; top.mouseMoveEvent = self.mouseMoveEvent; top.mouseReleaseEvent = self.mouseReleaseEvent

        self.tabs = QTabWidget()
        for index, fixed_name in enumerate(FIELD_LOCATIONS):
            location = self.settings.field_boss_locations[index]
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(s(10, sc), s(10, sc), s(10, sc), s(10, sc))
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            # The seven-day calendar uses the same compact vertical cell as
            # Event, so every weekday fits without a horizontal scrollbar.
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            calendar = QWidget()
            grid = QGridLayout(calendar)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(s(7, sc))
            grid.setVerticalSpacing(s(5, sc))
            for day, day_name in enumerate(DAYS):
                label = QLabel(day_name)
                label.setObjectName("GroupTitle")
                label.setAlignment(Qt.AlignCenter)
                grid.addWidget(label, 0, day)
            location_editors = []
            schedule = location.get("schedule") if isinstance(location.get("schedule"), dict) else {}
            for row_index in range(ROWS_PER_DAY):
                row_editors = []
                for day in range(7):
                    values = schedule.get(str(day), [])
                    value = values[row_index] if row_index < len(values) and isinstance(values[row_index], dict) else {}
                    cell = QFrame()
                    cell.setObjectName("ScheduleCell")
                    cell.setFixedWidth(s(152, sc))
                    cell_layout = QVBoxLayout(cell)
                    cell_layout.setContentsMargins(s(5, sc), s(4, sc), s(5, sc), s(4, sc))
                    cell_layout.setSpacing(s(3, sc))
                    boss = QLineEdit(str(value.get("name") or ""))
                    boss.setPlaceholderText("")
                    boss.setMaxLength(20)
                    time_edit = QLineEdit(str(value.get("time") or ""))
                    time_edit.setPlaceholderText("00:00")
                    time_edit.setMaxLength(5)
                    time_edit.setAlignment(Qt.AlignCenter)
                    time_edit.setMinimumWidth(s(72, sc))
                    time_edit.textEdited.connect(lambda text, edit=time_edit: self.normalize_time(edit, text))
                    cell_layout.addWidget(boss)
                    cell_layout.addWidget(time_edit)
                    grid.addWidget(cell, row_index + 1, day)
                    row_editors.append((boss, time_edit))
                location_editors.append(row_editors)
            self.editors.append(location_editors)
            scroll.setWidget(calendar)
            tab_layout.addWidget(scroll, 1)
            self.tabs.addTab(tab, fixed_name)
        root.addWidget(self.tabs, 1)

        buttons = QHBoxLayout()
        reset_btn = QPushButton("Сбросить")
        reset_btn.setObjectName("Danger")
        reset_btn.clicked.connect(self.reset_defaults)
        import_btn = QPushButton("Импорт")
        import_btn.setObjectName("Ghost")
        import_btn.clicked.connect(self.import_schedule)
        export_btn = QPushButton("Экспорт")
        export_btn.setObjectName("Ghost")
        export_btn.clicked.connect(self.export_schedule)
        apply_btn = QPushButton("Применить")
        apply_btn.setObjectName("Primary")
        apply_btn.clicked.connect(self.apply)
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("Success")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("Ghost")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(reset_btn)
        buttons.addWidget(import_btn)
        buttons.addWidget(export_btn)
        buttons.addStretch(1)
        buttons.addWidget(save_btn)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)

    def reset_defaults(self):
        if not MessageDialog(self, "Сброс расписания", "Очистить расписания обеих локаций?", ok_text="Сбросить", cancel_text="Отмена").exec_result(): return
        for location in self.editors:
            for row in location:
                for boss, time_edit in row: boss.clear(); time_edit.clear()

    def values(self):
        locations = []
        for location_index, fixed_name in enumerate(FIELD_LOCATIONS):
            schedule = {str(day): [] for day in range(7)}
            for row in self.editors[location_index]:
                for day, (boss, time_edit) in enumerate(row):
                    name = boss.text().strip()
                    time_text = time_edit.text().strip()
                    if not name and not time_text:
                        continue
                    try:
                        hour, minute = map(int, time_text.split(":"))
                        if not (0 <= hour <= 23 and 0 <= minute <= 59): raise ValueError
                    except Exception:
                        raise ValueError(f"{DAYS[day]}: неверное время «{time_text}»")
                    schedule[str(day)].append({"name": name or "Полевой босс", "time": f"{hour:02d}:{minute:02d}"})
            locations.append({"name": fixed_name, "schedule": schedule})
        return locations

    @staticmethod
    def normalize_time(edit, text):
        digits = "".join(ch for ch in text if ch.isdigit())[:4]
        value = digits if len(digits) <= 2 else f"{digits[:2]}:{digits[2:]}"
        if value != text:
            edit.blockSignals(True); edit.setText(value); edit.blockSignals(False)

    def apply(self):
        try:
            self.settings.field_boss_locations = self.values()
        except ValueError as exc:
            MessageDialog(self, "Расписание", str(exc)).exec()
            return False
        self.settings.save()
        self.app.tick()
        if self.app.overlay_window is not None: self.app.overlay_window.apply_settings()
        return True

    def save_and_close(self):
        if self.apply(): self.accept()

    def export_schedule(self):
        try: locations = self.values()
        except ValueError as exc:
            MessageDialog(self, "Расписание", str(exc)).exec(); return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт расписания", "field_bosses.json", "JSON (*.json)")
        if not path: return
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"format": "bns-neo-field-bosses", "version": 1, "locations": locations}, file, ensure_ascii=False, indent=2)

    def import_schedule(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт расписания", "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as file: payload = json.load(file)
            locations = payload.get("locations") if isinstance(payload, dict) else None
            if not isinstance(locations, list): raise ValueError("Неверный формат файла")
            for location_index in range(2):
                location = locations[location_index] if location_index < len(locations) and isinstance(locations[location_index], dict) else {}
                schedule = location.get("schedule") if isinstance(location.get("schedule"), dict) else {}
                for row_index, row in enumerate(self.editors[location_index]):
                    for day, (boss, time_edit) in enumerate(row):
                        rows = schedule.get(str(day), [])
                        value = rows[row_index] if row_index < len(rows) and isinstance(rows[row_index], dict) else {}
                        boss.setText(str(value.get("name") or "")); time_edit.setText(str(value.get("time") or ""))
        except Exception as exc:
            MessageDialog(self, "Импорт", f"Не удалось загрузить расписание:\n{exc}").exec()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event):
        if self.drag_pos is not None: self.move(event.globalPosition().toPoint() - self.drag_pos); event.accept()
    def mouseReleaseEvent(self, event): self.drag_pos = None; event.accept()
