import threading
from datetime import datetime, timedelta
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel, QPushButton, QMenu, QSystemTrayIcon
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QRect, QPropertyAnimation, QEasingCurve, QEvent, QObject
from PySide6.QtGui import QAction

from config import (APP_VERSION, BLOCKS, TIMER_DEFS, ALL_TIMER_NAMES,
                    SPAWN_EFFECT_SECONDS, CHAT_MESSAGE_COOLDOWN, CHAT_DUPLICATE_SECONDS)
from settings import AppSettings
from utils import s, fmt_seconds, next_world_boss, custom_event_state
from styles import Style
from resources import app_icon, ui_icon, is_admin_build
from services.audio import stop_alert_sound, play_alert
from services.alert_sounds import AlertSoundController
from services.hotkeys import GlobalHotkeyManager
from services.updater import UpdateManager
from services.discord import post_discord_webhook
from network.manager import NetworkManager
from data.chat_history import ChatHistory

from widgets.timer_block import TimerBlock
from widgets.world_boss import WorldBossBlock
from widgets.event_block import EventBlock
from widgets.field_boss_block import FieldBossBlock
from widgets.motion import ButtonMotion, stagger_cards
from widgets.overlay import OverlayWindow
from widgets.tracker_button import TrackerButton
from widgets.ui_primitives import ThemeShell
from dialogs.feedback_dialog import FeedbackDialog
from dialogs.settings_dialog import SettingsDialog
from dialogs.about_dialog import AboutDialog
from dialogs.message_dialog import MessageDialog
from dialogs.chat_dialog import ChatDialog
from dialogs.nickname_dialog import NicknameDialog
from dialogs.chat_tracker_dialog import ChatTrackerDialog
from services.admin import verify_admin_packet
from services.chat_matching import clean as clean_chat_alert


