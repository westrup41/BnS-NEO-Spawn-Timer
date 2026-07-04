from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor
from utils import s
from config import COLORS

class DiscordSlider(QWidget):
    valueChanged = Signal(int)

    def __init__(self, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self.scale = scale
        self._minimum = 0
        self._maximum = 100
        self._value = 0
        self._dragging = False
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(s(34, self.scale))

    def setRange(self, minimum: int, maximum: int):
        self._minimum = int(minimum)
        self._maximum = int(maximum)
        if self._maximum <= self._minimum:
            self._maximum = self._minimum + 1
        self.setValue(self._value)

    def setValue(self, value: int):
        value = max(self._minimum, min(self._maximum, int(value)))
        if value == self._value:
            self.update()
            return
        self._value = value
        self.update()
        self.valueChanged.emit(self._value)

    def value(self) -> int:
        return self._value

    def _handle_radius(self) -> int:
        return s(9, self.scale)

    def _track_rect(self):
        radius = self._handle_radius()
        left = radius + s(2, self.scale)
        right = self.width() - radius - s(2, self.scale)
        cy = self.height() / 2
        h = s(5, self.scale)
        return QRectF(left, cy - h / 2, max(1, right - left), h)

    def _value_to_x(self) -> float:
        track = self._track_rect()
        ratio = (self._value - self._minimum) / (self._maximum - self._minimum)
        return track.left() + track.width() * ratio

    def _set_from_x(self, x: float):
        track = self._track_rect()
        ratio = (x - track.left()) / track.width()
        ratio = max(0.0, min(1.0, ratio))
        value = round(self._minimum + ratio * (self._maximum - self._minimum))
        self.setValue(value)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track = self._track_rect()
        r = track.height() / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#191B20"))
        painter.drawRoundedRect(track, r, r)
        handle_x = self._value_to_x()
        filled = QRectF(track.left(), track.top(), max(0.0, handle_x - track.left()), track.height())
        painter.setBrush(QColor(COLORS["accent"]))
        painter.drawRoundedRect(filled, r, r)
        radius = self._handle_radius()
        painter.setBrush(QColor(COLORS["accent"]))
        painter.setPen(QColor(COLORS["bg_panel"]))
        painter.drawEllipse(QRectF(handle_x - radius, self.height() / 2 - radius, radius * 2, radius * 2))
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._set_from_x(event.position().x())
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._set_from_x(event.position().x())
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()