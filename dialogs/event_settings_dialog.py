from datetime import datetime
import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from dialogs.message_dialog import MessageDialog
from styles import Style
from utils import s


DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


class EventSettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.settings = parent.settings
        self.rows = {day: [] for day in range(7)}
        self.day_layouts = {}
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedSize(s(720, self.settings.app_scale), s(780, self.settings.app_scale))
        self.build()

    def build(self):
        sc = self.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        main = QVBoxLayout(shell)
        main.setContentsMargins(s(20, sc), s(16, sc), s(20, sc), s(18, sc))
        main.setSpacing(s(10, sc))

        top_frame = QFrame()
        top = QHBoxLayout(top_frame)
        top.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Настройки Event")
        title.setObjectName("SectionTitle")
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.clicked.connect(self.reject)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)
        main.addWidget(top_frame)
        top_frame.mousePressEvent = self.mousePressEvent
        top_frame.mouseMoveEvent = self.mouseMoveEvent
        top_frame.mouseReleaseEvent = self.mouseReleaseEvent
        title.mousePressEvent = self.mousePressEvent
        title.mouseMoveEvent = self.mouseMoveEvent
        title.mouseReleaseEvent = self.mouseReleaseEvent

        global_row = QHBoxLayout()
        global_label = QLabel("Имя босса")
        global_label.setObjectName("FormLabel")
        self.global_name = QLineEdit("No_Text")
        self.global_name.setMaxLength(30)
        self.global_name.setFixedWidth(s(300, sc))
        apply_all_btn = QPushButton("Применить ко всем")
        apply_all_btn.setObjectName("Primary")
        apply_all_btn.clicked.connect(self.apply_name_to_all)
        global_row.addWidget(global_label)
        global_row.addWidget(self.global_name)
        global_row.addWidget(apply_all_btn)
        global_row.addStretch(1)
        main.addLayout(global_row)

        appearance_row = QHBoxLayout()
        appearance_label = QLabel("Время появления")
        appearance_label.setObjectName("FormLabel")
        self.appearance_minutes = QSpinBox()
        self.appearance_minutes.setButtonSymbols(QSpinBox.NoButtons)
        self.appearance_minutes.setRange(1, 59)
        self.appearance_minutes.setSuffix(" мин.")
        self.appearance_minutes.setValue(self.settings.event_appearance_minutes)
        self.appearance_minutes.setFixedWidth(s(110, sc))
        apply_appearance = QPushButton("Применить")
        apply_appearance.setObjectName("Primary")
        apply_appearance.clicked.connect(self.apply_appearance_time)
        reset_appearance = QPushButton("Сбросить")
        reset_appearance.setObjectName("Ghost")
        reset_appearance.clicked.connect(lambda: self.appearance_minutes.setValue(5))
        appearance_row.addWidget(appearance_label)
        appearance_row.addWidget(self.appearance_minutes)
        appearance_row.addWidget(apply_appearance)
        appearance_row.addWidget(reset_appearance)
        appearance_row.addStretch(1)
        main.addLayout(appearance_row)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        host.setObjectName("SettingsScrollContent")
        days_layout = QVBoxLayout(host)
        days_layout.setContentsMargins(0, 0, s(8, sc), 0)
        days_layout.setSpacing(s(10, sc))

        schedule = self.settings.event_schedule
        for day, day_name in enumerate(DAYS):
            group = QFrame()
            group.setObjectName("SettingsGroup")
            box = QVBoxLayout(group)
            box.setContentsMargins(s(12, sc), s(10, sc), s(12, sc), s(10, sc))
            box.setSpacing(s(6, sc))
            header = QHBoxLayout()
            label_text = f"{day_name} (сегодня)" if day == datetime.now().weekday() else day_name
            label = QLabel(label_text)
            label.setObjectName("GroupTitle")
            add = QPushButton("+")
            add.setObjectName("Ghost")
            add.setFixedSize(s(34, sc), s(30, sc))
            add.setToolTip("Добавить событие")
            add.clicked.connect(lambda checked=False, target_day=day: self.add_row(target_day))
            header.addWidget(label)
            header.addStretch(1)
            header.addWidget(add)
            box.addLayout(header)
            self.day_layouts[day] = box
            day_rows = schedule.get(str(day), [])
            for row in day_rows[:10]:
                self.add_row(day, row.get("name", "No_Text"), row.get("time", ""))
            while len(self.rows[day]) < 3:
                self.add_row(day)
            days_layout.addWidget(group)

        days_layout.addStretch(1)
        scroll.setWidget(host)
        main.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        clear = QPushButton("Очистить")
        clear.setObjectName("Danger")
        clear.clicked.connect(self.clear_schedule)
        export_btn = QPushButton("Экспорт")
        export_btn.setObjectName("Ghost")
        export_btn.clicked.connect(self.export_schedule)
        import_btn = QPushButton("Импорт")
        import_btn.setObjectName("Ghost")
        import_btn.clicked.connect(self.import_schedule)
        cancel = QPushButton("Отмена")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setObjectName("Success")
        save.clicked.connect(self.save_schedule)
        apply_btn = QPushButton("Применить")
        apply_btn.setObjectName("Primary")
        apply_btn.clicked.connect(self.apply_schedule)
        buttons.addWidget(clear)
        buttons.addWidget(export_btn)
        buttons.addWidget(import_btn)
        buttons.addStretch(1)
        buttons.addWidget(save)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel)
        main.addLayout(buttons)

    def add_row(self, day: int, name: str = "No_Text", time: str = ""):
        if len(self.rows[day]) >= 10:
            return
        sc = self.settings.app_scale
        line = QFrame()
        row_layout = QHBoxLayout(line)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(s(8, sc))
        number = QLabel(str(len(self.rows[day]) + 1))
        number.setObjectName("FormLabel")
        number.setFixedWidth(s(20, sc))
        name_input = QLineEdit(name or "No_Text")
        name_input.setMaxLength(30)
        name_input.setPlaceholderText("No_Text")
        time_input = QLineEdit(time)
        time_input.setMaxLength(5)
        time_input.setPlaceholderText("23:59")
        time_input.setFixedWidth(s(90, sc))
        time_input.textEdited.connect(lambda value, edit=time_input: self.normalize_time(edit, value))
        row_layout.addWidget(number)
        row_layout.addWidget(name_input, 1)
        row_layout.addWidget(time_input)
        remove_btn = None
        if len(self.rows[day]) >= 3:
            remove_btn = QPushButton("×")
            remove_btn.setObjectName("Close")
            remove_btn.setFixedSize(s(34, sc), s(34, sc))
            remove_btn.setToolTip("Удалить строку")
            remove_btn.clicked.connect(lambda checked=False, target_day=day, target_line=line: self.remove_row(target_day, target_line))
            row_layout.addWidget(remove_btn)
        self.rows[day].append((line, number, name_input, time_input))
        self.day_layouts[day].addWidget(line)

    def remove_row(self, day: int, line):
        if len(self.rows[day]) <= 3:
            return
        for index, row in enumerate(self.rows[day]):
            if row[0] is line and index >= 3:
                self.rows[day].pop(index)
                self.day_layouts[day].removeWidget(line)
                line.deleteLater()
                break
        for index, (_, number, _, _) in enumerate(self.rows[day], start=1):
            number.setText(str(index))

    def normalize_time(self, edit, text):
        digits = "".join(char for char in text if char.isdigit())[:4]
        value = digits[:2] + ":" + digits[2:] if len(digits) >= 3 else digits
        if value != text:
            edit.blockSignals(True)
            edit.setText(value)
            edit.blockSignals(False)

    def apply_name_to_all(self):
        name = self.global_name.text().strip() or "No_Text"
        for day_rows in self.rows.values():
            for _, _, name_input, _ in day_rows:
                name_input.setText(name)

    def apply_appearance_time(self):
        self.settings.event_appearance_minutes = self.appearance_minutes.value()
        self.settings.save()
        self.app.tick()

    def clear_schedule(self):
        if not MessageDialog(
            self,
            "Хотите очистить расписание?",
            "Будут удалены все данные событий.",
            ok_text="Очистить",
            cancel_text="Отмена",
            ok_first=True,
            center_buttons=True,
        ).exec_result():
            return
        self.global_name.setText("No_Text")
        for day in range(7):
            for line, _, _, _ in self.rows[day][3:]:
                self.day_layouts[day].removeWidget(line)
                line.deleteLater()
            self.rows[day] = self.rows[day][:3]
            for _, _, name_input, time_input in self.rows[day]:
                name_input.setText("No_Text")
                time_input.clear()

    def save_schedule(self):
        if self._store_schedule():
            self.accept()

    def apply_schedule(self):
        self._store_schedule()

    def _store_schedule(self):
        schedule = {}
        for day in range(7):
            day_rows = []
            for _, _, name_input, time_input in self.rows[day]:
                time = time_input.text().strip()
                if time:
                    try:
                        hour, minute = map(int, time.split(":"))
                        if not (0 <= hour <= 23 and 0 <= minute <= 59):
                            raise ValueError
                    except Exception:
                        MessageDialog(self, "Неверное время", f"{DAYS[day]}: укажите время от 00:00 до 23:59.").exec()
                        time_input.setFocus()
                        return False
                day_rows.append({
                    "name": (name_input.text().strip() or "No_Text")[:30],
                    "time": time,
                })
            schedule[str(day)] = day_rows
        self.settings.event_schedule = schedule
        self.settings.event_appearance_minutes = self.appearance_minutes.value()
        self.settings.save()
        self.app.tick()
        if self.app.overlay_window is not None:
            self.app.overlay_window.apply_settings()
        return True

    def export_schedule(self):
        if not self._store_schedule():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт Event", "bns-neo-event.json", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as file:
                json.dump({"format": "bns-neo-event", "version": 1,
                           "appearance_minutes": self.settings.event_appearance_minutes,
                           "schedule": self.settings.event_schedule}, file, ensure_ascii=False, indent=2)
        except Exception as exc:
            MessageDialog(self, "Ошибка экспорта", str(exc)).exec()

    def import_schedule(self):
        path, _ = QFileDialog.getOpenFileName(self, "Импорт Event", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            if payload.get("format") != "bns-neo-event" or not isinstance(payload.get("schedule"), dict):
                raise ValueError("Это не файл расписания Event")
            self.settings.event_schedule = payload["schedule"]
            self.settings.event_appearance_minutes = max(1, min(59, int(payload.get("appearance_minutes", 5))))
            self.settings.save()
            MessageDialog(self, "Импорт завершён", "Расписание загружено. Откройте окно Event заново для проверки.").exec()
            self.accept()
        except Exception as exc:
            MessageDialog(self, "Ошибка импорта", str(exc)).exec()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        event.accept()
