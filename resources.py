import os
import sys
import tempfile
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QFont
from PySide6.QtCore import Qt, QRectF
from config import COLORS

_ARROW_ASSET = None

def make_app_icon(size=64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    rect = QRectF(4, 4, size - 8, size - 8)
    path = QPainterPath()
    path.addRoundedRect(rect, 14, 14)
    painter.fillPath(path, QColor(COLORS["bg_input"]))
    painter.setPen(QColor(COLORS["accent"]))
    painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 14, 14)
    painter.setPen(QColor(COLORS["text_main"]))
    painter.setFont(QFont("Segoe UI", int(size * 0.22), QFont.Black))
    painter.drawText(rect, Qt.AlignCenter, "B&S")
    painter.end()
    return QIcon(pix)

def make_feedback_icon(size=64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    bubble = QRectF(size * 0.17, size * 0.18, size * 0.66, size * 0.52)
    path = QPainterPath()
    path.addRoundedRect(bubble, size * 0.16, size * 0.16)
    tail = QPainterPath()
    tail.moveTo(size * 0.39, size * 0.68)
    tail.lineTo(size * 0.31, size * 0.83)
    tail.lineTo(size * 0.52, size * 0.69)
    tail.closeSubpath()
    path = path.united(tail)
    painter.setPen(QColor(COLORS["accent"]))
    painter.setBrush(QColor(COLORS["bg_input"]))
    painter.drawPath(path)
    painter.setBrush(QColor(COLORS["text_main"]))
    painter.setPen(Qt.NoPen)
    r = size * 0.045
    for x in (0.36, 0.50, 0.64):
        painter.drawEllipse(QRectF(size * x - r, size * 0.43 - r, r * 2, r * 2))
    painter.end()
    return QIcon(pix)

def resource_path(filename: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0] or __file__)))
    return os.path.join(base, filename)

def app_icon() -> QIcon:
    icon_path = resource_path("icon.ico")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        if not icon.isNull():
            return icon
    return make_app_icon()

def combo_arrow_asset() -> str:
    global _ARROW_ASSET
    if _ARROW_ASSET and os.path.exists(_ARROW_ASSET):
        return _ARROW_ASSET.replace("\\", "/")
    folder = os.path.join(tempfile.gettempdir(), "bns_neo_timer_assets")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "combo_arrow.svg")
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="8" viewBox="0 0 12 8"><path d="M1.2 1.4L6 6.2L10.8 1.4" fill="none" stroke="#DBDEE1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    with open(path, "w", encoding="utf-8") as file:
        file.write(svg)
    _ARROW_ASSET = path
    return path.replace("\\", "/")