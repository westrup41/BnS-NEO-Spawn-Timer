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