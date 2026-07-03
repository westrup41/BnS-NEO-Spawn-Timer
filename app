import json
import math
import os
import platform
import shutil
import struct
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

try:
    from PySide6.QtCore import Qt, QTimer, QRectF, QSize, Signal, QUrl
    from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap, QPalette
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QTextEdit,
        QMainWindow,
        QMenu,
        QMessageBox,
        QFileDialog,
        QPushButton,
        QSizePolicy,
        QScrollArea,
        QSlider,
        QSystemTrayIcon,
        QStyledItemDelegate,
        QStyle,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise SystemExit("Нужен PySide6. Установка: pip install PySide6") from exc

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_QT_MULTIMEDIA = True
except Exception:
    QAudioOutput = None
    QMediaPlayer = None
    HAS_QT_MULTIMEDIA = False

try:
    import winsound
    HAS_SOUND = True
except Exception:
    HAS_SOUND = False

APP_VERSION = "v3.0"
SETTINGS_FILE = "boss_timer_settings.json"
USER_SOUNDS_DIR = "user_sounds"
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma"}
FEEDBACK_WEBHOOK_URL = "https://discord.com/api/webhooks/1518467190511108108/mCPyupFdNGFzwYyQRPPWE0yyewj-6_gMYSdDb4Oj5K7QnLTes63xJv1urS_eF5cARNhR"
MSK = timezone(timedelta(hours=3))

COLORS = {
    "bg_main": "#313338",
    "bg_card": "#2B2D31",
    "bg_panel": "#24262B",
    "bg_input": "#1E1F22",
    "border": "#3A3D45",
    "border_soft": "#343741",
    "text_main": "#DBDEE1",
    "text_soft": "#B5BAC1",
    "text_muted": "#949BA4",
    "text_disabled": "#6D7480",
    "accent": "#5865F2",
    "accent_hover": "#4752C4",
    "danger": "#DA373C",
    "danger_hover": "#B92B30",
    "success": "#23A559",
    "success_hover": "#1E8E4B",
    "timer_hot": "#F23F43",
}

WORLD_BOSS_SCHEDULE = [
    (0, 21, 0, "Древний дракон"),
    (1, 21, 0, "Полуденный дракон"),
    (2, 21, 0, "Священный дракон"),
    (3, 21, 0, "Небесный бивень"),
    (4, 21, 0, "Сюань У"),
    (5, 15, 0, "Полуденный дракон"),
    (5, 21, 0, "Небесный бивень"),
    (6, 15, 0, "Небесный бивень"),
    (6, 21, 0, "Священный дракон"),
]

BLOCKS = [
    {
        "key": "block1",
        "title": "Императорское древо",
        "names": ["Канал 1", "Канал 2", "Канал 3"],
        "start": timedelta(hours=2),
        "end": timedelta(hours=5),
    },
]

TIMER_DEFS = {name: block for block in BLOCKS for name in block["names"]}
ALL_TIMER_NAMES = list(TIMER_DEFS.keys())


@dataclass
class AppSettings:
    sound_enabled: bool = True
    custom_sound_path: str = ""
    sound_volume: int = 50
    discord_nickname: str = ""
    discord_webhooks: list = field(default_factory=lambda: [""] * 10)
    overlay_enabled: bool = False
    overlay_locked: bool = False
    overlay_block1: bool = False
    overlay_block2: bool = False
    overlay_block3: bool = False
    overlay_pos_x: int = 100
    overlay_pos_y: int = 100
    overlay_alpha: float = 0.90
    app_scale: float = 1.02
    overlay_scale: float = 1.15
    active_timers: dict = field(default_factory=dict)

    @classmethod
    def load(cls):
        settings = cls()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
                    data = json.load(file)
                for key in settings.__dataclass_fields__:
                    if key in data:
                        setattr(settings, key, data[key])
            except Exception:
                pass
        settings.overlay_alpha = max(0.20, min(1.00, float(settings.overlay_alpha)))
        settings.app_scale = max(0.82, min(1.22, float(settings.app_scale)))
        settings.overlay_scale = max(0.70, min(1.60, float(settings.overlay_scale)))
        if not isinstance(settings.active_timers, dict):
            settings.active_timers = {}
        if not isinstance(settings.discord_webhooks, list):
            settings.discord_webhooks = [""] * 10
        settings.discord_webhooks = (settings.discord_webhooks + [""] * 10)[:10]
        settings.discord_nickname = str(settings.discord_nickname or "")
        settings.custom_sound_path = str(settings.custom_sound_path or "")
        try:
            settings.sound_volume = max(0, min(100, int(settings.sound_volume)))
        except Exception:
            settings.sound_volume = 50
        if settings.sound_volume <= 0:
            settings.sound_enabled = False
        elif settings.sound_enabled and settings.sound_volume <= 0:
            settings.sound_volume = 50
        if not settings.overlay_enabled:
            settings.overlay_block1 = False
            settings.overlay_block3 = False
        return settings

    def save(self):
        data = {key: getattr(self, key) for key in self.__dataclass_fields__}
        with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)


def s(value: int, scale: float) -> int:
    return max(1, int(round(value * scale)))


def fmt_seconds(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def next_world_boss(now_msk=None):
    now_msk = now_msk or datetime.now(MSK)
    best_target = None
    best_name = "—"
    best_delta = timedelta(days=365)
    for weekday, hour, minute, name in WORLD_BOSS_SCHEDULE:
        days_ahead = weekday - now_msk.weekday()
        if days_ahead < 0:
            days_ahead += 7
        target = now_msk.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
        if target <= now_msk:
            target += timedelta(days=7)
        delta = target - now_msk
        if delta < best_delta:
            best_delta = delta
            best_target = target
            best_name = name
    return best_name, best_target, int(best_delta.total_seconds())


ALERT_WAV_PATH = os.path.join(tempfile.gettempdir(), "bs_neo_soft_chime_v2.wav")


def ensure_alert_wav() -> str:
    if os.path.exists(ALERT_WAV_PATH) and os.path.getsize(ALERT_WAV_PATH) > 1024:
        return ALERT_WAV_PATH

    sample_rate = 44100
    volume = 0.20
    sequence = [
        (659.25, 0.18),
        (0.0, 0.045),
        (880.00, 0.24),
    ]

    frames = []
    for frequency, duration in sequence:
        count = max(1, int(sample_rate * duration))
        for index in range(count):
            if frequency <= 0:
                sample = 0.0
            else:
                t = index / sample_rate
                fade_in = min(1.0, index / max(1, int(sample_rate * 0.010)))
                decay = math.exp(-3.2 * index / count)
                fade_out = min(1.0, (count - index) / max(1, int(sample_rate * 0.035)))
                envelope = fade_in * decay * fade_out
                fundamental = math.sin(2 * math.pi * frequency * t)
                overtone = 0.18 * math.sin(2 * math.pi * frequency * 2.0 * t)
                soft_tail = 0.08 * math.sin(2 * math.pi * frequency * 0.5 * t)
                sample = (fundamental + overtone + soft_tail) * volume * envelope
            frames.append(struct.pack("<h", max(-32767, min(32767, int(sample * 32767)))))

    with wave.open(ALERT_WAV_PATH, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(frames))
    return ALERT_WAV_PATH


_MEDIA_PLAYERS = []


def app_storage_path(*parts: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0] or __file__))
    return os.path.join(base_dir, *parts)


