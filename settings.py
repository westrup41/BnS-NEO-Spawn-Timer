import json
import os
import shutil
import threading
from pathlib import Path
from paths import APP_DIR
from dataclasses import dataclass, field
from config import SETTINGS_FILE


_SETTINGS_SAVE_LOCK = threading.RLock()

@dataclass
class AppSettings:
    sound_enabled: bool = True
    incoming_alert_sound_enabled: bool = True
    custom_sound_path: str = ""
    sound_volume: int = 50
    discord_nickname: str = ""
    discord_message: str = "@everyone 🚨 Императорское древо"
    discord_webhooks: list = field(default_factory=lambda: [""] * 10)
    update_check_interval: str = "week"
    last_update_check: str = ""
    overlay_enabled: bool = False
    overlay_locked: bool = False
    overlay_block1: bool = False
    overlay_block2: bool = False
    overlay_block3: bool = False
    overlay_pos_x: int = 100
    overlay_pos_y: int = 100
    # 6% transparency matches the previous visual default. The overlay card
    # itself is now fully opaque at 0%; all transparency comes from this value.
    overlay_alpha: float = 0.94
    app_scale: float = 1.02
    ui_theme: str = "classic"
    theme_choice_version: int = 0
    overlay_scale: float = 1.15
    active_timers: dict = field(default_factory=dict)
    
    network_enabled: bool = True
    online_room_private: bool = False
    online_room_code: str = ""
    chat_enabled: bool = True
    global_notifications: bool = True
    hide_to_tray: bool = True
    event_enabled: bool = False
    event_schedule: dict = field(default_factory=dict)
    event_appearance_minutes: int = 5
    blocked_alert_user_ids: list = field(default_factory=list)
    blocked_alert_users: dict = field(default_factory=dict)
    blocked_chat_users: dict = field(default_factory=dict)
    admin_chat_epoch: str = ""
    admin_deleted_message_ids: list = field(default_factory=list)
    admin_banned_user_ids: list = field(default_factory=list)
    admin_commands: list = field(default_factory=list)

    @classmethod
    def load(cls):
        settings = cls()
        theme_migrated = False
        legacy_settings = Path("boss_timer_settings.json")
        
        if not os.path.exists(SETTINGS_FILE) and legacy_settings.exists():
            try:
                shutil.move(str(legacy_settings), str(SETTINGS_FILE))
            except Exception:
                pass
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
                    data = json.load(file)
                for key in settings.__dataclass_fields__:
                    if key in data:
                        setattr(settings, key, data[key])
            except Exception:
                pass
        settings.overlay_alpha = max(0.00, min(1.00, float(settings.overlay_alpha)))
        settings.app_scale = max(0.82, min(1.22, float(settings.app_scale)))
        try:
            settings.theme_choice_version = int(settings.theme_choice_version)
        except Exception:
            settings.theme_choice_version = 0
        if settings.theme_choice_version < 1:
            settings.ui_theme = "classic"
            settings.theme_choice_version = 1
            theme_migrated = True
        elif str(settings.ui_theme) not in {"classic", "midnight", "starlight"}:
            settings.ui_theme = "classic"
        settings.overlay_scale = max(0.70, min(1.60, float(settings.overlay_scale)))
        if not isinstance(settings.active_timers, dict):
            settings.active_timers = {}
        if not isinstance(settings.discord_webhooks, list):
            settings.discord_webhooks = [""] * 10
        settings.discord_webhooks = (settings.discord_webhooks + [""] * 10)[:10]
        settings.discord_nickname = str(settings.discord_nickname or "")
        settings.discord_nickname = settings.discord_nickname[:16]
        settings.custom_sound_path = str(settings.custom_sound_path or "")
        settings.network_enabled = bool(settings.network_enabled)
        settings.online_room_private = bool(settings.online_room_private)
        settings.online_room_code = str(settings.online_room_code or "")[:64]
        settings.chat_enabled = bool(settings.chat_enabled)
        settings.global_notifications = bool(settings.global_notifications)
        settings.incoming_alert_sound_enabled = bool(settings.incoming_alert_sound_enabled)
        settings.hide_to_tray = bool(settings.hide_to_tray)
        settings.event_enabled = bool(settings.event_enabled)
        try:
            settings.event_appearance_minutes = max(1, min(59, int(settings.event_appearance_minutes)))
        except Exception:
            settings.event_appearance_minutes = 5
        if not isinstance(settings.event_schedule, dict):
            settings.event_schedule = {}
        normalized_schedule = {}
        for day in range(7):
            rows = settings.event_schedule.get(str(day), settings.event_schedule.get(day, []))
            if not isinstance(rows, list):
                rows = []
            cleaned = []
            for row in rows[:10]:
                if not isinstance(row, dict):
                    continue
                cleaned.append({
                    "name": str(row.get("name") or "No_Text")[:30],
                    "time": str(row.get("time") or "")[:5],
                })
            while len(cleaned) < 3:
                cleaned.append({"name": "No_Text", "time": ""})
            normalized_schedule[str(day)] = cleaned
        settings.event_schedule = normalized_schedule
        if not isinstance(settings.blocked_alert_user_ids, list):
            settings.blocked_alert_user_ids = []
        settings.blocked_alert_user_ids = list(dict.fromkeys(
            str(user_id) for user_id in settings.blocked_alert_user_ids if str(user_id).strip()
        ))[:500]
        if not isinstance(settings.blocked_alert_users, dict):
            settings.blocked_alert_users = {}
        normalized_blocked = {
            str(user_id): str(nickname or "Неизвестный")[:16]
            for user_id, nickname in settings.blocked_alert_users.items()
            if str(user_id).strip()
        }
        for user_id in settings.blocked_alert_user_ids:
            normalized_blocked.setdefault(user_id, "Неизвестный")
        settings.blocked_alert_users = dict(list(normalized_blocked.items())[:500])
        settings.blocked_alert_user_ids = list(settings.blocked_alert_users)
        if not isinstance(settings.blocked_chat_users, dict):
            settings.blocked_chat_users = {}
        settings.blocked_chat_users = {
            str(user_id): str(nickname or "Неизвестный")[:16]
            for user_id, nickname in settings.blocked_chat_users.items()
            if str(user_id).strip()
        }
        if not isinstance(settings.admin_deleted_message_ids, list):
            settings.admin_deleted_message_ids = []
        settings.admin_deleted_message_ids = list(dict.fromkeys(
            str(value) for value in settings.admin_deleted_message_ids if str(value).strip()
        ))[-2000:]
        if not isinstance(settings.admin_banned_user_ids, list):
            settings.admin_banned_user_ids = []
        settings.admin_banned_user_ids = list(dict.fromkeys(
            str(value) for value in settings.admin_banned_user_ids if str(value).strip()
        ))[-1000:]
        settings.admin_chat_epoch = str(settings.admin_chat_epoch or "")
        if not isinstance(settings.admin_commands, list):
            settings.admin_commands = []
        settings.admin_commands = [item for item in settings.admin_commands[-1000:] if isinstance(item, dict)]
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
            settings.overlay_block2 = False
            settings.overlay_block3 = False
        if not settings.event_enabled:
            settings.overlay_block2 = False
        if theme_migrated:
            try:
                settings.save()
            except OSError:
                pass
        return settings

    def save(self):
        with _SETTINGS_SAVE_LOCK:
            data = {key: getattr(self, key) for key in self.__dataclass_fields__}
            temp_path = SETTINGS_FILE.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, SETTINGS_FILE)

    def export_public(self):
        """Portable user configuration; identity keys and transient state are excluded."""
        excluded = {"last_update_check", "active_timers", "online_room_private", "online_room_code", "admin_chat_epoch",
                    "admin_deleted_message_ids", "admin_banned_user_ids", "admin_commands"}
        return {
            "format": "bns-neo-settings",
            "version": 1,
            "settings": {
                key: getattr(self, key) for key in self.__dataclass_fields__
                if key not in excluded
            },
        }

    def import_public(self, payload):
        if not isinstance(payload, dict) or payload.get("format") != "bns-neo-settings":
            raise ValueError("Это не файл настроек B&S NEO Spawn Timer")
        values = payload.get("settings")
        if not isinstance(values, dict):
            raise ValueError("Файл настроек повреждён")
        protected = {"last_update_check", "active_timers", "online_room_private", "online_room_code", "admin_chat_epoch",
                     "admin_deleted_message_ids", "admin_banned_user_ids", "admin_commands"}
        for key in self.__dataclass_fields__:
            if key in values and key not in protected:
                setattr(self, key, values[key])
        self.save()