class TooltipBlocker(QObject):
    def eventFilter(self, watched, event):
        if event.type() == QEvent.ToolTip:
            if bool(watched.property("allowTooltip")):
                return False
            return True
        return super().eventFilter(watched, event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = AppSettings.load()
        self.tooltip_blocker = TooltipBlocker(self)
        QApplication.instance().installEventFilter(self.tooltip_blocker)
        self._hidden_aux_windows = []
        self._aux_windows_hidden_for_tray = False
        self._quitting = False
        Style.set_theme(self.settings.ui_theme)
        self.admin_build = is_admin_build()
        self.button_motion = ButtonMotion(self)
        self.active_timers = {}
        self.alerted = set()
        self.rows = {}
        self.overlay_window = None
        self.settings_dialog = None
        self.feedback_dialog = None
        self.about_dialog = None
        self.chat_dialog = None
        self.chat_tracker_dialog = None
        self.chat_alert_until = None
        self.chat_alert_source = None
        self.chat_alert_recent = {}
        self.chat_alert_quorum = {}
        initial_room = self.settings.online_room_code if self.settings.online_room_private else ""
        self.chat_history = ChatHistory(room_code=initial_room)
        self.chat_unread = False
        self.internet_available = False
        self.tray = None
        self.drag_pos = None
        self.world_name = "—"
        self.world_timer = "--:--:--"
        self.world_status = "normal"
        self.world_alerted_target = None
        self.event_name = "Неизвестный босс"
        self.event_timer = "--:--:--"
        self.event_days = 0
        self.event_status = "idle"
        self.event_alerted_target = None
        self.field_boss_states = []
        self.field_boss_alerted_targets = [None, None]
        self._chat_animation = None
        self.discord_alert_last_sent = {}
        self.incoming_spawn_last_seen = {}
        self.chat_last_sent_at = None
        self.chat_last_sent_text = ""
        self.chat_recent_remote = {}
        self.spawn_effects = {}
        self.spawn_blink_state = False
        self.spawn_start_times = {}
        self.network = NetworkManager(self)
        self.network.spawn_received.connect(self.on_network_spawn)
        self.network.chat_received.connect(self.on_network_chat)
        self.network.reaction_received.connect(self.on_network_reaction)
        self.network.online_changed.connect(self.on_online_changed)
        self.network.history_received.connect(self.on_network_history)
        self.network.admin_received.connect(self.on_admin_command)
        self.network.chat_alert_received.connect(self.on_network_chat_alert)
        self.sound_controller = AlertSoundController(self.settings, self)

        suffix = " Admin" if self.admin_build else ""
        self.setWindowTitle(f"B&S NEO Spawn Timer {APP_VERSION}{suffix}")
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.restore_active_timers()
        self.build_ui()
        self.hotkey_manager = GlobalHotkeyManager(QApplication.instance(), self)
        self.hotkey_manager.triggered.connect(self.on_hotkey)
        self.apply_hotkeys()
        self.updater = UpdateManager(self)
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
        if self.settings.auto_update_enabled:
            QTimer.singleShot(2500, self.updater.check_automatic)

    def target_size(self):
        return s(1120, self.settings.app_scale), s(590, self.settings.app_scale)

    def build_ui(self):
        self.rows = {}
        motion_cards = []
        sc = self.settings.app_scale
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.shell = ThemeShell(self)
        root_layout.addWidget(self.shell)
        self.setCentralWidget(root)

        shell_layout = QHBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        sidebar = QFrame(); sidebar.setObjectName("BrandRail"); sidebar.setFixedWidth(s(184, sc))
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(s(14, sc), s(18, sc), s(14, sc), s(16, sc))
        sidebar_layout.setSpacing(s(8, sc))
        workspace = QFrame(); workspace.setObjectName("Workspace")
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(s(14, sc), s(12, sc), s(14, sc), s(14, sc))
        layout.setSpacing(s(10, sc))
        shell_layout.addWidget(workspace, 1)
        shell_layout.addWidget(sidebar)

        top = QFrame()
        top.setObjectName("TopBar")
        top.setFixedHeight(s(34, sc))
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

        feedback_btn = QPushButton("Обратная связь")
        feedback_btn.setObjectName("RailButton")
        feedback_btn.setIcon(ui_icon("chat"))
        feedback_btn.setIconSize(QSize(s(18, sc), s(18, sc)))
        feedback_btn.setFixedHeight(s(38, sc))
        feedback_btn.clicked.connect(self.open_feedback)
        
        about_btn = QPushButton("О программе")
        about_btn.setObjectName("RailButton")
        about_btn.setIcon(ui_icon("info"))
        about_btn.setIconSize(QSize(s(23, sc), s(23, sc)))
        about_btn.setToolTip("О программе")
        about_btn.setFixedHeight(s(38, sc))
        about_btn.clicked.connect(self.open_about)

        settings_btn = QPushButton("Настройки")
        settings_btn.setObjectName("RailButton")
        settings_btn.setIcon(ui_icon("settings")); settings_btn.setIconSize(QSize(s(19, sc), s(19, sc)))
        settings_btn.setFixedHeight(s(38, sc))
        settings_btn.clicked.connect(self.open_settings)

        self.sound_btn = QPushButton("")
        self.sound_btn.setObjectName("RailButton")
        self.sound_btn.setText("Звук")
        self.sound_btn.setFixedHeight(s(38, sc))
        self.sound_btn.clicked.connect(self.toggle_sound_muted)
        self.update_sound_button()

        minimize = QPushButton("")
        minimize.setObjectName("Chrome")
        minimize.setIcon(ui_icon("minimize")); minimize.setIconSize(QSize(s(18, sc), s(18, sc)))
        minimize.setFixedSize(s(38, sc), s(34, sc))
        minimize.clicked.connect(self.showMinimized)
        close = QPushButton("")
        close.setObjectName("Close")
        close.setIcon(ui_icon("close")); close.setIconSize(QSize(s(18, sc), s(18, sc)))
        close.setFixedSize(s(38, sc), s(34, sc))
        close.clicked.connect(self.handle_close_button)

        sidebar_layout.addLayout(titles)
        rail_line = QFrame(); rail_line.setObjectName("RailLine"); rail_line.setFixedHeight(1); sidebar_layout.addWidget(rail_line)
        sidebar_layout.addSpacing(s(4, sc))
        sidebar_layout.addWidget(settings_btn)
        sidebar_layout.addWidget(self.sound_btn)
        sidebar_layout.addWidget(about_btn)
        sidebar_layout.addWidget(feedback_btn)

        top_layout.addStretch(1)
        top_layout.addWidget(minimize)
        top_layout.addWidget(close)
        layout.addWidget(top)

        content = QFrame(); content.setObjectName("Dashboard")
        dashboard = QGridLayout(content); dashboard.setContentsMargins(0, 0, 0, 0); dashboard.setSpacing(s(12, sc))
        self.tree_block = TimerBlock(self, BLOCKS[0], settings_button=False)
        self.field_boss_block = FieldBossBlock(self)
        self.world_block = WorldBossBlock(self)
        self.event_block = EventBlock(self)
        cards = (self.tree_block, self.field_boss_block, self.world_block, self.event_block)
        for index, card in enumerate(cards):
            dashboard.addWidget(card, index // 2, index % 2)
            motion_cards.append(card)
        self.tree_block.set_section_enabled(self.settings.tree_section_enabled)
        self.field_boss_block.set_section_enabled(self.settings.field_bosses_enabled)
        self.world_block.set_section_enabled(self.settings.world_section_enabled)
        self.event_block.set_section_enabled(self.settings.event_enabled)
        dashboard.setRowMinimumHeight(0, s(342, sc)); dashboard.setRowMinimumHeight(1, s(150, sc))
        dashboard.setRowStretch(0, 0); dashboard.setRowStretch(1, 0)
        dashboard.setColumnStretch(0, 1); dashboard.setColumnStretch(1, 1)
        layout.addWidget(content, 1)

        self.chat_btn = QPushButton("Чат")
        self.chat_btn.setObjectName("ChatButton")
        self.chat_btn.setIcon(ui_icon("chat"))
        self.chat_btn.setIconSize(QSize(s(19, sc), s(19, sc)))
        self.chat_btn.setFixedHeight(s(40, sc))
        self.chat_btn.setToolTip("Открыть P2P-чат")
        self.chat_btn.clicked.connect(self.open_chat)
        sidebar_layout.addStretch(1)

        self.tracker_btn = TrackerButton(self, sidebar)
        self.tracker_btn.setText("Трекер чата")
        self.tracker_btn.setIconSize(QSize(s(20, sc), s(20, sc)))
        self.tracker_btn.setFixedHeight(s(40, sc))
        self.tracker_btn.setToolTip("Трекер игрового чата")
        self.tracker_btn.clicked.connect(self.open_chat_tracker)
        self.tracker_btn.setVisible(True)
        self.tracker_btn.setEnabled(self.settings.chat_tracker_enabled)
        sidebar_layout.addWidget(self.tracker_btn)
        sidebar_layout.addWidget(self.chat_btn)
        self.chat_badge = QLabel(self.chat_btn)
        self.chat_badge.setObjectName("ChatBadge")
        self.chat_badge.setFixedSize(s(11, sc), s(11, sc))
        self.chat_badge.move(s(145, sc), s(4, sc))
        self.update_chat_button()

        if self.settings.ui_theme != "classic":
            self.button_motion.install(self.shell)
            QTimer.singleShot(20, lambda cards=motion_cards: stagger_cards(cards, self))

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
        if self.chat_dialog is not None:
            self.chat_dialog.apply_visual_settings()
            if self.chat_dialog.isVisible():
                QTimer.singleShot(0, lambda: self.chat_dialog.setGeometry(self.chat_panel_geometry()) if self.chat_dialog is not None and self.chat_dialog.isVisible() else None)
        if hasattr(self, 'tracker_btn'): QTimer.singleShot(0, self.position_tracker_button)

    def position_tracker_button(self):
        if not hasattr(self, 'tracker_btn'): return
        if self.tracker_btn.parent() is not self.shell:
            return
        x=s(18,self.settings.app_scale); y=max(0,self.shell.height()-self.tracker_btn.height()-s(16,self.settings.app_scale))
        self.tracker_btn.move(max(0,min(x,self.shell.width()-self.tracker_btn.width())),max(0,min(y,self.shell.height()-self.tracker_btn.height())))
        self.tracker_btn.raise_()

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
        if name in TIMER_DEFS and not self.settings.tree_section_enabled:
            return
        self.sound_controller.stop("timer")
        self.cancel_spawn_effect(name)
        self.active_timers[name] = base_time
        self.alerted.discard(name)
        self.settings.active_timers[name] = base_time.isoformat()
        self.settings.save()
        self.tick()

    def stop_timer(self, name: str):
        self.sound_controller.stop("timer")
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
            if not self.settings.tree_section_enabled:
                result[name] = {"timer": "--:--:--", "interval": "", "status": "idle", "active": False}
                continue
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
                self.sound_controller.play("timer")
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

        if self.settings.world_section_enabled:
            boss_name, world_target, seconds = next_world_boss()
            self.world_name = boss_name
            self.world_timer = fmt_seconds(seconds)
            self.world_status = "hot" if seconds <= 600 else "normal"
            world_alert_key = world_target.isoformat() if world_target else None
            if world_alert_key and 0 < seconds <= 600 and self.world_alerted_target != world_alert_key:
                self.sound_controller.play("timer")
                self.world_alerted_target = world_alert_key
            self.world_block.set_state(self.world_name, self.world_timer, self.world_status)
        else:
            self.world_name, self.world_timer, self.world_status = "—", "--:--:--", "idle"

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
                self.event_timer = fmt_seconds(event_seconds)
                self.event_status = "hot" if event_seconds <= 600 else "normal"
                event_key = event_target.isoformat()
                if 0 < event_seconds <= 600 and self.event_alerted_target != event_key:
                    self.sound_controller.play("timer")
                    self.event_alerted_target = event_key
            if self.event_block is not None:
                self.event_block.set_state(self.event_name, self.event_timer, self.event_status, self.event_days)
        else:
            self.event_name, self.event_timer, self.event_status, self.event_days = "—", "--:--:--", "idle", 0

        self.field_boss_states = []
        if self.settings.field_bosses_enabled:
            for index, location in enumerate(self.settings.field_boss_locations[:2]):
                location_name = str(location.get("name") or "")
                state = custom_event_state(
                    location.get("schedule") if isinstance(location.get("schedule"), dict) else {},
                    appearance_seconds=self.settings.field_boss_appearance_minutes * 60,
                )
                target = state["target"]
                seconds_left = state["seconds"]
                if state["phase"] == "appearing":
                    timer_text, status = "Появление", "appearing"
                elif target is None or seconds_left is None:
                    timer_text, status = "--:--:--", "idle"
                else:
                    hours, remainder = divmod(max(0, int(seconds_left)), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    timer_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    status = "hot" if seconds_left <= 600 else "normal"
                    target_key = target.isoformat()
                    if 0 < seconds_left <= 600 and self.field_boss_alerted_targets[index] != target_key:
                        self.sound_controller.play("timer")
                        self.field_boss_alerted_targets[index] = target_key
                item = {
                    "location": location_name,
                    "name": state["name"],
                    "timer": timer_text,
                    "status": status,
                }
                self.field_boss_states.append(item)
                if self.field_boss_block is not None:
                    self.field_boss_block.set_location_state(index, location_name, item["name"], timer_text, status)
        else:
            self.field_boss_states = []

        if self.overlay_window is not None and self.overlay_window.isVisible():
            self.overlay_window.update_timers(data)
            self.overlay_window.update_world(self.world_name, self.world_timer, self.world_status)
            self.overlay_window.update_event(self.event_name, self.event_timer, self.event_status, self.event_days)
            self.overlay_window.update_field_bosses(self.field_boss_states)
        
    def announce_spawn(self, channel_name: str):
        now = datetime.now()

        if not self.settings.global_notifications or not self.settings.tree_section_enabled or not self.internet_available or channel_name not in TIMER_DEFS:
            return False

        last_sent = self.discord_alert_last_sent.get(channel_name)

        if last_sent and (now - last_sent).total_seconds() < 30:
            return False

        packet = self.network.send_spawn(channel_name)
        if packet is None:
            return False

        self.discord_alert_last_sent[channel_name] = now
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
        if not self.settings.global_notifications:
            return
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
        if sender_id in self.settings.admin_banned_user_ids:
            return
        sender_blocked = sender_id in self.settings.blocked_alert_user_ids
        if sender_blocked:
            return
        self._accept_spawn(packet, apply_notification=True)

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

    def set_user_chat_blocked(self, user_id: str, blocked: bool, nickname: str = "Неизвестный"):
        user_id = str(user_id or "").strip()
        if not user_id or user_id == self.get_user_id():
            return
        users = dict(self.settings.blocked_chat_users)
        if blocked:
            users[user_id] = str(nickname or "Неизвестный")[:16]
            self.chat_history.delete_by_author(user_id)
        else:
            users.pop(user_id, None)
        self.settings.blocked_chat_users = users
        self.settings.save()
        self.notify_chat_changed(unread=False)

    def is_user_chat_blocked(self, user_id: str) -> bool:
        return str(user_id or "") in self.settings.blocked_chat_users

    def _message_allowed(self, packet: dict) -> bool:
        author_id = str(packet.get("author_id") or "")
        message_id = str(packet.get("id") or "")
        if (author_id in self.settings.blocked_chat_users
                or author_id in self.settings.admin_banned_user_ids
                or message_id in self.settings.admin_deleted_message_ids):
            return False
        epoch = self.settings.admin_chat_epoch
        if epoch:
            try:
                if datetime.fromisoformat(str(packet.get("timestamp") or "")) <= datetime.fromisoformat(epoch):
                    return False
            except Exception:
                return False
        return True

    def _accept_spawn(self, packet: dict, apply_notification: bool):
        channel = str(packet.get("channel", ""))
        if channel not in TIMER_DEFS:
            return

        if self.settings.chat_enabled and self.settings.discord_nickname.strip():
            message = dict(packet)
            if self._message_allowed(message) and self.chat_history.add(message):
                self.notify_chat_changed(unread=True)

        if not apply_notification:
            return

        self.alerted.add(channel)
        self.sound_controller.play("manual")
        
        now = datetime.now()

        self.spawn_effects[channel] = now + timedelta(seconds=SPAWN_EFFECT_SECONDS)
        self.spawn_start_times[channel] = now
        self.tick()
        
    def update_spawn_effect(self):
        if not self.spawn_effects and not self.chat_alert_until:
            return

        self.spawn_blink_state = not self.spawn_blink_state

        if self.chat_alert_until:
            active=datetime.now()<self.chat_alert_until
            blink=active and self.spawn_blink_state
            if self.tree_block is not None: self.tree_block.set_chat_alert(blink)
            if self.overlay_window is not None: self.overlay_window.set_chat_alert(blink)
            if not active:
                self.chat_alert_until=None
                self.chat_alert_source=None

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
        if not self._message_allowed(packet):
            return
        if not str(packet.get("message") or "").strip() or len(str(packet.get("message"))) > 120:
            return
        author = str(packet.get("author_id") or "")
        normalized = " ".join(str(packet.get("message") or "").casefold().split())
        now = datetime.now()
        previous = self.chat_recent_remote.get(author)
        if previous and previous[0] == normalized and (now - previous[1]).total_seconds() < CHAT_DUPLICATE_SECONDS:
            return
        self.chat_recent_remote[author] = (normalized, now)
        if self.chat_history.add(packet):
            self.notify_chat_changed(unread=True)

    def send_chat_message(self, text: str):
        if not self.settings.chat_enabled or not self.settings.discord_nickname.strip():
            return False
        now = datetime.now()
        normalized = " ".join(str(text).casefold().split())
        if self.chat_last_sent_at and (now - self.chat_last_sent_at).total_seconds() < CHAT_MESSAGE_COOLDOWN:
            return False
        if (normalized == self.chat_last_sent_text and self.chat_last_sent_at
                and (now - self.chat_last_sent_at).total_seconds() < CHAT_DUPLICATE_SECONDS):
            return False
        packet = self.network.send_chat(text[:120])
        if packet is None:
            return False
        self.chat_last_sent_at = now
        self.chat_last_sent_text = normalized
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
        if str(packet.get("voter_id") or "") in self.settings.admin_banned_user_ids:
            return
        if self.chat_history.apply_reaction(packet):
            self.notify_chat_changed(unread=False)

    def on_network_history(self, messages: list):
        if not self.settings.chat_enabled or not self.settings.discord_nickname.strip():
            return
        changed = False
        for message in messages[:100]:
            if isinstance(message, dict) and self._message_allowed(message) and self.chat_history.add(message):
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
        nickname_ready = bool(self.settings.discord_nickname.strip()) and int(getattr(self.settings, "chat_avatar_id", -1)) >= 0
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
        if not self.settings.discord_nickname.strip() or int(getattr(self.settings, "chat_avatar_id", -1)) < 0:
            dialog = NicknameDialog(self)
            if dialog.exec() != QDialog.Accepted:
                return
            self.settings.discord_nickname = dialog.nickname()
            self.settings.chat_avatar_id = dialog.avatar_id()
            self.settings.save()
            self.update_chat_button()
        if self.chat_dialog is not None and self.chat_dialog.isVisible():
            self.hide_chat_panel()
            return
        if self.chat_dialog is None: self.chat_dialog = ChatDialog(self)
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen(); available = screen.availableGeometry(); geo = self.geometry()
        gap = s(4, self.settings.app_scale)
        right_space = available.right() - geo.right()
        total = geo.width() + gap + self.chat_dialog.width()
        if right_space < self.chat_dialog.width() + gap and total <= available.width():
            self.move(max(available.left(), available.right() - total + 1), geo.y())
        self.set_chat_unread(False)
        final = self.chat_panel_geometry(); start = QRect(final)
        start.moveLeft(self.geometry().right() - self.chat_dialog.width() + s(18, self.settings.app_scale))
        self.chat_dialog.setGeometry(start); self.chat_dialog.show(); self.chat_dialog.raise_()
        self._chat_animation = QPropertyAnimation(self.chat_dialog, b"geometry", self)
        self._chat_animation.setDuration(210); self._chat_animation.setStartValue(start); self._chat_animation.setEndValue(final)
        self._chat_animation.setEasingCurve(QEasingCurve.OutCubic); self._chat_animation.finished.connect(self._chat_animation_done); self._chat_animation.start()

    def chat_panel_geometry(self):
        geo = self.geometry(); screen = QApplication.screenAt(geo.center()) or QApplication.primaryScreen(); available = screen.availableGeometry()
        width, height = self.chat_dialog.width(), min(geo.height(), available.height())
        gap = s(4, self.settings.app_scale)
        x = min(available.right() - width + 1, geo.x() + geo.width() + gap)
        y = max(available.top(), min(geo.top(), available.bottom() - height))
        return QRect(x, y, width, height)

    def hide_chat_panel(self):
        if self.chat_dialog is None or not self.chat_dialog.isVisible(): return
        start = self.chat_dialog.geometry(); end = QRect(start)
        end.moveLeft(self.geometry().right() - start.width() + s(18, self.settings.app_scale))
        self._chat_animation = QPropertyAnimation(self.chat_dialog, b"geometry", self); self._chat_animation.setDuration(170)
        self._chat_animation.setStartValue(start); self._chat_animation.setEndValue(end); self._chat_animation.setEasingCurve(QEasingCurve.InCubic)
        self._chat_animation.finished.connect(self.chat_dialog.hide); self._chat_animation.finished.connect(self._chat_animation_done); self._chat_animation.start()

    def _chat_animation_done(self):
        self._chat_animation = None
        if self.chat_dialog is not None and self.chat_dialog.isVisible():
            self.chat_dialog.schedule_scroll_to_bottom()

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.chat_dialog is not None and self.chat_dialog.isVisible() and self._chat_animation is None:
            self.chat_dialog.setGeometry(self.chat_panel_geometry())

    def open_chat_tracker(self):
        if not self.settings.chat_tracker_enabled: return
        if self.chat_tracker_dialog is None: self.chat_tracker_dialog=ChatTrackerDialog(self)
        self.chat_tracker_dialog.show();self.chat_tracker_dialog.raise_();self.chat_tracker_dialog.activateWindow()

    def on_local_chat_detection(self, trigger: str, text: str):
        if not self.start_chat_alert_effect('local'): return False
        if self.settings.chat_auto_timer_enabled:
            channel = self.channel_from_chat_trigger(trigger, text)
            if channel:
                self.start_timer(channel, datetime.now())
        if self.settings.chat_alerts_enabled:
            self.network.send_chat_alert(trigger,text)
        return True

    def on_network_chat_alert(self, packet: dict):
        if not self.settings.chat_alerts_enabled: return
        sender=str(packet.get('author_id') or '')
        if sender in self.settings.admin_banned_user_ids or sender in self.settings.blocked_alert_user_ids:return
        key=(sender,clean_chat_alert(packet.get('trigger','')));now=datetime.now();last=self.chat_alert_recent.get(key)
        if last and (now-last).total_seconds()<30:return
        self.chat_alert_recent[key]=now
        if self.settings.chat_alert_quorum_enabled:
            trigger_key = clean_chat_alert(packet.get('trigger',''))
            vote = self.chat_alert_quorum.get(trigger_key)
            if not vote or (now - vote['started']).total_seconds() > 20:
                vote = {'started': now, 'senders': set()}
                self.chat_alert_quorum[trigger_key] = vote
            vote['senders'].add(sender)
            if len(vote['senders']) < self.settings.chat_alert_quorum_count:
                return
            self.chat_alert_quorum.pop(trigger_key, None)
        if not self.start_chat_alert_effect('remote'): return
        self.sound_controller.play("remote_ocr")

    @staticmethod
    def channel_from_chat_trigger(trigger: str, text: str):
        value = clean_chat_alert(f"{trigger} {text}")
        checks = {
            "Канал 1": ("м1", "м1к", "m1k", "m1 k", "канал 1"),
            "Канал 2": ("м2", "м2к", "m2k", "m2 k", "канал 2"),
            "Канал 3": ("м3", "м3к", "m3k", "m3 k", "канал 3"),
        }
        words = set(value.split())
        compact = value.replace(" ", "")
        for channel, markers in checks.items():
            for marker in markers:
                normalized = clean_chat_alert(marker)
                if (" " in normalized and normalized in value) or normalized in words or normalized.replace(" ", "") in compact:
                    return channel
        return None

    def start_chat_alert_effect(self, source: str):
        if self.chat_alert_until and datetime.now()<self.chat_alert_until:
            return False
        self.chat_alert_until=datetime.now()+timedelta(seconds=SPAWN_EFFECT_SECONDS)
        self.chat_alert_source=source
        return True

    def cancel_local_chat_alert_effect(self):
        if self.chat_alert_source != 'local':
            return False
        self.chat_alert_until=None
        self.chat_alert_source=None
        if self.tree_block is not None: self.tree_block.set_chat_alert(False)
        if self.overlay_window is not None: self.overlay_window.set_chat_alert(False)
        self.sound_controller.stop("local_ocr")
        return True

    def toggle_sound_muted(self):
        self.settings.sound_muted = not self.settings.sound_muted
        if self.settings.sound_muted:
            self.sound_controller.stop()
        self.settings.save()
        self.update_sound_button()

    def update_sound_button(self):
        if hasattr(self, "sound_btn"):
            self.sound_btn.setIcon(ui_icon("mute" if self.settings.sound_muted else "sound"))
            self.sound_btn.setText("Звук выключен" if self.settings.sound_muted else "Звук включен")
            self.sound_btn.setIconSize(QSize(s(22, self.settings.app_scale), s(22, self.settings.app_scale)))
            self.sound_btn.setProperty("muted", "true" if self.settings.sound_muted else "false")
            self.sound_btn.style().unpolish(self.sound_btn); self.sound_btn.style().polish(self.sound_btn)

    def apply_hotkeys(self):
        if not hasattr(self, "hotkey_manager"):
            return []
        mappings = self.settings.hotkeys if self.settings.hotkeys_enabled else {}
        return self.hotkey_manager.register(mappings)

    def on_hotkey(self, action: str):
        if action.startswith("toggle_channel_"):
            if not self.settings.tree_section_enabled: return
            channel = f"Канал {action.rsplit('_', 1)[-1]}"
            if channel in self.active_timers: self.stop_timer(channel)
            else: self.start_timer(channel, datetime.now())
        elif action.startswith("alert_channel_"):
            if not self.settings.tree_section_enabled: return
            self.announce_spawn(f"Канал {action.rsplit('_', 1)[-1]}")
        elif action == "toggle_chat_tracker":
            if not self.settings.chat_tracker_enabled: return
            self.open_chat_tracker()
            if self.chat_tracker_dialog.worker: self.chat_tracker_dialog.stop_tracking()
            else: self.chat_tracker_dialog.start_tracking()
        elif action == "toggle_sound":
            self.toggle_sound_muted()

    def on_online_changed(self, available: bool):
        self.internet_available = bool(available)
        self.refresh_discord_buttons()
        if self.chat_dialog is not None:
            self.chat_dialog.update_online_state(self.internet_available)
        if self.internet_available:
            QTimer.singleShot(300, self.network.request_history)
            QTimer.singleShot(2200, self.network.request_history)

    def on_admin_command(self, packet: dict):
        if str(packet.get("action") or "") == "state":
            commands = packet.get("commands", [])
            if isinstance(commands, list):
                for command in commands[-1000:]:
                    if isinstance(command, dict) and verify_admin_packet(command):
                        self.on_admin_command(command)
            return
        command_id = str(packet.get("id") or "")
        if command_id:
            if any(str(item.get("id") or "") == command_id for item in self.settings.admin_commands):
                return
            self.settings.admin_commands.append(dict(packet))
            self.settings.admin_commands = self.settings.admin_commands[-1000:]
        action = str(packet.get("action") or "")
        target = str(packet.get("target") or "")
        changed = False
        if action == "clear_chat":
            self.settings.admin_chat_epoch = str(packet.get("timestamp") or datetime.utcnow().isoformat())
            self.chat_history.clear()
            changed = True
        elif action == "delete_message" and target:
            if target not in self.settings.admin_deleted_message_ids:
                self.settings.admin_deleted_message_ids.append(target)
            changed = self.chat_history.delete(target)
        elif action == "ban_user" and target:
            if target not in self.settings.admin_banned_user_ids:
                self.settings.admin_banned_user_ids.append(target)
            changed = self.chat_history.delete_by_author(target)
        elif action == "unban_user" and target:
            if target in self.settings.admin_banned_user_ids:
                self.settings.admin_banned_user_ids.remove(target)
                changed = True
        else:
            return
        self.settings.admin_deleted_message_ids = self.settings.admin_deleted_message_ids[-2000:]
        self.settings.save()
        if changed:
            self.notify_chat_changed(unread=False)

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
                    continue
        threading.Thread(target=worker, daemon=True).start()

    def get_nickname(self):
        return self.settings.discord_nickname.strip() or "Неизвестный"

    def get_avatar_id(self):
        try: return max(-1, min(18, int(self.settings.chat_avatar_id)))
        except Exception: return -1

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
        if self.settings.hide_to_tray and self.tray is not None and self.tray.isVisible(): self.hide_to_tray()
        else: self.quit_app()

    def _is_auxiliary_window(self, widget):
        """Return true for windows owned by the app, never for the overlay."""
        if widget is None or widget is self or widget is self.overlay_window:
            return False
        parent = widget.parentWidget()
        while parent is not None:
            if parent is self:
                return True
            parent = parent.parentWidget()
        return False

    def _hide_auxiliary_windows(self):
        # Keep the exact set that was visible so tray restore does not open
        # windows the user had already closed. The overlay is deliberately
        # excluded by _is_auxiliary_window().
        if self._chat_animation is not None:
            self._chat_animation.stop()
            self._chat_animation = None
        self._hidden_aux_windows = []
        for widget in QApplication.topLevelWidgets():
            if widget.isHidden() or not self._is_auxiliary_window(widget):
                continue
            self._hidden_aux_windows.append(widget)
            widget.hide()

    def _restore_auxiliary_windows(self):
        windows, self._hidden_aux_windows = self._hidden_aux_windows, []
        for widget in windows:
            if widget is not None:
                widget.show()
                widget.raise_()

    def hide_to_tray(self):
        self._hide_auxiliary_windows()
        self._aux_windows_hidden_for_tray = True
        self.hide()

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if self._aux_windows_hidden_for_tray:
            self._aux_windows_hidden_for_tray = False
            self._restore_auxiliary_windows()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self._hide_auxiliary_windows()
            elif self._hidden_aux_windows and not self._aux_windows_hidden_for_tray:
                self._restore_auxiliary_windows()
        super().changeEvent(event)

    def quit_app(self):
        if self._quitting:
            return
        self._quitting = True
        if self.ticker is not None: self.ticker.stop()
        if self.spawn_timer is not None: self.spawn_timer.stop()
        if self.chat_tracker_dialog is not None:self.chat_tracker_dialog.close()
        self.network.stop()
        self.sound_controller.stop()
        if hasattr(self, "hotkey_manager"): self.hotkey_manager.shutdown()
        if self.overlay_window is not None: self.overlay_window.close()
        for widget in QApplication.topLevelWidgets():
            if widget is not self and widget is not self.tray:
                widget.close()
        if self.tray is not None:
            self.tray.hide()
            self.tray.deleteLater()
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.exit(0)

    def closeEvent(self, event):
        if self._quitting:
            event.accept()
            return
        if self.settings.hide_to_tray and self.tray is not None and self.tray.isVisible():
            event.ignore()
            self.hide_to_tray()
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