def resolve_audio_path(path: str) -> str:
    path = (path or "").strip().strip('"')
    if not path:
        return ""
    if os.path.isabs(path):
        return path
    return app_storage_path(path)


def copy_custom_sound_to_storage(source_path: str) -> str:
    source_path = resolve_audio_path(source_path)
    if not source_path or not os.path.exists(source_path):
        return ""
    ext = os.path.splitext(source_path)[1].lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        return ""
    folder = app_storage_path(USER_SOUNDS_DIR)
    os.makedirs(folder, exist_ok=True)
    dest_name = f"custom_timer_sound{ext}"
    dest = os.path.join(folder, dest_name)
    if os.path.abspath(source_path) != os.path.abspath(dest):
        shutil.copy2(source_path, dest)
    return os.path.join(USER_SOUNDS_DIR, dest_name)


def _finish_media_player(player):
    if getattr(player, "_finish_called", False):
        return
    player._finish_called = True
    callback = getattr(player, "_finish_callback", None)
    if callback is not None:
        try:
            callback()
        except Exception:
            pass


def _cleanup_media_player(player, call_callback: bool = True):
    try:
        if call_callback:
            _finish_media_player(player)
        if player in _MEDIA_PLAYERS:
            _MEDIA_PLAYERS.remove(player)
        player.stop()
        player.deleteLater()
    except Exception:
        pass


def _play_with_qt_multimedia(path: str, volume_percent: int = 100, on_finished=None) -> bool:
    if not HAS_QT_MULTIMEDIA:
        return False
    try:
        player = QMediaPlayer()
        audio_output = QAudioOutput()
        volume = max(0.0, min(1.0, float(volume_percent) / 100.0))
        audio_output.setVolume(volume)
        player.setAudioOutput(audio_output)
        player._audio_output = audio_output
        player._finish_callback = on_finished
        player._finish_called = False
        _MEDIA_PLAYERS.append(player)

        def finish_cleanup(*args):
            _finish_media_player(player)
            QTimer.singleShot(800, lambda: _cleanup_media_player(player, call_callback=False))

        try:
            player.mediaStatusChanged.connect(
                lambda status: finish_cleanup()
                if status in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia)
                else None
            )
            player.errorOccurred.connect(lambda *args: finish_cleanup())
        except Exception:
            pass

        player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        player.play()
        return True
    except Exception:
        return False


