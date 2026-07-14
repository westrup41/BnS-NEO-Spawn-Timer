import os
import sys
import tempfile
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QFont, QPen, QPolygonF
from PySide6.QtCore import Qt, QRectF, QPointF
from config import COLORS

_ARROW_ASSETS = {}

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

def make_info_icon(size=64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(COLORS["text_main"]), max(2, int(size * 0.09)))
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(size * 0.12, size * 0.12, size * 0.76, size * 0.76))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(COLORS["text_main"]))
    painter.drawEllipse(QRectF(size * 0.44, size * 0.28, size * 0.12, size * 0.12))
    painter.drawRoundedRect(QRectF(size * 0.44, size * 0.46, size * 0.12, size * 0.30), size * 0.05, size * 0.05)
    painter.end()
    return QIcon(pix)

def make_github_icon(size=64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    color = QColor(COLORS["text_main"])
    painter.setBrush(color)
    head = QPainterPath()
    head.moveTo(size * 0.23, size * 0.40)
    head.lineTo(size * 0.25, size * 0.20)
    head.lineTo(size * 0.40, size * 0.30)
    head.cubicTo(size * 0.47, size * 0.27, size * 0.53, size * 0.27, size * 0.60, size * 0.30)
    head.lineTo(size * 0.75, size * 0.20)
    head.lineTo(size * 0.77, size * 0.40)
    head.cubicTo(size * 0.86, size * 0.50, size * 0.83, size * 0.72, size * 0.68, size * 0.78)
    head.cubicTo(size * 0.58, size * 0.83, size * 0.42, size * 0.83, size * 0.32, size * 0.78)
    head.cubicTo(size * 0.17, size * 0.72, size * 0.14, size * 0.50, size * 0.23, size * 0.40)
    head.closeSubpath()
    painter.drawPath(head)
    painter.setBrush(QColor(COLORS["bg_input"]))
    painter.drawEllipse(QRectF(size * 0.34, size * 0.50, size * 0.09, size * 0.09))
    painter.drawEllipse(QRectF(size * 0.57, size * 0.50, size * 0.09, size * 0.09))
    painter.end()
    return QIcon(pix)

def make_telegram_icon(size=64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#2AABEE"))
    painter.drawEllipse(QRectF(size * 0.10, size * 0.10, size * 0.80, size * 0.80))
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawPolygon(QPolygonF([
        QPointF(size * 0.24, size * 0.48), QPointF(size * 0.76, size * 0.27),
        QPointF(size * 0.61, size * 0.75), QPointF(size * 0.47, size * 0.60),
        QPointF(size * 0.38, size * 0.69), QPointF(size * 0.39, size * 0.55),
    ]))
    painter.end()
    return QIcon(pix)

def make_discord_icon(size=64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#5865F2"))
    painter.drawRoundedRect(QRectF(size * 0.10, size * 0.15, size * 0.80, size * 0.70), size * 0.20, size * 0.20)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawEllipse(QRectF(size * 0.31, size * 0.43, size * 0.13, size * 0.13))
    painter.drawEllipse(QRectF(size * 0.56, size * 0.43, size * 0.13, size * 0.13))
    painter.end()
    return QIcon(pix)

def make_settings_icon(size=64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    color = QColor(COLORS["text_main"])
    pen = QPen(color, max(2, int(size * 0.10)), Qt.SolidLine, Qt.RoundCap)
    painter.setPen(pen)
    center = QPointF(size / 2, size / 2)
    for dx, dy in ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)):
        length = (dx * dx + dy * dy) ** 0.5
        painter.drawLine(
            QPointF(center.x() + dx / length * size * 0.25, center.y() + dy / length * size * 0.25),
            QPointF(center.x() + dx / length * size * 0.37, center.y() + dy / length * size * 0.37),
        )
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(size * 0.25, size * 0.25, size * 0.50, size * 0.50))
    painter.drawEllipse(QRectF(size * 0.42, size * 0.42, size * 0.16, size * 0.16))
    painter.end()
    return QIcon(pix)

def make_room_icon(private=False, size=64, color=None) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    icon_color = QColor(color or COLORS["text_main"])
    pen = QPen(icon_color, max(2, int(size * 0.075)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    if private:
        painter.drawEllipse(QRectF(size * .17, size * .23, size * .34, size * .34))
        painter.drawLine(QPointF(size * .45, size * .51), QPointF(size * .79, size * .78))
        painter.drawLine(QPointF(size * .66, size * .67), QPointF(size * .72, size * .60))
        painter.drawLine(QPointF(size * .73, size * .73), QPointF(size * .79, size * .66))
    else:
        globe = QRectF(size * .14, size * .14, size * .72, size * .72)
        painter.drawEllipse(globe)
        painter.drawEllipse(QRectF(size * .34, size * .14, size * .32, size * .72))
        painter.drawLine(QPointF(size * .15, size * .50), QPointF(size * .85, size * .50))
        painter.drawArc(QRectF(size * .17, size * .28, size * .66, size * .44), 0, 180 * 16)
    painter.end()
    return QIcon(pix)

def resource_path(filename: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)

def app_icon() -> QIcon:
    icon_path = resource_path("icon.ico")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        if not icon.isNull():
            return icon
    return make_app_icon()

def combo_arrow_asset() -> str:
    color = COLORS["text_main"]
    if color in _ARROW_ASSETS and os.path.exists(_ARROW_ASSETS[color]):
        return _ARROW_ASSETS[color].replace("\\", "/")
    folder = os.path.join(tempfile.gettempdir(), "bns_neo_timer_assets")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"combo_arrow_{color.lstrip('#')}.svg")
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="8" viewBox="0 0 12 8"><path d="M1.2 1.4L6 6.2L10.8 1.4" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    with open(path, "w", encoding="utf-8") as file:
        file.write(svg)
    _ARROW_ASSETS[color] = path
    return path.replace("\\", "/")

def is_admin_build() -> bool:
    return os.path.exists(resource_path("admin_build.flag"))
