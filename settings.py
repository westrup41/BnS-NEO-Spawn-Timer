import json
import os
import shutil
from pathlib import Path
from paths import APP_DIR
from dataclasses import dataclass, field
from config import SETTINGS_FILE

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
    overlay_alpha: float = 1.00
    app_scale: float = 1.02
    overlay_scale: float = 1.15
    active_timers: dict = field(default_factory=dict)
    
    network_enabled: bool = True
    chat_enabled: bool = True
    global_notifications: bool = True
    hide_to_tray: bool = True
    event_enabled: bool = False
    event_schedule: dict = field(default_factory=dict)
    event_appearance_minutes: int = 5
    blocked_alert_user_ids: list = field(default_factory=list)
    blocked_alert_users: dict = field(default_factory=dict)

    @classmethod
    def load(cls):
        settings = cls()
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
        return settings

    def save(self):
        data = {key: getattr(self, key) for key in self.__dataclass_fields__}
        with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
