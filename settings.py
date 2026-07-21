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
    experimental_enabled: bool = False
    chat_tracker_enabled: bool = False
    chat_alerts_enabled: bool = False
    chat_region: dict = field(default_factory=dict)
    chat_triggers: list = field(default_factory=lambda: [
        "монарх", "м1", "м2", "м3", "м1к", "м2к", "м3к",
        "m1k", "m2k", "m3k", "m1 k", "m2 k", "m3 k", "дерево",
    ])
    chat_similarity: int = 82
    chat_matching_version: int = 2
    chat_ocr_confidence: int = 45
    chat_contrast: bool = False
    chat_alert_quorum_enabled: bool = False
    chat_alert_quorum_count: int = 2
    chat_auto_timer_enabled: bool = False
    tracker_button_x: int = -1
    tracker_button_y: int = -1
    sound_enabled: bool = True
    sound_muted: bool = False
    incoming_alert_sound_enabled: bool = True
    ocr_sound_enabled: bool = True
    custom_sound_path: str = ""
    sound_volume: int = 50
    hotkeys_enabled: bool = False
    hotkeys: dict = field(default_factory=dict)
    discord_nickname: str = ""
    chat_avatar_id: int = -1
    discord_message: str = "@everyone 🚨 Императорское древо"
    discord_webhooks: list = field(default_factory=lambda: [""] * 10)
    overlay_enabled: bool = False
    overlay_locked: bool = False
    overlay_block1: bool = False
    overlay_block2: bool = False
    overlay_block3: bool = False
    overlay_field_bosses: bool = False
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
    auto_update_enabled: bool = True
    last_auto_update_check: str = ""
    event_enabled: bool = False
    tree_section_enabled: bool = True
    world_section_enabled: bool = True
    field_bosses_enabled: bool = False
    event_schedule: dict = field(default_factory=dict)
    event_appearance_minutes: int = 5
    field_boss_appearance_minutes: int = 5
    field_boss_locations: list = field(default_factory=lambda: [
        {"name": "Остров хранителей", "schedule": {}},
        {"name": "Белые горы", "schedule": {}},
    ])
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
        loaded_data = {}
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
                if isinstance(data, dict):
                    loaded_data = data
                for key in settings.__dataclass_fields__:
                    if key in loaded_data:
                        setattr(settings, key, loaded_data[key])
            except Exception:
                pass
        settings.overlay_alpha = max(0.05, min(1.00, float(settings.overlay_alpha)))
        settings.app_scale = max(0.82, min(1.22, float(settings.app_scale)))
        try:
            settings.theme_choice_version = int(settings.theme_choice_version)
        except Exception:
            settings.theme_choice_version = 0
        if settings.theme_choice_version < 1:
            settings.ui_theme = "classic"
            settings.theme_choice_version = 1
            theme_migrated = True
        elif str(settings.ui_theme) not in {"classic", "midnight", "starlight", "blade_soul"}:
            settings.ui_theme = "classic"
        settings.overlay_scale = max(0.70, min(1.60, float(settings.overlay_scale)))
        settings.experimental_enabled = bool(settings.experimental_enabled)
        settings.chat_tracker_enabled = bool(settings.chat_tracker_enabled)
        settings.chat_alerts_enabled = bool(settings.chat_alerts_enabled)
        settings.chat_alert_quorum_enabled = bool(settings.chat_alert_quorum_enabled)
        settings.chat_auto_timer_enabled = bool(settings.chat_auto_timer_enabled)
        try: settings.chat_alert_quorum_count = max(2, min(5, int(settings.chat_alert_quorum_count)))
        except Exception: settings.chat_alert_quorum_count = 2
        if not isinstance(settings.chat_region, dict): settings.chat_region = {}
        if not isinstance(settings.chat_triggers, list): settings.chat_triggers = []
        settings.chat_triggers = list(dict.fromkeys(
            str(value).strip()[:80] for value in settings.chat_triggers if str(value).strip()
        ))[:100]
        try: settings.chat_similarity = max(50, min(100, int(settings.chat_similarity)))
        except Exception: settings.chat_similarity = 82
        try: settings.chat_matching_version = int(settings.chat_matching_version)
        except Exception: settings.chat_matching_version = 0
        if settings.chat_matching_version < 2:
            if settings.chat_similarity == 76:
                settings.chat_similarity = 82
            settings.chat_matching_version = 2
            theme_migrated = True
        try: settings.chat_ocr_confidence = max(10, min(95, int(settings.chat_ocr_confidence)))
        except Exception: settings.chat_ocr_confidence = 45
        settings.chat_contrast = bool(settings.chat_contrast)
        if not isinstance(settings.active_timers, dict):
            settings.active_timers = {}
        if not isinstance(settings.discord_webhooks, list):
            settings.discord_webhooks = [""] * 10
        settings.discord_webhooks = (settings.discord_webhooks + [""] * 10)[:10]
        settings.discord_nickname = str(settings.discord_nickname or "")
        settings.discord_nickname = settings.discord_nickname[:16]
        try: settings.chat_avatar_id = max(-1, min(18, int(settings.chat_avatar_id)))
        except Exception: settings.chat_avatar_id = -1
        settings.custom_sound_path = str(settings.custom_sound_path or "")
        settings.network_enabled = bool(settings.network_enabled)
        settings.online_room_private = bool(settings.online_room_private)
        settings.online_room_code = str(settings.online_room_code or "")[:64]
        settings.chat_enabled = bool(settings.chat_enabled)
        settings.global_notifications = bool(settings.global_notifications)
        settings.incoming_alert_sound_enabled = bool(settings.incoming_alert_sound_enabled)
        settings.ocr_sound_enabled = bool(settings.ocr_sound_enabled)
        settings.hide_to_tray = bool(settings.hide_to_tray)
        settings.auto_update_enabled = bool(settings.auto_update_enabled)
        settings.last_auto_update_check = str(settings.last_auto_update_check or "")
        settings.event_enabled = bool(settings.event_enabled)
        settings.tree_section_enabled = bool(settings.tree_section_enabled)
        settings.world_section_enabled = bool(settings.world_section_enabled)
        settings.field_bosses_enabled = bool(settings.field_bosses_enabled)
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
                    "name": ("Неизвестный босс" if str(row.get("name") or "").strip().casefold() in {"", "no_text", "no text"} else str(row.get("name")))[:30],
                    "time": str(row.get("time") or "")[:5],
                })
            while len(cleaned) < 3:
                cleaned.append({"name": "Неизвестный босс", "time": ""})
            normalized_schedule[str(day)] = cleaned
        settings.event_schedule = normalized_schedule
        try: settings.field_boss_appearance_minutes = max(1, min(59, int(settings.field_boss_appearance_minutes)))
        except Exception: settings.field_boss_appearance_minutes = 5
        defaults = ["Остров хранителей", "Белые горы"]
        raw_locations = settings.field_boss_locations if isinstance(settings.field_boss_locations, list) else []
        normalized_locations = []
        for index in range(2):
            raw = raw_locations[index] if index < len(raw_locations) and isinstance(raw_locations[index], dict) else {}
            raw_schedule = raw.get("schedule") if isinstance(raw.get("schedule"), dict) else {}
            schedule = {}
            for day in range(7):
                rows = raw_schedule.get(str(day), raw_schedule.get(day, []))
                cleaned_rows = []
                if isinstance(rows, list):
                    for row in rows[:20]:
                        if not isinstance(row, dict): continue
                        name = str(row.get("name") or "").strip()[:20]
                        time_text = str(row.get("time") or "").strip()[:5]
                        if name or time_text: cleaned_rows.append({"name": name, "time": time_text})
                schedule[str(day)] = cleaned_rows
            normalized_locations.append({
                "name": defaults[index],
                "schedule": schedule,
            })
        settings.field_boss_locations = normalized_locations
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
        settings.sound_muted = bool(settings.sound_muted)
        if loaded_data and "sound_volume" not in loaded_data:
            legacy_volumes = []
            for field_name in ("timer_sound_volume", "manual_alert_volume"):
                try: legacy_volumes.append(max(0, min(100, int(loaded_data[field_name]))))
                except Exception: pass
            if legacy_volumes:
                settings.sound_volume = round(sum(legacy_volumes) / len(legacy_volumes))
                theme_migrated = True
        try: settings.sound_volume = max(0, min(100, int(settings.sound_volume)))
        except Exception: settings.sound_volume = 50
        settings.hotkeys_enabled = bool(settings.hotkeys_enabled)
        if not isinstance(settings.hotkeys, dict): settings.hotkeys = {}
        settings.hotkeys = {str(key)[:40]: str(value)[:40] for key, value in settings.hotkeys.items() if str(value).strip()}
        if not settings.overlay_enabled:
            settings.overlay_block1 = False
            settings.overlay_block2 = False
            settings.overlay_block3 = False
            settings.overlay_field_bosses = False
        settings.overlay_block1 = bool(settings.overlay_block1 and settings.tree_section_enabled)
        settings.overlay_block2 = bool(settings.overlay_block2 and settings.event_enabled)
        settings.overlay_field_bosses = bool(settings.overlay_field_bosses and settings.field_bosses_enabled)
        settings.overlay_block3 = bool(settings.overlay_block3 and settings.world_section_enabled)
        settings.overlay_enabled = bool(settings.overlay_enabled and any((
            settings.overlay_block1,
            settings.overlay_block2,
            settings.overlay_field_bosses,
            settings.overlay_block3,
        )))
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

    def reset_user_settings(self):
        """Restore user-facing preferences without touching moderation state or identity."""
        defaults = type(self)()
        protected = {
            "admin_chat_epoch", "admin_deleted_message_ids", "admin_banned_user_ids",
            "admin_commands", "blocked_alert_user_ids", "blocked_alert_users",
            "blocked_chat_users",
        }
        for key in self.__dataclass_fields__:
            if key not in protected:
                setattr(self, key, getattr(defaults, key))
        self.save()

    def export_public(self):
        """Portable user configuration; identity keys and transient state are excluded."""
        excluded = {"active_timers", "online_room_private", "online_room_code", "last_auto_update_check", "admin_chat_epoch",
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
        protected = {"active_timers", "online_room_private", "online_room_code", "last_auto_update_check", "admin_chat_epoch",
                     "admin_deleted_message_ids", "admin_banned_user_ids", "admin_commands"}
        for key in self.__dataclass_fields__:
            if key in values and key not in protected:
                setattr(self, key, values[key])
        if "sound_volume" not in values:
            legacy_volumes = []
            for field_name in ("timer_sound_volume", "manual_alert_volume"):
                try: legacy_volumes.append(max(0, min(100, int(values[field_name]))))
                except Exception: pass
            if legacy_volumes:
                self.sound_volume = round(sum(legacy_volumes) / len(legacy_volumes))
        self.save()
