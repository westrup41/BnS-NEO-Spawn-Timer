import threading
import webbrowser
from datetime import datetime, timedelta
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QMenu, QSystemTrayIcon
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QAction

from config import APP_VERSION, BLOCKS, TIMER_DEFS, ALL_TIMER_NAMES, SPAWN_EFFECT_SECONDS
from settings import AppSettings
from utils import s, fmt_seconds, next_world_boss, custom_event_state, split_duration
from styles import Style
from resources import app_icon, make_feedback_icon, make_info_icon
from services.audio import stop_alert_sound, play_alert
from services.discord import post_discord_webhook
from services.updater import UpdateManager
from services.logger import log
from network.manager import NetworkManager
from data.chat_history import ChatHistory

from widgets.timer_block import TimerBlock
from widgets.world_boss import WorldBossBlock
from widgets.event_block import EventBlock
from widgets.overlay import OverlayWindow
from dialogs.feedback_dialog import FeedbackDialog
from dialogs.settings_dialog import SettingsDialog
from dialogs.about_dialog import AboutDialog
from dialogs.message_dialog import MessageDialog
from dialogs.chat_dialog import ChatDialog
from dialogs.nickname_dialog import NicknameDialog

class MainWindow(QMainWindow):
    update_available_signal = Signal(object)
    update_check_result_signal = Signal(object)

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
        self.chat_dialog = None
        self.chat_history = ChatHistory()
        self.chat_unread = False
        self.internet_available = False
        self.tray = None
        self.drag_pos = None
        self.world_name = "—"
        self.world_timer = "--:--:--"
        self.world_status = "normal"
        self.world_alerted_target = None
        self.event_name = "No_Text"
        self.event_timer = "--:--:--"
        self.event_days = 0
        self.event_status = "idle"
        self.event_alerted_target = None
        self.discord_alert_last_sent = {}
        self.incoming_spawn_last_seen = {}
        self.spawn_effects = {}
        self.spawn_blink_state = False
        self.spawn_start_times = {}
        self.network = NetworkManager(self)
        self.network.spawn_received.connect(self.on_network_spawn)
        self.network.chat_received.connect(self.on_network_chat)
        self.network.reaction_received.connect(self.on_network_reaction)
        self.network.online_changed.connect(self.on_online_changed)
        self.network.history_received.connect(self.on_network_history)
        self.update_available_signal.connect(self.show_update_dialog)
        self.update_check_result_signal.connect(self.show_update_check_result)

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
        self.network.start()

        self.ticker = QTimer(self)
        self.ticker.timeout.connect(self.tick)
        self.ticker.start(1000)
        self.spawn_timer = QTimer(self)
        self.spawn_timer.timeout.connect(self.update_spawn_effect)
        self.spawn_timer.start(500)
        self.tick()
        if self.settings.overlay_enabled:
            QTimer.singleShot(150, self.apply_overlay_settings)

    def target_size(self):
        scale = self.settings.app_scale
        base_height = 668 + (148 if self.settings.event_enabled else 0)
        return s(700, scale), s(base_height, scale)

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
        
        about_btn = QPushButton("")
        about_btn.setObjectName("Ghost")
        about_btn.setIcon(make_info_icon(s(23, sc)))
        about_btn.setIconSize(QSize(s(23, sc), s(23, sc)))
        about_btn.setToolTip("О программе")
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
        self.event_block = None
        if self.settings.event_enabled:
            self.event_block = EventBlock(self)
            layout.addWidget(self.event_block)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addStretch(1)

        self.chat_btn = QPushButton("")
        self.chat_btn.setObjectName("ChatButton")
        self.chat_btn.setIcon(make_feedback_icon(s(30, sc)))
        self.chat_btn.setIconSize(self.chat_btn.sizeHint())
        self.chat_btn.setFixedSize(s(48, sc), s(48, sc))
        self.chat_btn.setToolTip("Открыть P2P-чат")
        self.chat_btn.clicked.connect(self.open_chat)
        footer.addWidget(self.chat_btn)
        layout.addLayout(footer)
        self.chat_badge = QLabel(self.chat_btn)
        self.chat_badge.setObjectName("ChatBadge")
        self.chat_badge.setFixedSize(s(11, sc), s(11, sc))
        self.chat_badge.move(s(34, sc), s(3, sc))
        self.update_chat_button()

        top.mousePressEvent = self.mousePressEvent
        top.mouseMoveEvent = self.mouseMoveEvent
        top.mouseReleaseEvent = self.mouseReleaseEvent

    def has_discord_webhooks(self) -> bool:
        return any(str(url).strip() for url in self.settings.discord_webhooks)

    def refresh_discord_buttons(self):
        for row in self.rows.values():
            if hasattr(row, "refresh_announce_button_visual"):
                row.refresh_announce_button_visual()

    def apply_visual_settings(self, rebuild=False):
        if rebuild: self.build_ui()
        QApplication.instance().setStyleSheet(Style.main(self.settings.app_scale))
        width, height = self.target_size()
        self.setFixedSize(width, height)
        self.tick()
        self.refresh_discord_buttons()
        self.update_chat_button()

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
        self.cancel_spawn_effect(name)
        self.active_timers[name] = base_time
        self.alerted.discard(name)
        self.settings.active_timers[name] = base_time.isoformat()
        self.settings.save()
        self.tick()

    def stop_timer(self, name: str):
        stop_alert_sound()
        self.cancel_spawn_effect(name)
        self.active_timers.pop(name, None)
        self.alerted.discard(name)
        self.settings.active_timers.pop(name, None)
        self.settings.save()
        self.tick()

    def cancel_spawn_effect(self, name: str):
        self.spawn_effects.pop(name, None)
        self.spawn_start_times.pop(name, None)
        row = self.rows.get(name)
        if row is not None:
            row.set_spawn_blink(False)
        if self.overlay_window is not None:
            self.overlay_window.set_spawn_blink(name, False)

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
        for channel, until in list(self.spawn_effects.items()):

            if datetime.now() < until:
                if channel in data:
                    data[channel] = {
                        "timer": "Появляется",
                        "interval": "",
                        "status": "detected",
                        "active": True
                    }
            else:
                del self.spawn_effects[channel]
                row = self.rows.get(channel)
                if row:
                    row.set_spawn_blink(False)
                if self.overlay_window is not None:
                    self.overlay_window.set_spawn_blink(channel, False)

                base_time = self.spawn_start_times.pop(channel, None)
                if base_time is not None:
                    self.start_timer(channel, base_time)
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

        if self.settings.event_enabled:
            event_state = custom_event_state(
                self.settings.event_schedule,
                appearance_seconds=self.settings.event_appearance_minutes * 60,
            )
            event_target = event_state["target"]
            event_seconds = event_state["seconds"]
            self.event_name = event_state["name"]
            self.event_days = 0
            if event_state["phase"] == "appearing":
                self.event_timer = "Появление"
                self.event_status = "appearing"
            elif event_target is None or event_seconds is None:
                self.event_timer = "--:--:--"
                self.event_status = "idle"
            else:
                self.event_days, self.event_timer = split_duration(event_seconds)
                self.event_status = "hot" if event_seconds <= 600 else "normal"
                event_key = event_target.isoformat()
                if 0 < event_seconds <= 600 and self.event_alerted_target != event_key:
                    play_alert(self.settings.sound_enabled, self.settings.custom_sound_path, self.settings.sound_volume)
                    self.event_alerted_target = event_key
            if self.event_block is not None:
                self.event_block.set_state(self.event_name, self.event_timer, self.event_status, self.event_days)

        if self.overlay_window is not None and self.overlay_window.isVisible():
            self.overlay_window.update_timers(data)
            self.overlay_window.update_world(self.world_name, self.world_timer, self.world_status)
            self.overlay_window.update_event(self.event_name, self.event_timer, self.event_status, self.event_days)
        
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

        result = self.updater.check_with_status(force=force)
        update = result.get("update")

        if update:
            log(f"Найдена новая версия {update['version']}")
            self.update_available_signal.emit(update)
            if force:
                self.update_check_result_signal.emit({
                    "status": "update",
                    "update": update,
                })
        else:
            log("Обновлений нет")
            if force:
                self.update_check_result_signal.emit(result)

    def show_update_check_result(self, result: dict):
        status = result.get("status")
        if status == "current":
            text = f"У вас установлена актуальная версия {APP_VERSION}."
        elif status == "update":
            text = f"Доступна новая версия {result.get('update', {}).get('version', '')}."
        else:
            text = "Не удалось проверить обновления. Проверьте подключение к интернету."
        if self.about_dialog is not None:
            self.about_dialog.set_update_status(text, status == "error")
        else:
            MessageDialog(self, "Проверка обновлений", text).exec()

    def announce_spawn(self, channel_name: str):
        now = datetime.now()

        if not self.internet_available or channel_name not in TIMER_DEFS:
            return False

        last_sent = self.discord_alert_last_sent.get(channel_name)

        if last_sent and (now - last_sent).total_seconds() < 30:
            return False

        self.discord_alert_last_sent[channel_name] = now

        packet = self.network.send_spawn(channel_name)
        if packet is None:
            return False

        self._accept_spawn(packet, apply_notification=True)
        self._send_webhooks_async(channel_name)

        return True

    def get_announce_cooldown(self, channel_name: str) -> int:
        last_sent = self.discord_alert_last_sent.get(channel_name)
        if not last_sent:
            return 0
        remaining = 30 - int((datetime.now() - last_sent).total_seconds())
        return max(0, remaining)

    def on_network_spawn(self, packet: dict):
        channel = str(packet.get("channel", ""))
        sender_id = str(packet.get("author_id", ""))
        key = (sender_id, channel)
        now = datetime.now()
        last_seen = self.incoming_spawn_last_seen.get(key)
        if last_seen and (now - last_seen).total_seconds() < 30:
            return
        self.incoming_spawn_last_seen[key] = now
        if len(self.incoming_spawn_last_seen) > 1000:
            cutoff = now - timedelta(minutes=10)
            self.incoming_spawn_last_seen = {
                item_key: seen for item_key, seen in self.incoming_spawn_last_seen.items()
                if seen >= cutoff
            }
        sender_blocked = sender_id in self.settings.blocked_alert_user_ids
        self._accept_spawn(packet, apply_notification=self.settings.global_notifications and not sender_blocked)

    def set_user_alert_blocked(self, user_id: str, blocked: bool, nickname: str = "Неизвестный"):
        user_id = str(user_id or "").strip()
        if not user_id or user_id == self.get_user_id():
            return
        blocked_users = dict(self.settings.blocked_alert_users)
        if blocked:
            blocked_users[user_id] = str(nickname or "Неизвестный")[:16]
        else:
            blocked_users.pop(user_id, None)
        self.settings.blocked_alert_users = blocked_users
        self.settings.blocked_alert_user_ids = list(blocked_users)
        self.settings.save()

    def is_user_alert_blocked(self, user_id: str) -> bool:
        return str(user_id or "") in self.settings.blocked_alert_users

    def _accept_spawn(self, packet: dict, apply_notification: bool):
        channel = str(packet.get("channel", ""))
        if channel not in TIMER_DEFS:
            return

        if self.settings.chat_enabled and self.settings.discord_nickname.strip():
            message = dict(packet)
            if self.chat_history.add(message):
                self.notify_chat_changed(unread=True)

        if not apply_notification:
            return

        self.alerted.add(channel)
        play_alert(
            self.settings.incoming_alert_sound_enabled,
            self.settings.custom_sound_path,
            self.settings.sound_volume
        )
        
        now = datetime.now()

        self.spawn_effects[channel] = now + timedelta(seconds=SPAWN_EFFECT_SECONDS)
        self.spawn_start_times[channel] = now
        self.tick()
        
    def update_spawn_effect(self):
        if not self.spawn_effects:
            return

        self.spawn_blink_state = not self.spawn_blink_state

        for channel in list(self.spawn_effects.keys()):

            if datetime.now() >= self.spawn_effects[channel]:
                row = self.rows.get(channel)
                if row:
                    row.set_spawn_blink(False)
                if self.overlay_window is not None:
                    self.overlay_window.set_spawn_blink(channel, False)
                continue

            row = self.rows.get(channel)

            if row:
                row.set_spawn_blink(self.spawn_blink_state)
            if self.overlay_window is not None:
                self.overlay_window.set_spawn_blink(channel, self.spawn_blink_state)

    def on_network_chat(self, packet: dict):
        if not self.settings.chat_enabled or not self.settings.discord_nickname.strip():
            return
        packet = dict(packet)
        if not str(packet.get("message") or "").strip() or len(str(packet.get("message"))) > 120:
            return
        if self.chat_history.add(packet):
            self.notify_chat_changed(unread=True)

    def send_chat_message(self, text: str):
        if not self.settings.chat_enabled or not self.settings.discord_nickname.strip():
            return False
        packet = self.network.send_chat(text[:120])
        if packet is None:
            return False
        self.chat_history.add(packet)
        self.notify_chat_changed(unread=False)
        return True

    def react_to_message(self, message_id: str, value: int):
        user_id = self.get_user_id()
        current = self.chat_history.get_vote(message_id, user_id)
        applied = 0 if current == value else value
        packet = self.network.send_reaction(message_id, applied)
        if packet is not None and self.chat_history.apply_reaction(packet):
            self.notify_chat_changed(unread=False)

    def on_network_reaction(self, packet: dict):
        if self.chat_history.apply_reaction(packet):
            self.notify_chat_changed(unread=False)

    def on_network_history(self, messages: list):
        if not self.settings.chat_enabled or not self.settings.discord_nickname.strip():
            return
        changed = False
        for message in messages[:100]:
            if isinstance(message, dict) and self.chat_history.add(message):
                changed = True
        if changed:
            self.notify_chat_changed(unread=True)

    def notify_chat_changed(self, unread=False):
        if self.chat_dialog is not None and self.chat_dialog.isVisible():
            self.chat_dialog.refresh_messages(scroll_to_bottom=True)
            unread = False
        if unread:
            self.set_chat_unread(True)

    def set_chat_unread(self, unread: bool):
        self.chat_unread = bool(unread and self.settings.chat_enabled)
        self.update_chat_button()

    def update_chat_button(self):
        if not hasattr(self, "chat_btn"):
            return
        enabled = bool(self.settings.chat_enabled)
        nickname_ready = bool(self.settings.discord_nickname.strip())
        self.chat_btn.setEnabled(enabled)
        self.chat_btn.setProperty("missing_nickname", "true" if enabled and not nickname_ready else "false")
        self.chat_btn.style().unpolish(self.chat_btn)
        self.chat_btn.style().polish(self.chat_btn)
        self.chat_badge.setVisible(enabled and self.chat_unread)
        if not enabled:
            tooltip = "Чат отключён в онлайн-функциях"
        elif not nickname_ready:
            tooltip = "Введите ник, чтобы открыть чат"
        else:
            tooltip = "Открыть чат"
        self.chat_btn.setToolTip(tooltip)

    def open_chat(self):
        if not self.settings.chat_enabled:
            return
        if not self.settings.discord_nickname.strip():
            dialog = NicknameDialog(self)
            if dialog.exec() != QDialog.Accepted:
                return
            self.settings.discord_nickname = dialog.nickname()
            self.settings.save()
            self.update_chat_button()
        if self.chat_dialog is None:
            self.chat_dialog = ChatDialog(self)
            geo = self.geometry()
            self.chat_dialog.move(geo.right() - self.chat_dialog.width(), geo.bottom() - self.chat_dialog.height())
        self.set_chat_unread(False)
        self.chat_dialog.show()
        self.chat_dialog.raise_()
        self.chat_dialog.activateWindow()

    def on_online_changed(self, available: bool):
        self.internet_available = bool(available)
        self.refresh_discord_buttons()
        if self.chat_dialog is not None:
            self.chat_dialog.update_online_state(self.internet_available)

    def _send_webhooks_async(self, channel_name: str):
        urls = [str(url).strip() for url in self.settings.discord_webhooks if str(url).strip()]
        if not urls:
            return
        nickname = self.get_nickname()
        text = self.settings.discord_message.strip() or "@everyone 🚨 Императорское древо"
        content = f"{text} | {channel_name}\nОтправитель: {nickname}"

        def worker():
            for url in urls:
                ok, error = post_discord_webhook(url, content)
                if not ok:
                    log(f"Discord webhook пропущен: {error}")
        threading.Thread(target=worker, daemon=True).start()

    def get_nickname(self):
        return self.settings.discord_nickname.strip() or "Неизвестный"

    def get_user_id(self):
        return self.network.identity.user_id

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
        if self.settings.hide_to_tray and self.tray is not None and self.tray.isVisible(): self.hide()
        else: self.quit_app()

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self.network.stop()
        stop_alert_sound()
        log("Выход из программы")
        if self.overlay_window is not None: self.overlay_window.close()
        if self.tray is not None: self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if self.settings.hide_to_tray and self.tray is not None and self.tray.isVisible():
            event.ignore()
            self.hide()
        else:
            event.ignore()
            self.quit_app()

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
