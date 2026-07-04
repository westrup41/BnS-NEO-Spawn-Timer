from datetime import datetime, timedelta
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton
from dialogs.message_dialog import MessageDialog
from PySide6.QtGui import QPalette, QColor
from utils import s
from config import COLORS
from widgets.timer_row import TimerRow
from widgets.combo_delegate import ComboItemDelegate

class TimerBlock(QFrame):
    def __init__(self, app, block: dict, settings_button=False):
        super().__init__()
        self.app = app
        self.block = block
        self.rows = {}
        self.setObjectName("Card")
        sc = app.settings.app_scale
        main = QVBoxLayout(self)
        main.setContentsMargins(s(16, sc), s(16, sc), s(16, sc), s(16, sc))
        main.setSpacing(s(10, sc))

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel(block["title"])
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        main.addLayout(header)
        main.addSpacing(s(8, sc))

        control = QHBoxLayout()
        control.setSpacing(s(10, sc))

        target_label = QLabel("Канал")
        target_label.setObjectName("FormLabel")
        self.target_combo = QComboBox()
        self.target_combo.addItems(block["names"])
        self.target_combo.setFixedWidth(s(176, sc))
        self.target_combo.setMaxVisibleItems(len(block["names"]))
        self.target_combo.setItemDelegate(ComboItemDelegate(sc, self.target_combo))

        time_label = QLabel("Время")
        time_label.setObjectName("FormLabel")
        self.time_input = QLineEdit()
        self.time_input.setMaxLength(5)
        self.time_input.setPlaceholderText("23:59")
        palette = self.time_input.palette()
        palette.setColor(QPalette.PlaceholderText, QColor(COLORS["text_disabled"]))
        self.time_input.setPalette(palette)
        self.time_input.setFixedWidth(s(86, sc))
        self.time_input.textEdited.connect(self.normalize_time_input)

        self.apply_btn = QPushButton("Применить")
        self.apply_btn.setObjectName("Primary")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setFixedWidth(s(104, sc))
        self.apply_btn.clicked.connect(self.apply_time)

        control.addWidget(target_label)
        control.addWidget(self.target_combo)
        control.addWidget(time_label)
        control.addWidget(self.time_input)
        control.addWidget(self.apply_btn)
        control.addStretch(1)
        main.addLayout(control)

        for name in block["names"]:
            row = TimerRow(name, app)
            self.rows[name] = row
            app.rows[name] = row
            main.addWidget(row)

    def normalize_time_input(self, text):
        digits = "".join(ch for ch in text if ch.isdigit())[:4]
        value = digits[:2] + ":" + digits[2:] if len(digits) >= 3 else digits
        if value != text:
            self.time_input.blockSignals(True)
            self.time_input.setText(value)
            self.time_input.blockSignals(False)
        self.apply_btn.setEnabled(len(digits) == 4)

    def apply_time(self):
        text = self.time_input.text()
        try:
            hour, minute = map(int, text.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except Exception:
            MessageDialog(
                self.app,
                "Неверное время",
                "Введите корректное время.",
                "Допустимый формат: 00:00 — 23:59"
            ).exec()
            return
        now = datetime.now()
        base = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        target_check = base + self.block["start"]
        if target_check - now > timedelta(hours=12):
            base -= timedelta(days=1)
        interval_end = base + self.block["end"]
        if now > interval_end:
            base += timedelta(days=1)
        self.app.start_timer(self.target_combo.currentText(), base)
        self.time_input.clear()
        self.apply_btn.setEnabled(False)