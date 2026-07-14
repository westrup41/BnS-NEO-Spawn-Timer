from datetime import datetime
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QTimer
from utils import s
from config import COLORS, CHAT_COOLDOWN

class TimerRow(QFrame):
    def __init__(self, name: str, app):
        super().__init__()
        self.name = name
        self.app = app
        self.setObjectName("TimerBubble")
        self.setProperty("active", "false")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        sc = app.settings.app_scale
        self.setFixedHeight(s(74, sc))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(s(16, sc), s(10, sc), s(16, sc), s(10, sc))
        layout.setSpacing(s(14, sc))

        self.name_label = QLabel(name)
        self.name_label.setObjectName("TimerName")
        self.name_label.setMinimumWidth(s(120, sc))
        layout.addWidget(self.name_label, 1)

        time_box = QVBoxLayout()
        time_box.setSpacing(0)
        self.timer_label = QLabel("--:--:--")
        self.timer_label.setObjectName("TimerValue")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setMinimumWidth(s(142, sc))
        self.timer_label.setMinimumHeight(s(28, sc))
        self.interval_label = QLabel("")
        self.interval_label.setObjectName("TimerSub")
        self.interval_label.setAlignment(Qt.AlignCenter)
        self.interval_label.setMinimumHeight(s(16, sc))
        time_box.addWidget(self.timer_label)
        time_box.addWidget(self.interval_label)
        layout.addLayout(time_box)

        self.toggle_btn = QPushButton("Старт")
        self.toggle_btn.setObjectName("Primary")
        self.toggle_btn.setMinimumWidth(s(94, sc))
        self.toggle_btn.setFixedHeight(s(36, sc))
        self.toggle_btn.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_btn)

        self.restart_btn = QPushButton("Рестарт")
        self.restart_btn.setObjectName("Ghost")
        self.restart_btn.setMinimumWidth(s(94, sc))
        self.restart_btn.setFixedHeight(s(36, sc))
        self.restart_btn.setEnabled(False)
        self.restart_btn.clicked.connect(self.restart)
        layout.addWidget(self.restart_btn)

        self.announce_btn = QPushButton("🚨")
        self.announce_btn.setObjectName("Danger")
        self.announce_btn.setFixedSize(s(40, sc), s(36, sc))
        self.announce_btn.clicked.connect(self.announce_spawn)
        layout.addWidget(self.announce_btn)

        self.announce_cooldown_remaining = self.app.get_announce_cooldown(self.name)
        self.announce_cooldown_timer = QTimer(self)
        self.announce_cooldown_timer.setInterval(1000)
        self.announce_cooldown_timer.timeout.connect(self.update_announce_cooldown)
        if self.announce_cooldown_remaining > 0:
            self.announce_cooldown_timer.start()
        self.refresh_announce_button_visual()

    def announce_spawn(self):
        if self.announce_cooldown_remaining > 0:
            return
        sent_started = self.app.announce_spawn(self.name)
        if sent_started:
            self.start_announce_cooldown(CHAT_COOLDOWN)

    def refresh_announce_button_visual(self):
        cooldown_active = self.announce_cooldown_remaining > 0
        no_internet = not self.app.internet_available
        self.announce_btn.setProperty("cooldown", "true" if cooldown_active else "false")
        self.announce_btn.setProperty("no_internet", "true" if no_internet else "false")
        self.announce_btn.setEnabled(not cooldown_active and not no_internet)
        self.announce_btn.setText("🚨")
        self.announce_btn.setToolTip(
            "Нет доступа в интернет" if no_internet else
            (f"Повторная отправка через {self.announce_cooldown_remaining} сек." if cooldown_active else "Сообщить о появлении")
        )
        self.announce_btn.style().unpolish(self.announce_btn)
        self.announce_btn.style().polish(self.announce_btn)
        self.announce_btn.update()

    def set_announce_cooldown_visual(self, active: bool):
        self.announce_cooldown_remaining = max(1, self.announce_cooldown_remaining) if active else 0
        self.refresh_announce_button_visual()

    def start_announce_cooldown(self, seconds: int):
        self.announce_cooldown_remaining = max(0, int(seconds))
        if self.announce_cooldown_remaining > 0:
            self.refresh_announce_button_visual()
            self.announce_cooldown_timer.start()
        else:
            self.announce_cooldown_timer.stop()
            self.refresh_announce_button_visual()

    def update_announce_cooldown(self):
        self.announce_cooldown_remaining -= 1
        if self.announce_cooldown_remaining <= 0:
            self.announce_cooldown_timer.stop()
            self.announce_cooldown_remaining = 0
        self.refresh_announce_button_visual()

    def toggle(self):
        if self.name in self.app.active_timers or self.name in self.app.spawn_effects:
            self.app.stop_timer(self.name)
        else:
            self.app.start_timer(self.name, datetime.now())

    def restart(self):
        self.app.start_timer(self.name, datetime.now())

    def set_state(self, values: dict):
        active = values.get("active", False)
        status = values.get("status", "idle")
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.interval_label.setText(values.get("interval", ""))
        if status == "detected":
            self.timer_label.setText("Появляется")
            self.interval_label.hide()
        else:
            self.timer_label.setText(values.get("timer", "--:--:--"))
            self.interval_label.show()
        if status == "active":
            color = COLORS["success"]
        elif status == "hot":
            color = COLORS["timer_hot"]
        elif status == "detected":
            color = COLORS["danger"]
        elif status == "idle":
            color = COLORS["text_disabled"]
        else:
            color = COLORS["text_main"]
        self.timer_label.setStyleSheet(f"color: {color};")
        self.toggle_btn.setText("Сброс" if active else "Старт")
        self.toggle_btn.setObjectName("Danger" if active else "Primary")
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)
        self.restart_btn.setEnabled(active)

    def set_spawn_blink(self, active: bool):
        self.setProperty("spawn_alert", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
