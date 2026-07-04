from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QTimer
from settings import AppSettings
from utils import s
from config import COLORS, BLOCKS
from styles import Style
from services.windows import set_windows_click_through

class OverlayWindow(QWidget):
    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.drag_pos = None
        self.root_layout = None
        self.timer_labels = {}
        self.world_name_label = None
        self.world_timer_label = None
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowOpacity(self.settings.overlay_alpha)
        self.move(self.settings.overlay_pos_x, self.settings.overlay_pos_y)
        self.build()
        self.apply_lock()

    def selected_blocks(self):
        result = []
        if self.settings.overlay_block1:
            result.append(BLOCKS[0])
        return result

    def clear_layout(self):
        if self.root_layout is None:
            self.root_layout = QVBoxLayout(self)
            self.root_layout.setContentsMargins(s(10, self.settings.overlay_scale), s(10, self.settings.overlay_scale), s(10, self.settings.overlay_scale), s(10, self.settings.overlay_scale))
            self.root_layout.setSpacing(s(8, self.settings.overlay_scale))
            return
        while self.root_layout.count():
            item = self.root_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def build(self):
        self.setStyleSheet(Style.overlay(self.settings.overlay_scale))
        self.clear_layout()
        self.timer_labels.clear()
        self.world_name_label = None
        self.world_timer_label = None

        if not self.settings.overlay_block1 and not self.settings.overlay_block2 and not self.settings.overlay_block3:
            self.resize(1, 1)
            return

        for block in self.selected_blocks():
            self.root_layout.addWidget(self.make_timer_bubble(block))

        if self.settings.overlay_block3:
            self.root_layout.addWidget(self.make_world_bubble())
        self.adjustSize()

    def make_timer_bubble(self, block: dict):
        sc = self.settings.overlay_scale
        bubble = QFrame()
        bubble.setObjectName("OverlayBubble")
        bubble.setFixedWidth(s(236, sc))
        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(s(12, sc), s(11, sc), s(12, sc), s(12, sc))
        layout.setSpacing(s(6, sc))

        title = QLabel(block["title"])
        title.setObjectName("OverlayTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        line = QFrame()
        line.setObjectName("OverlayLine")
        line.setFixedHeight(1)
        layout.addWidget(line)

        for name in block["names"]:
            row = QHBoxLayout()
            row.setSpacing(s(6, sc))
            name_label = QLabel(name)
            name_label.setObjectName("OverlayName")
            name_label.setFixedWidth(s(64, sc))
            row.addWidget(name_label)

            right = QVBoxLayout()
            right.setSpacing(0)
            timer = QLabel("--:--:--")
            timer.setObjectName("OverlayTimer")
            timer.setFixedWidth(s(116, sc))
            timer.setAlignment(Qt.AlignCenter)
            interval = QLabel("")
            interval.setObjectName("OverlayInterval")
            interval.setFixedWidth(s(116, sc))
            interval.setAlignment(Qt.AlignCenter)
            right.addWidget(timer)
            right.addWidget(interval)
            row.addLayout(right)

            layout.addLayout(row)
            self.timer_labels[name] = {"timer": timer, "interval": interval}
        return bubble

    def make_world_bubble(self):
        sc = self.settings.overlay_scale
        bubble = QFrame()
        bubble.setObjectName("OverlayBubble")
        bubble.setFixedWidth(s(236, sc))
        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(s(12, sc), s(11, sc), s(12, sc), s(12, sc))
        layout.setSpacing(s(6, sc))

        title = QLabel("Мировой босс")
        title.setObjectName("OverlayTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        line = QFrame()
        line.setObjectName("OverlayLine")
        line.setFixedHeight(1)
        layout.addWidget(line)

        self.world_name_label = QLabel("—")
        self.world_name_label.setObjectName("OverlayWorldName")
        self.world_name_label.setAlignment(Qt.AlignCenter)
        self.world_timer_label = QLabel("--:--:--")
        self.world_timer_label.setObjectName("OverlayWorldTimer")
        self.world_timer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.world_name_label)
        layout.addWidget(self.world_timer_label)
        return bubble

    def apply_settings(self):
        self.setWindowOpacity(self.settings.overlay_alpha)
        self.build()
        self.apply_lock()

    def apply_lock(self):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        if self.settings.overlay_locked and hasattr(Qt, "WindowTransparentForInput"):
            flags |= Qt.WindowTransparentForInput
        self.setWindowFlags(flags)
        if self.settings.overlay_enabled:
            self.show()
            QTimer.singleShot(80, lambda: set_windows_click_through(int(self.winId()), self.settings.overlay_locked))

    def update_timers(self, data: dict):
        for name, labels in self.timer_labels.items():
            values = data.get(name, {})
            labels["timer"].setText(values.get("timer", "--:--:--"))
            labels["interval"].setText(values.get("interval", ""))
            status = values.get("status", "idle")
            if status == "active":
                color = COLORS["success"]
            elif status == "hot":
                color = COLORS["timer_hot"]
            elif status == "idle":
                color = COLORS["text_disabled"]
            else:
                color = COLORS["text_main"]
            labels["timer"].setStyleSheet(f"color: {color};")

    def update_world(self, name: str, timer_text: str, status: str):
        if self.world_name_label is None or self.world_timer_label is None:
            return
        self.world_name_label.setText(name)
        self.world_timer_label.setText(timer_text)
        if status == "active":
            color = COLORS["success"]
        elif status == "hot":
            color = COLORS["timer_hot"]
        else:
            color = COLORS["text_main"]
        self.world_timer_label.setStyleSheet(f"color: {color};")

    def mousePressEvent(self, event):
        if self.settings.overlay_locked: return
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.settings.overlay_locked or self.drag_pos is None: return
        self.move(event.globalPosition().toPoint() - self.drag_pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        if not self.settings.overlay_locked:
            self.settings.overlay_pos_x = self.x()
            self.settings.overlay_pos_y = self.y()
            self.settings.save()
        self.drag_pos = None
        event.accept()