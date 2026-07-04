import threading
import webbrowser
from datetime import datetime, timedelta
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QMenu, QSystemTrayIcon
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction

from config import APP_VERSION, BLOCKS, TIMER_DEFS, ALL_TIMER_NAMES
from settings import AppSettings
from utils import s, fmt_seconds, next_world_boss
from styles import Style
from resources import app_icon, make_feedback_icon
from services.audio import stop_alert_sound, play_alert
from services.discord import post_discord_webhook
from services.updater import UpdateManager
from services.logger import log

from widgets.timer_block import TimerBlock
from widgets.world_boss import WorldBossBlock
from widgets.overlay import OverlayWindow
from dialogs.feedback_dialog import FeedbackDialog
from dialogs.settings_dialog import SettingsDialog
from dialogs.about_dialog import AboutDialog
from dialogs.message_dialog import MessageDialog

class MainWindow(QMainWindow):
    notify_signal = Signal(str, str)
    update_available_signal = Signal(object)

    def __init__(self):
        super().__init__()
        self.settings = AppSettings.load()
        self.active_timers = {}
        self.alerted = set()
        self.rows = {}
        self.overlay_window = None
        self.settings_dialog = None
        self.feedback_dialog = None
        self.about_dialog = None
        self.tray = None
        self.drag_pos = None
        self.world_name = "—"
        self.world_timer = "--:--:--"
        self.world_status = "normal"
        self.world_alerted_target = None
        self.discord_alert_last_sent = {}
        self.notify_signal.connect(self.show_notification)
        self.update_available_signal.connect(self.show_update_dialog)

        self.updater = UpdateManager(self.settings)
        log(f"Запуск программы {APP_VERSION}")

        QTimer.singleShot(1000, self.check_updates)

        self.setWindowTitle(f"B&S NEO Spawn Timer {APP_VERSION}")
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
        title = QLabel("B&S NEO Spawn Timer")
        title.setObjectName("AppTitle")
        title.setFixedHeight(s(18, sc))
        subtitle = QLabel(f"Версия {APP_VERSION}")
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
        
        about_btn = QPushButton("ⓘ")
        about_btn.setObjectName("Ghost")
        about_btn.setFixedSize(s(34, sc), s(34, sc))
        about_btn.clicked.connect(self.open_about)

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
        top_layout.addWidget(about_btn)
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
        if rebuild: self.build_ui()
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
                if now - base < timedelta(hours=12): self.active_timers[name] = base
                else:
                    del self.settings.active_timers[name]
                    cleaned = True
            except Exception:
                del self.settings.active_timers[name]
                cleaned = True
        if cleaned: self.settings.save()

    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable(): return
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(f"B&S NEO Spawn Timer {APP_VERSION}")
        menu = QMenu()
        show_action = QAction("Открыть", self)
        show_action.triggered.connect(self.show_from_tray)

        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.open_settings)

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.quit_app)

        menu.addAction(show_action)
        menu.addAction(settings_action)
        menu.addSeparator()
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
        if not self.rows: return
        data = self.calculate_timer_data()
        for name, values in data.items():
            if name in self.rows: self.rows[name].set_state(values)

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
        if self.tray is not None and self.tray.isVisible(): self.tray.showMessage(title, message, app_icon(), 3500)
        else: print(f"{title}: {message}")
        
    def show_update_dialog(self, update: dict):
        version = update.get("version", "Неизвестно")
        body = update.get("body", "").strip()
        url = update.get("url", "")

        if not body:
            body = "Описание изменений отсутствует."

        message = (
            f"Доступна новая версия программы.\n\n"
            f"Текущая версия: {APP_VERSION}\n"
            f"Новая версия: {version}"
        )

        dialog = MessageDialog(
            self,
            "Доступно обновление",
            message,
            body[:1200],
            ok_text="Открыть релиз",
            cancel_text="Позже",
        )

        if dialog.exec_result() and url:
            webbrowser.open(url)
            
    def check_updates_now(self):
        threading.Thread(
            target=lambda: self._check_updates_worker(force=True),
            daemon=True
        ).start()
        
    def check_updates(self):
        threading.Thread(
            target=self._check_updates_worker,
            daemon=True
        ).start()

    def _check_updates_worker(self, force=False):
        log("Проверка обновлений...")

        update = self.updater.check(force=force)

        if update:
            log(f"Найдена новая версия {update['version']}")
            self.update_available_signal.emit(update)
        else:
            log("Обновлений нет")

    def send_discord_alert(self, channel_name: str):
        now = datetime.now()
        last_sent = self.discord_alert_last_sent.get(channel_name)
        if last_sent and (now - last_sent).total_seconds() < 30: return False

        webhooks = [url.strip() for url in self.settings.discord_webhooks if str(url).strip()]
        if not webhooks:
            self.show_notification("Discord", "Добавь хотя бы один вебхук в настройках.")
            return False

        nickname = self.settings.discord_nickname.strip() or "Неизвестный"
        message = self.settings.discord_message.strip() or "@everyone 🚨 Императорское древо"

        content = (
            f"{message}\n"
            f"**{channel_name}**\n"
            f"Отправитель: **{nickname}**"
        )
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
                log(f"Discord отправлен ({ok_count}/{len(webhooks)})")
                return

            log(f"Ошибка отправки Discord ({ok_count}/{len(webhooks)})")

            if ok_count > 0:
                self.notify_signal.emit(
                    "Discord",
                    f"Discord-оповещение отправлено не во все каналы: "
                    f"{ok_count}/{len(webhooks)}.\n"
                    "Проверьте интернет-соединение, обход или корректность вебхук-ссылок."
                )
            else:
                self.notify_signal.emit(
                    "Discord",
                    "Не удалось отправить Discord-оповещение.\n"
                    "Проверьте интернет-соединение, обход или корректность вебхук-ссылок."
                )

            if errors:
                log("Discord errors: " + "; ".join(errors[:3]))
                print("Discord webhook errors:", "; ".join(errors[:3]))

        threading.Thread(target=worker, daemon=True).start()
        return True

    def apply_overlay_settings(self):
        if not self.settings.overlay_enabled:
            if self.overlay_window is not None: self.overlay_window.hide()
            return
        if self.overlay_window is None: self.overlay_window = OverlayWindow(self.settings)
        else: self.overlay_window.apply_settings()
        self.overlay_window.show()
        self.tick()

    def open_feedback(self):
        if self.feedback_dialog is not None:
            self.feedback_dialog.raise_()
            self.feedback_dialog.activateWindow()
            return

        self.feedback_dialog = FeedbackDialog(self)

        geo = self.geometry()
        self.feedback_dialog.move(
            geo.x() + geo.width() - self.feedback_dialog.width() - s(18, self.settings.app_scale),
            geo.y() + s(50, self.settings.app_scale)
        )

        self.feedback_dialog.show()

    def open_settings(self):
        if self.settings_dialog is not None:
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return

        self.settings_dialog = SettingsDialog(self)

        geo = self.geometry()
        self.settings_dialog.move(
            geo.x() + geo.width() - self.settings_dialog.width() - s(18, self.settings.app_scale),
            geo.y() + s(50, self.settings.app_scale)
        )

        self.settings_dialog.show()
        
    def open_about(self):
        if self.about_dialog is not None:
            if self.about_dialog.isVisible():
                self.about_dialog.raise_()
                self.about_dialog.activateWindow()
                return

            self.about_dialog.show()
            self.about_dialog.raise_()
            self.about_dialog.activateWindow()
            return

        self.about_dialog = AboutDialog(self)
        self.about_dialog.show()

    def handle_close_button(self):
        if self.tray is not None and self.tray.isVisible(): self.hide()
        else: self.quit_app()

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        stop_alert_sound()
        log("Выход из программы")
        if self.overlay_window is not None: self.overlay_window.close()
        if self.tray is not None: self.tray.hide()
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