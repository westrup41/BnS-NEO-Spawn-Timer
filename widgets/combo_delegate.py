from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPainter, QColor, QFont
from utils import s
from config import COLORS

class ComboItemDelegate(QStyledItemDelegate):
    def __init__(self, scale: float, parent=None):
        super().__init__(parent)
        self.scale = scale

    def sizeHint(self, option, index):
        return QSize(s(120, self.scale), s(34, self.scale))

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        selected_flag = getattr(QStyle, "State_Selected", QStyle.StateFlag.State_Selected)
        hover_flag = getattr(QStyle, "State_MouseOver", QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & selected_flag)
        hover = bool(option.state & hover_flag)
        rect = QRectF(option.rect).adjusted(s(5, self.scale), s(3, self.scale), -s(5, self.scale), -s(3, self.scale))
        if selected:
            fill = QColor(COLORS["accent"])
            pen = QColor("#7C85FF")
            text = QColor("#FFFFFF")
        elif hover:
            fill = QColor("#2E323A")
            pen = QColor("#3F4450")
            text = QColor(COLORS["text_main"])
        else:
            fill = QColor(COLORS["bg_input"])
            pen = QColor(COLORS["bg_input"])
            text = QColor(COLORS["text_main"])
        painter.setPen(pen)
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, s(8, self.scale), s(8, self.scale))
        painter.setPen(text)
        painter.setFont(QFont("Segoe UI", s(10, self.scale), QFont.Bold))
        painter.drawText(option.rect.adjusted(s(14, self.scale), 0, -s(14, self.scale), 0), Qt.AlignVCenter | Qt.AlignLeft, str(index.data()))
        painter.restore()