from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QLabel,
    QHBoxLayout,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt
from settings import AppSettings
from utils import s
from config import COLORS, BLOCKS
from styles import Style

class OverlayWindow(QWidget):
    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.drag_pos = None
        self.root_layout = None
        self.timer_labels = {}
        self.world_name_label = None
        self.world_timer_label = None
        self.event_name_label = None
        self.event_timer_label = None
        self.event_day_label = None
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.move(self.settings.overlay_pos_x, self.settings.overlay_pos_y)
        self.build()
        self.apply_lock()

    def _apply_visual_opacity(self, widget: QWidget) -> QWidget:
        """Fade the rendered overlay content without changing native window opacity.

        QWidget.setWindowOpacity() uses the Win32 layered-window opacity path.
        Combining it with a per-pixel translucent Qt window can make capture tools
        handle the same window through two different composition mechanisms.  A
        graphics effect keeps all alpha composition inside Qt's paint pass.
        """
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(max(0.0, min(1.0, float(self.settings.overlay_alpha))))
        widget.setGraphicsEffect(effect)
        return widget

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
        self.event_name_label = None
        self.event_timer_label = None
        self.event_day_label = None

        if not self.settings.overlay_block1 and not self.settings.overlay_block2 and not self.settings.overlay_block3:
            self.resize(1, 1)
            return

        for block in self.selected_blocks():
            self.root_layout.addWidget(self.make_timer_bubble(block))

        if self.settings.overlay_block2 and self.settings.event_enabled:
            self.root_layout.addWidget(self.make_event_bubble())
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
            row_frame = QFrame()
            row_frame.setObjectName("OverlayTimerRow")
            row_frame.setProperty("spawn_alert", "false")
            row = QHBoxLayout(row_frame)
            row.setContentsMargins(s(5, sc), s(3, sc), s(5, sc), s(3, sc))
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

            layout.addWidget(row_frame)
            self.timer_labels[name] = {"timer": timer, "interval": interval, "frame": row_frame}
        return self._apply_visual_opacity(bubble)

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
        return self._apply_visual_opacity(bubble)

    def make_event_bubble(self):
        sc = self.settings.overlay_scale
        bubble = QFrame()
        bubble.setObjectName("OverlayBubble")
        bubble.setFixedWidth(s(236, sc))
        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(s(12, sc), s(11, sc), s(12, sc), s(12, sc))
        layout.setSpacing(s(6, sc))
        title = QLabel("Event")
        title.setObjectName("OverlayTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        line = QFrame()
        line.setObjectName("OverlayLine")
        line.setFixedHeight(1)
        layout.addWidget(line)
        self.event_name_label = QLabel("No_Text")
        self.event_name_label.setObjectName("OverlayWorldName")
        self.event_name_label.setAlignment(Qt.AlignCenter)
        self.event_name_label.setWordWrap(True)
        self.event_timer_label = QLabel("--:--:--")
        self.event_timer_label.setObjectName("OverlayWorldTimer")
        self.event_timer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.event_name_label)
        timer_row = QHBoxLayout()
        self.event_day_label = QLabel("")
        self.event_day_label.setObjectName("OverlayDayBadge")
        self.event_day_label.setAlignment(Qt.AlignCenter)
        self.event_day_label.hide()
        timer_row.addStretch(1)
        timer_row.addWidget(self.event_day_label)
        timer_row.addWidget(self.event_timer_label)
        timer_row.addStretch(1)
        layout.addLayout(timer_row)
        return self._apply_visual_opacity(bubble)

    def apply_settings(self):
        self.build()
        self.apply_lock()

    def apply_lock(self):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        if self.settings.overlay_locked and hasattr(Qt, "WindowTransparentForInput"):
            flags |= Qt.WindowTransparentForInput
        if self.settings.overlay_locked and hasattr(Qt, "WindowDoesNotAcceptFocus"):
            flags |= Qt.WindowDoesNotAcceptFocus
        self.setAttribute(Qt.WA_ShowWithoutActivating, self.settings.overlay_locked)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.settings.overlay_locked)
        self.setWindowFlags(flags)
        if self.settings.overlay_enabled:
            self.show()

    def update_timers(self, data: dict):
        for name, labels in self.timer_labels.items():
            values = data.get(name, {})
            labels["timer"].setText(values.get("timer", "--:--:--"))
            labels["interval"].setText(values.get("interval", ""))
            status = values.get("status", "idle")
            labels["interval"].setVisible(status != "detected")
            if status == "active":
                color = COLORS["success"]
            elif status == "hot":
                color = COLORS["timer_hot"]
            elif status == "idle":
                color = COLORS["text_disabled"]
            elif status == "detected":
                color = COLORS["danger"]
            else:
                color = COLORS["text_main"]
            labels["timer"].setStyleSheet(f"color: {color};")

    def set_spawn_blink(self, channel: str, active: bool):
        labels = self.timer_labels.get(channel)
        if not labels:
            return
        frame = labels.get("frame")
        if frame is None:
            return
        frame.setProperty("spawn_alert", "true" if active else "false")
        frame.style().unpolish(frame)
        frame.style().polish(frame)
        frame.update()

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

    def update_event(self, name: str, timer_text: str, status: str, days: int = 0):
        if self.event_name_label is None or self.event_timer_label is None:
            return
        self.event_name_label.setText(name or "No_Text")
        self.event_timer_label.setText(timer_text or "--:--:--")
        if self.event_day_label is not None:
            self.event_day_label.setText(f"{days} сут.")
            self.event_day_label.setVisible(days > 0 and status not in ("appearing", "idle"))
        if status == "hot":
            color = COLORS["timer_hot"]
        elif status == "appearing":
            color = COLORS["success"]
        else:
            color = COLORS["text_main"]
        self.event_timer_label.setStyleSheet(f"color: {color};")

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