def _wav_duration_ms(path: str, default_ms: int = 1800) -> int:
    try:
        with wave.open(path, "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate() or 44100
            return max(300, int(frames * 1000 / rate) + 250)
    except Exception:
        return default_ms


def stop_alert_sound():
    for player in list(_MEDIA_PLAYERS):
        try:
            player.stop()
            _cleanup_media_player(player)
        except Exception:
            pass
    if HAS_SOUND:
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            try:
                winsound.PlaySound(None, 0)
            except Exception:
                pass


def play_alert(sound_enabled: bool, custom_sound_path: str = "", volume_percent: int = 50, on_finished=None) -> bool:
    try:
        volume_percent = max(0, min(100, int(volume_percent)))
    except Exception:
        volume_percent = 50
    if not sound_enabled or volume_percent <= 0:
        if on_finished is not None:
            QTimer.singleShot(0, on_finished)
        return False

    sound_path = resolve_audio_path(custom_sound_path)
    if sound_path and os.path.exists(sound_path):
        if _play_with_qt_multimedia(sound_path, volume_percent, on_finished=on_finished):
            return True
        ext = os.path.splitext(sound_path)[1].lower()
        if ext == ".wav" and HAS_SOUND:
            def wav_worker():
                try:
                    winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception:
                    pass
            threading.Thread(target=wav_worker, daemon=True).start()
            if on_finished is not None:
                QTimer.singleShot(_wav_duration_ms(sound_path), on_finished)
            return True

    default_path = ensure_alert_wav()
    if _play_with_qt_multimedia(default_path, volume_percent, on_finished=on_finished):
        return True

    if not HAS_SOUND:
        if on_finished is not None:
            QTimer.singleShot(0, on_finished)
        return False

    def worker():
        try:
            winsound.PlaySound(default_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            try:
                winsound.Beep(659, 140)
                winsound.Beep(880, 180)
            except Exception:
                pass

    threading.Thread(target=worker, daemon=True).start()
    if on_finished is not None:
        QTimer.singleShot(_wav_duration_ms(default_path), on_finished)
    return True

def post_discord_webhook(webhook_url: str, content: str, allow_everyone: bool = True):
    payload = {
        "content": content,
        "allowed_mentions": {"parse": ["everyone"] if allow_everyone else []},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "BNS-NEO-Spawn-Timer/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = getattr(response, "status", response.getcode())
            if status in (200, 204):
                return True, ""
            return False, f"HTTP {status}"
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:260]
        except Exception:
            detail = ""
        return False, f"HTTP {exc.code}: {detail}"
    except Exception as exc:
        return False, str(exc)


def set_windows_click_through(hwnd: int, enabled: bool):
    if platform.system() != "Windows":
        return
    try:
        import ctypes
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_LAYERED = 0x00080000
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enabled:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
        else:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (style & ~WS_EX_TRANSPARENT) | WS_EX_LAYERED)
    except Exception:
        pass


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


_ARROW_ASSET = None


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


class Style:
    @staticmethod
    def main(scale: float) -> str:
        arrow_path = combo_arrow_asset()
        return f"""
        QWidget {{
            background: transparent;
            color: {COLORS['text_main']};
            font-family: "Segoe UI";
            font-size: {s(11, scale)}px;
        }}
        QFrame#Shell {{
            background: {COLORS['bg_main']};
            border: 1px solid #26292F;
            border-radius: {s(14, scale)}px;
        }}
        QFrame#TopBar {{
            background: transparent;
            border: none;
        }}
        QFrame#Logo {{
            background: {COLORS['bg_input']};
            border: 1px solid {COLORS['border']};
            border-radius: {s(10, scale)}px;
        }}
        QLabel#LogoText {{
            color: {COLORS['accent']};
            font-size: {s(11, scale)}px;
            font-weight: 900;
        }}
        QLabel#AppTitle {{
            color: #FFFFFF;
            font-size: {s(14, scale)}px;
            font-weight: 850;
        }}
        QLabel#AppSubtitle {{
            color: {COLORS['text_muted']};
            font-size: {s(10, scale)}px;
            font-weight: 600;
        }}
        QFrame#Card {{
            background: {COLORS['bg_card']};
            border: 1px solid {COLORS['border']};
            border-radius: {s(14, scale)}px;
        }}
        QFrame#AccentLine {{
            background: {COLORS['accent']};
            border-radius: {s(2, scale)}px;
        }}
        QLabel#SectionTitle {{
            color: #FFFFFF;
            font-size: {s(15, scale)}px;
            font-weight: 850;
        }}
        QLabel#FormLabel {{
            color: {COLORS['text_muted']};
            font-size: {s(10, scale)}px;
            font-weight: 700;
        }}
        QFrame#TimerBubble {{
            background: {COLORS['bg_panel']};
            border: 1px solid {COLORS['border_soft']};
            border-radius: {s(12, scale)}px;
        }}
        QFrame#TimerBubble[active="true"] {{
            background: #252A33;
            border: 1px solid #4650A8;
        }}
        QLabel#TimerName {{
            color: #FFFFFF;
            font-size: {s(12, scale)}px;
            font-weight: 850;
        }}
        QLabel#TimerSub {{
            color: {COLORS['text_soft']};
            font-size: {s(11, scale)}px;
            font-weight: 750;
        }}
        QLabel#TimerValue {{
            color: {COLORS['text_main']};
            font-size: {s(18, scale)}px;
            font-weight: 900;
            letter-spacing: 0.5px;
        }}
        QLabel#WorldName {{
            color: #FFFFFF;
            font-size: {s(18, scale)}px;
            font-weight: 900;
        }}
        QLabel#WorldTimer {{
            color: {COLORS['text_main']};
            font-size: {s(34, scale)}px;
            font-weight: 900;
            letter-spacing: 1.0px;
        }}
        QLineEdit, QTextEdit, QComboBox {{
            background: {COLORS['bg_input']};
            color: {COLORS['text_main']};
            border: 1px solid {COLORS['border']};
            border-radius: {s(9, scale)}px;
            padding: {s(7, scale)}px {s(10, scale)}px;
            font-weight: 750;
            selection-background-color: {COLORS['accent']};
        }}
        QLineEdit, QTextEdit {{
            placeholder-text-color: {COLORS['text_disabled']};
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border-color: {COLORS['accent']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: {s(34, scale)}px;
            subcontrol-origin: padding;
            subcontrol-position: top right;
        }}
        QComboBox::down-arrow {{
            image: url("{arrow_path}");
            width: {s(12, scale)}px;
            height: {s(8, scale)}px;
            margin-right: {s(10, scale)}px;
        }}
        QComboBox QAbstractItemView {{
            background: {COLORS['bg_input']};
            color: {COLORS['text_main']};
            border: 1px solid {COLORS['border']};
            border-radius: {s(10, scale)}px;
            padding: {s(6, scale)}px;
            selection-background-color: transparent;
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: {s(30, scale)}px;
            padding: {s(6, scale)}px {s(12, scale)}px;
        }}
        QPushButton {{
            border: none;
            border-radius: {s(9, scale)}px;
            padding: {s(8, scale)}px {s(14, scale)}px;
            color: #FFFFFF;
            font-weight: 850;
        }}
        QPushButton#Primary {{
            background: {COLORS['accent']};
        }}
        QPushButton#Primary:hover {{
            background: {COLORS['accent_hover']};
        }}
        QPushButton#Danger {{
            background: {COLORS['danger']};
        }}
        QPushButton#Danger:hover {{
            background: {COLORS['danger_hover']};
        }}
        QPushButton#Danger:disabled,
        QPushButton#Danger:disabled:hover,
        QPushButton#Danger[cooldown="true"],
        QPushButton#Danger[cooldown="true"]:hover,
        QPushButton#Danger[no_webhook="true"],
        QPushButton#Danger[no_webhook="true"]:hover {{
            background: #3D414A;
            color: #8D939E;
            border: none;
        }}
        QPushButton#Success {{
            background: {COLORS['success']};
        }}
        QPushButton#Success:hover {{
            background: {COLORS['success_hover']};
        }}
        QPushButton#Ghost {{
            background: {COLORS['bg_input']};
            color: {COLORS['text_main']};
            border: 1px solid {COLORS['border']};
        }}
        QPushButton#Ghost:hover {{
            background: #2A2D34;
            border-color: #4A4E58;
        }}
        QPushButton#Chrome {{
            background: {COLORS['bg_input']};
            border: 1px solid {COLORS['border']};
            color: {COLORS['text_soft']};
            padding: 0;
        }}
        QPushButton#Chrome:hover {{
            background: #2A2D34;
            color: #FFFFFF;
        }}
        QPushButton#Close {{
            background: {COLORS['bg_input']};
            border: 1px solid {COLORS['border']};
            color: {COLORS['text_soft']};
            padding: 0;
            font-size: {s(14, scale)}px;
            font-weight: 900;
        }}
        QPushButton#Close:hover {{
            background: {COLORS['danger']};
            border-color: {COLORS['danger']};
            color: #FFFFFF;
        }}
        QPushButton:disabled {{
            background: #3D414A;
            color: #8D939E;
            border: none;
        }}
        QCheckBox {{
            color: {COLORS['text_main']};
            font-weight: 700;
            spacing: {s(9, scale)}px;
        }}
        QCheckBox::indicator {{
            width: {s(17, scale)}px;
            height: {s(17, scale)}px;
            border-radius: {s(5, scale)}px;
            background: {COLORS['bg_input']};
            border: 1px solid {COLORS['border']};
        }}
        QCheckBox::indicator:checked {{
            background: {COLORS['accent']};
            border: 1px solid {COLORS['accent']};
        }}
        QSlider {{
            min-height: {s(34, scale)}px;
        }}
        QSlider::groove:horizontal {{
            height: {s(5, scale)}px;
            background: #191B20;
            border: 1px solid #3B404A;
            border-radius: {s(3, scale)}px;
        }}
        QSlider::sub-page:horizontal {{
            background: {COLORS['accent']};
            border: 1px solid {COLORS['accent']};
            border-radius: {s(3, scale)}px;
        }}
        QSlider::add-page:horizontal {{
            background: #191B20;
            border: 1px solid #3B404A;
            border-radius: {s(3, scale)}px;
        }}
        QSlider::handle:horizontal {{
            width: {s(22, scale)}px;
            height: {s(22, scale)}px;
            margin: {s(-10, scale)}px 0;
            border-radius: {s(11, scale)}px;
            background: {COLORS['accent']};
            border: {s(3, scale)}px solid #252A33;
        }}
        QSlider::handle:horizontal:hover {{
            background: #6B74FF;
            border: {s(3, scale)}px solid #3C427A;
        }}
        QFrame#SettingsGroup {{
            background: {COLORS['bg_panel']};
            border: 1px solid {COLORS['border_soft']};
            border-radius: {s(12, scale)}px;
        }}
        QScrollArea#SettingsScroll {{
            background: transparent;
            border: none;
        }}
        QWidget#SettingsScrollContent {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: #191B20;
            width: {s(12, scale)}px;
            margin: {s(2, scale)}px 0 {s(2, scale)}px {s(4, scale)}px;
            border-radius: {s(6, scale)}px;
        }}
        QScrollBar::handle:vertical {{
            background: #5865F2;
            border-radius: {s(6, scale)}px;
            min-height: {s(42, scale)}px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: #6B74FF;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
            background: transparent;
            border: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        QLabel#GroupTitle {{
            color: #FFFFFF;
            font-size: {s(12, scale)}px;
            font-weight: 900;
        }}
        """

    @staticmethod
    def overlay(scale: float) -> str:
        return f"""
        QWidget {{
            background: transparent;
            color: {COLORS['text_main']};
            font-family: "Segoe UI";
        }}
        QFrame#OverlayBubble {{
            background: rgba(43,45,49,0.94);
            border: 1px solid rgba(76,82,96,0.95);
            border-radius: {s(18, scale)}px;
        }}
        QLabel#OverlayTitle {{
            color: {COLORS['accent']};
            font-size: {s(13, scale)}px;
            font-weight: 900;
        }}
        QFrame#OverlayLine {{
            background: rgba(148,155,164,0.30);
        }}
        QLabel#OverlayName {{
            color: #FFFFFF;
            font-size: {s(12, scale)}px;
            font-weight: 850;
        }}
        QLabel#OverlayInterval {{
            color: {COLORS['text_soft']};
            font-size: {s(10, scale)}px;
            font-weight: 750;
        }}
        QLabel#OverlayTimer {{
            color: {COLORS['text_main']};
            font-size: {s(16, scale)}px;
            font-weight: 900;
            letter-spacing: 0.2px;
        }}
        QLabel#OverlayWorldName {{
            color: #FFFFFF;
            font-size: {s(14, scale)}px;
            font-weight: 900;
        }}
        QLabel#OverlayWorldTimer {{
            color: {COLORS['text_main']};
            font-size: {s(24, scale)}px;
            font-weight: 900;
            letter-spacing: 0.8px;
        }}
        """


def system_tray_menu_stylesheet() -> str:
    return """
    QMenu {
        background-color: #F0F0F0;
        color: #000000;
        border: 1px solid #A0A0A0;
        padding: 1px 0;
        font-family: "Segoe UI";
        font-size: 9pt;
    }
    QMenu::item {
        background-color: transparent;
        padding: 4px 34px 4px 28px;
        min-width: 92px;
    }
    QMenu::item:selected {
        background-color: #91C9F7;
        color: #000000;
    }
    QMenu::separator {
        height: 1px;
        background: #D0D0D0;
        margin: 3px 0;
    }
    """


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

        self.discord_btn = QPushButton("🚨")
        self.discord_btn.setObjectName("Danger")
        self.discord_btn.setToolTip("Отправить Discord-оповещение")
        self.discord_btn.setFixedSize(s(40, sc), s(36, sc))
        self.discord_btn.clicked.connect(self.send_discord_alert)
        layout.addWidget(self.discord_btn)

        self.discord_cooldown_remaining = 0
        self.discord_cooldown_timer = QTimer(self)
        self.discord_cooldown_timer.setInterval(1000)
        self.discord_cooldown_timer.timeout.connect(self.update_discord_cooldown)
        self.refresh_discord_button_visual()

    def send_discord_alert(self):
        if self.discord_cooldown_remaining > 0:
            return
        sent_started = self.app.send_discord_alert(self.name)
        if sent_started:
            self.start_discord_cooldown(30)

    def refresh_discord_button_visual(self):
        cooldown_active = self.discord_cooldown_remaining > 0
        no_webhook = not self.app.has_discord_webhooks()
        self.discord_btn.setProperty("cooldown", "true" if cooldown_active else "false")
        self.discord_btn.setProperty("no_webhook", "true" if (no_webhook and not cooldown_active) else "false")
        self.discord_btn.setEnabled(not cooldown_active)
        self.discord_btn.setText("🚨")
        self.discord_btn.style().unpolish(self.discord_btn)
        self.discord_btn.style().polish(self.discord_btn)
        self.discord_btn.update()

    def set_discord_cooldown_visual(self, active: bool):
        self.discord_cooldown_remaining = max(1, self.discord_cooldown_remaining) if active else 0
        self.refresh_discord_button_visual()

    def start_discord_cooldown(self, seconds: int):
        self.discord_cooldown_remaining = max(0, int(seconds))
        if self.discord_cooldown_remaining > 0:
            self.refresh_discord_button_visual()
            self.discord_cooldown_timer.start()
        else:
            self.discord_cooldown_timer.stop()
            self.refresh_discord_button_visual()

    def update_discord_cooldown(self):
        self.discord_cooldown_remaining -= 1
        if self.discord_cooldown_remaining <= 0:
            self.discord_cooldown_timer.stop()
            self.discord_cooldown_remaining = 0
        self.refresh_discord_button_visual()

    def toggle(self):
        if self.name in self.app.active_timers:
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
        self.timer_label.setText(values.get("timer", "--:--:--"))
        if status == "active":
            color = COLORS["success"]
        elif status == "hot":
            color = COLORS["timer_hot"]
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
            QMessageBox.critical(self, "Ошибка", "Неверное время")
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


class WorldBossBlock(QFrame):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setObjectName("Card")
        sc = app.settings.app_scale
        layout = QVBoxLayout(self)
        layout.setContentsMargins(s(16, sc), s(2, sc), s(16, sc), s(16, sc))
        layout.setSpacing(s(6, sc))

        title = QLabel("Мировой босс")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        bubble = QFrame()
        bubble.setObjectName("TimerBubble")
        bubble_layout = QHBoxLayout(bubble)
        bubble_layout.setContentsMargins(s(18, sc), s(15, sc), s(18, sc), s(15, sc))
        bubble_layout.setSpacing(s(12, sc))

        left = QVBoxLayout()
        left.setSpacing(2)
        self.name_label = QLabel("—")
        self.name_label.setObjectName("WorldName")
        left.addWidget(self.name_label)
        bubble_layout.addLayout(left, 1)

        self.timer_label = QLabel("--:--:--")
        self.timer_label.setObjectName("WorldTimer")
        self.timer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bubble_layout.addWidget(self.timer_label)
        layout.addWidget(bubble)

    def set_state(self, name: str, timer_text: str, status: str):
        self.name_label.setText(name)
        self.timer_label.setText(timer_text)
        if status == "active":
            color = COLORS["success"]
        elif status == "hot":
            color = COLORS["timer_hot"]
        else:
            color = COLORS["text_main"]
        self.timer_label.setStyleSheet(f"color: {color};")


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
        if self.settings.overlay_locked:
            return
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.settings.overlay_locked or self.drag_pos is None:
            return
        self.move(event.globalPosition().toPoint() - self.drag_pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        if not self.settings.overlay_locked:
            self.settings.overlay_pos_x = self.x()
            self.settings.overlay_pos_y = self.y()
            self.settings.save()
        self.drag_pos = None
        event.accept()


class FeedbackDialog(QDialog):
    feedback_result = Signal(bool, str)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet(Style.main(parent.settings.app_scale))
        self.setFixedSize(s(470, parent.settings.app_scale), s(420, parent.settings.app_scale))
        self.feedback_result.connect(self.on_feedback_result)
        self.build()

    def build(self):
        sc = self.parent_window.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, sc), s(18, sc), s(22, sc), s(20, sc))
        layout.setSpacing(s(12, sc))

        top = QHBoxLayout()
        title = QLabel("Отзыв")
        title.setObjectName("SectionTitle")
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.clicked.connect(self.reject)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)
        layout.addLayout(top)

        nick_label = QLabel("Никнейм")
        nick_label.setObjectName("FormLabel")
        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("")
        self.nickname_input.setText(self.parent_window.settings.discord_nickname.strip())
        layout.addWidget(nick_label)
        layout.addWidget(self.nickname_input)

        text_label = QLabel("Что можно изменить/улучшить?")
        text_label.setObjectName("FormLabel")
        self.feedback_text = QTextEdit()
        self.feedback_text.setMinimumHeight(s(160, sc))
        layout.addWidget(text_label)
        layout.addWidget(self.feedback_text, 1)

        buttons = QHBoxLayout()
        self.send_btn = QPushButton("Отправить")
        self.send_btn.setObjectName("Primary")
        self.send_btn.clicked.connect(self.send_feedback)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("Ghost")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(self.send_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def send_feedback(self):
        nickname = self.nickname_input.text().strip() or "Без ника"
        message = self.feedback_text.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Отзыв", "Напиши отзыв.")
            return
        if len(nickname) > 80:
            nickname = nickname[:80]
        if len(message) > 1700:
            message = message[:1700] + "…"
        content = f"Версия: {APP_VERSION}\nНик: {nickname}\nФидбэк: {message}"
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Отправляю...")

        def worker():
            ok, error = post_discord_webhook(FEEDBACK_WEBHOOK_URL, content, allow_everyone=False)
            self.feedback_result.emit(ok, error)

        threading.Thread(target=worker, daemon=True).start()

    def on_feedback_result(self, ok: bool, error: str):
        if ok:
            self.parent_window.notify_signal.emit("Отзыв", "Отзыв отправлен успешно.")
            self.accept()
            return
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Отправить")
        self.parent_window.notify_signal.emit("Отзыв", "Не удалось отправить отзыв.")
        QMessageBox.warning(self, "Отзыв", "Не удалось отправить отзыв.")

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


class WebhooksDialog(QDialog):
    def __init__(self, parent, urls):
        super().__init__(parent)
        self.parent_dialog = parent
        self.urls = (list(urls) + [""] * 10)[:10]
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setStyleSheet(Style.main(parent.settings.app_scale))
        self.setFixedSize(s(590, parent.settings.app_scale), s(590, parent.settings.app_scale))
        self.inputs = []
        self.build()

    def build(self):
        sc = self.parent_dialog.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, sc), s(18, sc), s(22, sc), s(20, sc))
        layout.setSpacing(s(10, sc))

        top = QHBoxLayout()
        title = QLabel("Discord вебхуки")
        title.setObjectName("SectionTitle")
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.clicked.connect(self.reject)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)
        layout.addLayout(top)


        for index in range(10):
            row = QHBoxLayout()
            row.setSpacing(s(8, sc))
            label = QLabel(f"#{index + 1}")
            label.setObjectName("FormLabel")
            label.setFixedWidth(s(26, sc))
            edit = QLineEdit()
            edit.setPlaceholderText("https://discord.com/api/webhooks/...")
            edit.setText(self.urls[index])
            self.inputs.append(edit)
            row.addWidget(label)
            row.addWidget(edit)
            layout.addLayout(row)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("Success")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("Ghost")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addStretch(1)
        layout.addLayout(buttons)

    def get_urls(self):
        return [edit.text().strip() for edit in self.inputs][:10]

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


class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.settings = parent.settings
        self.drag_pos = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet(Style.main(self.settings.app_scale))
        self.setFixedSize(s(430, self.settings.app_scale), s(790, self.settings.app_scale))
        self.build()

    def build(self):
        sc = self.settings.app_scale
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        shell = QFrame()
        shell.setObjectName("Shell")
        root.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(s(22, sc), s(18, sc), s(22, sc), s(20, sc))
        layout.setSpacing(s(12, sc))

        top = QHBoxLayout()
        title = QLabel("Настройки")
        title.setObjectName("SectionTitle")
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(34, sc), s(32, sc))
        close.clicked.connect(self.reject)
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(close)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setViewportMargins(0, 0, s(6, sc), 0)
        scroll_widget = QWidget()
        scroll_widget.setObjectName("SettingsScrollContent")
        content_layout = QVBoxLayout(scroll_widget)
        content_layout.setContentsMargins(0, 0, s(8, sc), 0)
        content_layout.setSpacing(s(12, sc))

        sound_group = QFrame()
        sound_group.setObjectName("SettingsGroup")
        sound_layout = QVBoxLayout(sound_group)
        sound_layout.setContentsMargins(s(14, sc), s(2, sc), s(14, sc), s(12, sc))
        sound_layout.setSpacing(s(6, sc))
        sound_title = QLabel("Звук")
        sound_title.setObjectName("GroupTitle")
        sound_layout.addWidget(sound_title)
        sound_layout.addSpacing(s(8, sc))
        self.sound = QCheckBox("Звуковое оповещение за 10 минут до события")
        self.sound.setChecked(self.settings.sound_enabled)
        sound_layout.addWidget(self.sound)

        sound_layout.addSpacing(s(8, sc))
        self.sound_volume_label = QLabel()
        self.sound_volume_label.setObjectName("FormLabel")
        self.sound_volume_slider = DiscordSlider(sc)
        self.sound_volume_slider.setRange(0, 100)
        self.sound_volume_slider.setValue(int(self.settings.sound_volume if self.settings.sound_enabled else 0))
        self.sound.toggled.connect(self.on_sound_toggled)
        self.sound_volume_slider.valueChanged.connect(self.on_sound_volume_changed)
        sound_layout.addWidget(self.sound_volume_label)
        sound_layout.addWidget(self.sound_volume_slider)

        sound_layout.addSpacing(s(8, sc))
        custom_sound_label = QLabel("Кастомный звук оповещения")
        custom_sound_label.setObjectName("FormLabel")
        custom_sound_label.setWordWrap(True)
        sound_layout.addWidget(custom_sound_label)
        sound_row = QHBoxLayout()
        sound_row.setSpacing(s(8, sc))
        self.custom_sound_value = self.settings.custom_sound_path
        self.test_sound_active = False
        self.browse_sound_btn = QPushButton("Выбрать")
        self.browse_sound_btn.setObjectName("Ghost")
        self.browse_sound_btn.setFixedWidth(s(100, sc))
        self.browse_sound_btn.clicked.connect(self.choose_custom_sound)
        self.clear_sound_btn = QPushButton("×")
        self.clear_sound_btn.setObjectName("Ghost")
        self.clear_sound_btn.setFixedWidth(s(34, sc))
        self.clear_sound_btn.clicked.connect(self.clear_custom_sound)
        self.test_sound_btn = QPushButton("Проверить")
        self.test_sound_btn.setObjectName("Primary")
        self.test_sound_btn.setFixedWidth(s(108, sc))
        self.test_sound_btn.clicked.connect(self.test_custom_sound)
        sound_row.addWidget(self.browse_sound_btn)
        sound_row.addWidget(self.clear_sound_btn)
        sound_row.addWidget(self.test_sound_btn)
        sound_row.addStretch(1)
        sound_layout.addLayout(sound_row)
        self.update_custom_sound_button()
        content_layout.addWidget(sound_group)

        discord_group = QFrame()
        discord_group.setObjectName("SettingsGroup")
        discord_layout = QVBoxLayout(discord_group)
        discord_layout.setContentsMargins(s(14, sc), s(12, sc), s(14, sc), s(12, sc))
        discord_layout.setSpacing(s(8, sc))
        discord_title = QLabel("Discord-оповещения")
        discord_title.setObjectName("GroupTitle")
        discord_layout.addWidget(discord_title)

        nick_label = QLabel("Никнейм отправителя")
        nick_label.setObjectName("FormLabel")
        self.discord_nickname = QLineEdit()
        self.discord_nickname.setPlaceholderText("Например: Westrup")
        self.discord_nickname.setText(self.settings.discord_nickname)
        discord_layout.addWidget(nick_label)
        discord_layout.addWidget(self.discord_nickname)

        webhook_row = QHBoxLayout()
        webhook_row.setSpacing(s(8, sc))
        self.webhooks_btn = QPushButton("Вебхуки")
        self.webhooks_btn.setObjectName("Primary")
        self.webhooks_btn.setFixedWidth(s(112, sc))
        self.webhooks_btn.clicked.connect(self.open_webhooks_dialog)
        webhook_row.addWidget(self.webhooks_btn)
        webhook_row.addStretch(1)
        discord_layout.addLayout(webhook_row)
        self.discord_webhooks = (list(self.settings.discord_webhooks) + [""] * 10)[:10]
        content_layout.addWidget(discord_group)

        ui_group = QFrame()
        ui_group.setObjectName("SettingsGroup")
        ui_layout = QVBoxLayout(ui_group)
        ui_layout.setContentsMargins(s(14, sc), s(12, sc), s(14, sc), s(12, sc))
        ui_layout.setSpacing(s(6, sc))
        ui_title = QLabel("Интерфейс")
        ui_title.setObjectName("GroupTitle")
        ui_layout.addWidget(ui_title)
        ui_layout.addSpacing(s(8, sc))

        self.app_scale_label = QLabel()
        self.app_scale_label.setObjectName("FormLabel")
        self.app_scale_slider = DiscordSlider(sc)
        self.app_scale_slider.setRange(82, 122)
        self.app_scale_slider.setValue(int(self.settings.app_scale * 100))
        self.app_scale_slider.valueChanged.connect(self.update_labels)
        ui_layout.addWidget(self.app_scale_label)
        ui_layout.addWidget(self.app_scale_slider)
        content_layout.addWidget(ui_group)

        overlay_group = QFrame()
        overlay_group.setObjectName("SettingsGroup")
        overlay_layout = QVBoxLayout(overlay_group)
        overlay_layout.setContentsMargins(s(14, sc), s(12, sc), s(14, sc), s(12, sc))
        overlay_layout.setSpacing(s(6, sc))
        overlay_title = QLabel("Оверлей")
        overlay_title.setObjectName("GroupTitle")
        overlay_layout.addWidget(overlay_title)
        overlay_layout.addSpacing(s(8, sc))

        self.overlay = QCheckBox("Включить оверлей:")
        self.overlay.setChecked(self.settings.overlay_enabled)
        self.block1 = QCheckBox("Императорское древо")
        self.block1.setChecked(self.settings.overlay_block1)
        self.block3 = QCheckBox("Мировой босс")
        self.block3.setChecked(self.settings.overlay_block3)
        self.lock = QCheckBox("Закрепить оверлей")
        self.lock.setChecked(self.settings.overlay_locked)

        overlay_layout.addWidget(self.overlay)
        overlay_layout.addLayout(self._indented_checkbox(self.block1, sc))
        overlay_layout.addLayout(self._indented_checkbox(self.block3, sc))
        overlay_layout.addWidget(self.lock)

        self.overlay.toggled.connect(self.on_overlay_toggled)
        self.block1.toggled.connect(self.on_overlay_block_toggled)
        self.block3.toggled.connect(self.on_overlay_block_toggled)

        overlay_layout.addSpacing(s(8, sc))
        self.alpha_label = QLabel()
        self.alpha_label.setObjectName("FormLabel")
        self.alpha_slider = DiscordSlider(sc)
        self.alpha_slider.setRange(20, 100)
        self.alpha_slider.setValue(int(self.settings.overlay_alpha * 100))
        self.alpha_slider.valueChanged.connect(self.update_labels)
        overlay_layout.addWidget(self.alpha_label)
        overlay_layout.addWidget(self.alpha_slider)

        self.overlay_scale_label = QLabel()
        self.overlay_scale_label.setObjectName("FormLabel")
        self.overlay_scale_slider = DiscordSlider(sc)
        self.overlay_scale_slider.setRange(70, 160)
        self.overlay_scale_slider.setValue(int(self.settings.overlay_scale * 100))
        self.overlay_scale_slider.valueChanged.connect(self.update_labels)
        overlay_layout.addWidget(self.overlay_scale_label)
        overlay_layout.addWidget(self.overlay_scale_slider)
        content_layout.addWidget(overlay_group)
        content_layout.addStretch(1)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        apply_btn = QPushButton("Применить")
        apply_btn.setObjectName("Primary")
        apply_btn.clicked.connect(self.apply)
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("Success")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("Ghost")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(apply_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        self.update_labels()

    def on_sound_toggled(self, checked: bool):
        if checked:
            if self.sound_volume_slider.value() <= 0:
                self.sound_volume_slider.setValue(50)
        else:
            if self.sound_volume_slider.value() != 0:
                self.sound_volume_slider.setValue(0)
        self.update_labels()

    def on_sound_volume_changed(self, value: int):
        self.sound.blockSignals(True)
        self.sound.setChecked(value > 0)
        self.sound.blockSignals(False)
        self.update_labels()

    def update_custom_sound_button(self):
        selected = bool(getattr(self, "custom_sound_value", ""))
        self.browse_sound_btn.setText("Выбрано" if selected else "Выбрать")
        self.browse_sound_btn.setObjectName("Success" if selected else "Ghost")
        self.browse_sound_btn.style().unpolish(self.browse_sound_btn)
        self.browse_sound_btn.style().polish(self.browse_sound_btn)
        self.clear_sound_btn.setEnabled(selected)

    def _finish_test_sound(self):
        if not getattr(self, "test_sound_active", False):
            return
        self.test_sound_active = False
        self.test_sound_btn.setText("Проверить")
        self.test_sound_btn.setObjectName("Primary")
        self.test_sound_btn.style().unpolish(self.test_sound_btn)
        self.test_sound_btn.style().polish(self.test_sound_btn)

    def test_custom_sound(self):
        if getattr(self, "test_sound_active", False):
            stop_alert_sound()
            self._finish_test_sound()
            return
        stop_alert_sound()
        volume = self.sound_volume_slider.value()
        if volume <= 0:
            return
        self.test_sound_active = True
        self.test_sound_btn.setText("Стоп")
        self.test_sound_btn.setObjectName("Danger")
        self.test_sound_btn.style().unpolish(self.test_sound_btn)
        self.test_sound_btn.style().polish(self.test_sound_btn)
        started = play_alert(True, self.custom_sound_value, volume, on_finished=self._finish_test_sound)
        if not started:
            self._finish_test_sound()

    def clear_custom_sound(self):
        self.custom_sound_value = ""
        self.update_custom_sound_button()

    def choose_custom_sound(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать звук оповещения",
            "",
            "Аудиофайлы (*.wav *.mp3 *.ogg *.flac *.m4a *.aac *.wma);;Все файлы (*.*)",
        )
        if not path:
            return
        try:
            stored_path = copy_custom_sound_to_storage(path)
            if not stored_path:
                QMessageBox.warning(self, "Звук", "Не удалось скопировать файл.")
                return
            self.custom_sound_value = stored_path
            self.update_custom_sound_button()
        except Exception as exc:
            QMessageBox.warning(self, "Звук", f"Не удалось скопировать файл:\n{exc}")

    def update_webhooks_count(self):
        return

    def open_webhooks_dialog(self):
        dialog = WebhooksDialog(self, self.discord_webhooks)
        geo = self.geometry()
        dialog.move(geo.x() + s(18, self.settings.app_scale), geo.y() + s(38, self.settings.app_scale))
        if dialog.exec() == QDialog.Accepted:
            self.discord_webhooks = dialog.get_urls()
            self.update_webhooks_count()

    def _indented_checkbox(self, checkbox, sc):
        row = QHBoxLayout()
        row.setContentsMargins(s(24, sc), 0, 0, 0)
        row.addWidget(checkbox)
        row.addStretch(1)
        return row

    def on_overlay_toggled(self, checked: bool):
        if not checked:
            self.block1.blockSignals(True)
            self.block3.blockSignals(True)
            self.block1.setChecked(False)
            self.block3.setChecked(False)
            self.block1.blockSignals(False)
            self.block3.blockSignals(False)

    def on_overlay_block_toggled(self, checked: bool):
        if checked and not self.overlay.isChecked():
            self.overlay.setChecked(True)
            return
        if not self.block1.isChecked() and not self.block3.isChecked() and self.overlay.isChecked():
            self.overlay.setChecked(False)

    def _range_percent(self, value: int, minimum: int, maximum: int) -> int:
        if maximum <= minimum:
            return 0
        return round((value - minimum) * 100 / (maximum - minimum))

    def update_labels(self):
        app_percent = self._range_percent(self.app_scale_slider.value(), 82, 122)
        overlay_percent = self._range_percent(self.overlay_scale_slider.value(), 70, 160)
        self.sound_volume_label.setText(f"Громкость оповещения: {self.sound_volume_slider.value()}%")
        self.alpha_label.setText(f"Прозрачность оверлея: {self.alpha_slider.value()}%")
        self.app_scale_label.setText(f"Размер программы: {app_percent}%")
        self.overlay_scale_label.setText(f"Размер оверлея: {overlay_percent}%")

    def apply(self):
        volume_value = max(0, min(100, int(self.sound_volume_slider.value())))
        self.settings.sound_volume = volume_value
        self.settings.sound_enabled = self.sound.isChecked() and volume_value > 0
        custom_sound_value = str(getattr(self, "custom_sound_value", "")).strip()
        if custom_sound_value and os.path.exists(resolve_audio_path(custom_sound_value)):
            try:
                custom_sound_value = copy_custom_sound_to_storage(custom_sound_value) or custom_sound_value
            except Exception:
                pass
        self.settings.custom_sound_path = custom_sound_value
        self.settings.discord_nickname = self.discord_nickname.text().strip()
        self.settings.discord_webhooks = (list(self.discord_webhooks) + [""] * 10)[:10]
        block1_enabled = self.block1.isChecked()
        block3_enabled = self.block3.isChecked()
        overlay_enabled = self.overlay.isChecked() and (block1_enabled or block3_enabled)
        self.settings.overlay_enabled = overlay_enabled
        self.settings.overlay_locked = self.lock.isChecked()
        self.settings.overlay_block1 = block1_enabled if overlay_enabled else False
        self.settings.overlay_block2 = False
        self.settings.overlay_block3 = block3_enabled if overlay_enabled else False
        self.settings.overlay_alpha = self.alpha_slider.value() / 100
        self.settings.app_scale = self.app_scale_slider.value() / 100
        self.settings.overlay_scale = self.overlay_scale_slider.value() / 100
        self.settings.save()
        self.app.apply_visual_settings(rebuild=True)
        self.app.apply_overlay_settings()

    def save_and_close(self):
        self.apply()
        self.accept()

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


class MainWindow(QMainWindow):
    notify_signal = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.settings = AppSettings.load()
        self.active_timers = {}
        self.alerted = set()
        self.rows = {}
        self.overlay_window = None
        self.tray = None
        self.drag_pos = None
        self.world_name = "—"
        self.world_timer = "--:--:--"
        self.world_status = "normal"
        self.world_alerted_target = None
        self.discord_alert_last_sent = {}
        self.notify_signal.connect(self.show_notification)

        self.setWindowTitle("B&S NEO Spawn Timer")
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.restore_active_timers()
        self.build_ui()
        self.apply_visual_settings(rebuild=False)
        self.setup_tray()

        self.ticker = QTimer(self)
        self.ticker.timeout.connect(self.tick)
        self.ticker.start(1000)
        self.tick()
        if self.settings.overlay_enabled:
            QTimer.singleShot(150, self.apply_overlay_settings)

    def target_size(self):
        scale = self.settings.app_scale
        return s(700, scale), s(616, scale)

    def build_ui(self):
        self.rows = {}
        sc = self.settings.app_scale
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.shell = QFrame()
        self.shell.setObjectName("Shell")
        root_layout.addWidget(self.shell)
        self.setCentralWidget(root)

        layout = QVBoxLayout(self.shell)
        layout.setContentsMargins(s(16, sc), s(14, sc), s(16, sc), s(16, sc))
        layout.setSpacing(s(12, sc))

        top = QFrame()
        top.setObjectName("TopBar")
        top.setFixedHeight(s(42, sc))
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(s(10, sc))

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("B&S NEO")
        title.setObjectName("AppTitle")
        title.setFixedHeight(s(18, sc))
        subtitle = QLabel(f"Spawn Timer {APP_VERSION} by westrup")
        subtitle.setObjectName("AppSubtitle")
        subtitle.setFixedHeight(s(15, sc))
        titles.addStretch(1)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        titles.addStretch(1)

        feedback_btn = QPushButton("")
        feedback_btn.setObjectName("Ghost")
        feedback_btn.setIcon(make_feedback_icon(s(28, sc)))
        feedback_btn.setFixedSize(s(42, sc), s(34, sc))
        feedback_btn.clicked.connect(self.open_feedback)

        settings_btn = QPushButton("Настройки")
        settings_btn.setObjectName("Ghost")
        settings_btn.setFixedHeight(s(34, sc))
        settings_btn.setMinimumWidth(s(96, sc))
        settings_btn.clicked.connect(self.open_settings)

        minimize = QPushButton("—")
        minimize.setObjectName("Chrome")
        minimize.setFixedSize(s(38, sc), s(34, sc))
        minimize.clicked.connect(self.showMinimized)
        close = QPushButton("×")
        close.setObjectName("Close")
        close.setFixedSize(s(38, sc), s(34, sc))
        close.clicked.connect(self.handle_close_button)

        top_layout.addLayout(titles)
        top_layout.addStretch(1)
        top_layout.addWidget(feedback_btn)
        top_layout.addWidget(settings_btn)
        top_layout.addWidget(minimize)
        top_layout.addWidget(close)
        layout.addWidget(top)

        for block in BLOCKS:
            timer_block = TimerBlock(self, block, settings_button=False)
            layout.addWidget(timer_block)

        self.world_block = WorldBossBlock(self)
        layout.addWidget(self.world_block)

        top.mousePressEvent = self.mousePressEvent
        top.mouseMoveEvent = self.mouseMoveEvent
        top.mouseReleaseEvent = self.mouseReleaseEvent

    def has_discord_webhooks(self) -> bool:
        return any(str(url).strip() for url in self.settings.discord_webhooks)

    def refresh_discord_buttons(self):
        for row in self.rows.values():
            if hasattr(row, "refresh_discord_button_visual"):
                row.refresh_discord_button_visual()

    def apply_visual_settings(self, rebuild=False):
        if rebuild:
            self.build_ui()
        QApplication.instance().setStyleSheet(Style.main(self.settings.app_scale))
        width, height = self.target_size()
        self.setFixedSize(width, height)
        self.tick()
        self.refresh_discord_buttons()

    def restore_active_timers(self):
        now = datetime.now()
        cleaned = False
        for name, iso_value in list(self.settings.active_timers.items()):
            if name not in TIMER_DEFS:
                del self.settings.active_timers[name]
                cleaned = True
                continue
            try:
                base = datetime.fromisoformat(iso_value)
                if now - base < timedelta(hours=12):
                    self.active_timers[name] = base
                else:
                    del self.settings.active_timers[name]
                    cleaned = True
            except Exception:
                del self.settings.active_timers[name]
                cleaned = True
        if cleaned:
            self.settings.save()

    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("B&S NEO Spawn Timer")
        menu = QMenu()
        show_action = QAction("Открыть", self)
        show_action.triggered.connect(self.show_from_tray)
        quit_action = QAction("Выйти", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_from_tray() if reason == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()

    def start_timer(self, name: str, base_time: datetime):
        stop_alert_sound()
        self.active_timers[name] = base_time
        self.alerted.discard(name)
        self.settings.active_timers[name] = base_time.isoformat()
        self.settings.save()
        self.tick()

    def stop_timer(self, name: str):
        stop_alert_sound()
        self.active_timers.pop(name, None)
        self.alerted.discard(name)
        self.settings.active_timers.pop(name, None)
        self.settings.save()
        self.tick()

    def calculate_timer_data(self):
        now = datetime.now()
        result = {}
        for name in ALL_TIMER_NAMES:
            block = TIMER_DEFS[name]
            if name not in self.active_timers:
                result[name] = {"timer": "--:--:--", "interval": "", "status": "idle", "active": False}
                continue
            base = self.active_timers[name]
            start = base + block["start"]
            end = base + block["end"]
            interval_text = f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"
            seconds = int((start - now).total_seconds())
            if seconds <= 0:
                result[name] = {"timer": "Появление", "interval": interval_text, "status": "active", "active": True}
            elif seconds <= 600:
                result[name] = {"timer": fmt_seconds(seconds), "interval": interval_text, "status": "hot", "active": True}
            else:
                result[name] = {"timer": fmt_seconds(seconds), "interval": interval_text, "status": "normal", "active": True}
            if 0 < seconds <= 600 and name not in self.alerted:
                play_alert(self.settings.sound_enabled, self.settings.custom_sound_path, self.settings.sound_volume)
                self.alerted.add(name)
        return result

    def tick(self):
        if not self.rows:
            return
        data = self.calculate_timer_data()
        for name, values in data.items():
            if name in self.rows:
                self.rows[name].set_state(values)

        boss_name, world_target, seconds = next_world_boss()
        self.world_name = boss_name
        self.world_timer = fmt_seconds(seconds)
        self.world_status = "hot" if seconds <= 600 else "normal"
        world_alert_key = world_target.isoformat() if world_target else None
        if world_alert_key and 0 < seconds <= 600 and self.world_alerted_target != world_alert_key:
            play_alert(self.settings.sound_enabled, self.settings.custom_sound_path, self.settings.sound_volume)
            self.world_alerted_target = world_alert_key
        if hasattr(self, "world_block"):
            self.world_block.set_state(self.world_name, self.world_timer, self.world_status)

        if self.overlay_window is not None and self.overlay_window.isVisible():
            self.overlay_window.update_timers(data)
            self.overlay_window.update_world(self.world_name, self.world_timer, self.world_status)

    def show_notification(self, title: str, message: str):
        if self.tray is not None and self.tray.isVisible():
            self.tray.showMessage(title, message, app_icon(), 3500)
        else:
            print(f"{title}: {message}")

    def send_discord_alert(self, channel_name: str):
        now = datetime.now()
        last_sent = self.discord_alert_last_sent.get(channel_name)
        if last_sent and (now - last_sent).total_seconds() < 30:
            return False

        webhooks = [url.strip() for url in self.settings.discord_webhooks if str(url).strip()]
        if not webhooks:
            self.show_notification("Discord", "Добавь хотя бы один вебхук в настройках.")
            return False

        nickname = self.settings.discord_nickname.strip() or "Игрок"
        content = f"@everyone 🚨 **Императорское древо**\nКанал: **{channel_name}**\nОтправил: **{nickname}**"
        self.discord_alert_last_sent[channel_name] = now
        def worker():
            ok_count = 0
            errors = []
            for url in webhooks:
                ok, error = post_discord_webhook(url, content)
                if ok:
                    ok_count += 1
                else:
                    errors.append(error)
            if ok_count == len(webhooks):
                return
            if ok_count > 0:
                self.notify_signal.emit("Discord", f"Discord-оповещение отправлено не во все каналы: {ok_count}/{len(webhooks)}.\nПроверьте интернет-соединение, обход или корректность вебхук-ссылок.")
            else:
                self.notify_signal.emit("Discord", "Не удалось отправить Discord-оповещение.\nПроверьте интернет-соединение, обход или корректность вебхук-ссылок.")
            if errors:
                print("Discord webhook errors:", "; ".join(errors[:3]))

        threading.Thread(target=worker, daemon=True).start()
        return True

    def apply_overlay_settings(self):
        if not self.settings.overlay_enabled:
            if self.overlay_window is not None:
                self.overlay_window.hide()
            return
        if self.overlay_window is None:
            self.overlay_window = OverlayWindow(self.settings)
        else:
            self.overlay_window.apply_settings()
        self.overlay_window.show()
        self.tick()

    def open_feedback(self):
        dialog = FeedbackDialog(self)
        geo = self.geometry()
        dialog.move(geo.x() + geo.width() - dialog.width() - s(18, self.settings.app_scale), geo.y() + s(50, self.settings.app_scale))
        dialog.show()

    def open_settings(self):
        dialog = SettingsDialog(self)
        geo = self.geometry()
        dialog.move(geo.x() + geo.width() - dialog.width() - s(18, self.settings.app_scale), geo.y() + s(50, self.settings.app_scale))
        dialog.show()

    def handle_close_button(self):
        if self.tray is not None and self.tray.isVisible():
            self.hide()
        else:
            self.quit_app()

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        stop_alert_sound()
        if self.overlay_window is not None:
            self.overlay_window.close()
        if self.tray is not None:
            self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if self.tray is not None and self.tray.isVisible():
            event.ignore()
            self.hide()
        else:
            event.accept()

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


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("B&S NEO Spawn Timer")
    app.setApplicationDisplayName("B&S NEO Spawn Timer")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("westrup")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
