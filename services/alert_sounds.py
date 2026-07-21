from PySide6.QtCore import QObject

from services.audio import play_alert, stop_alert_sound


class AlertSoundController(QObject):
    CATEGORIES = {"timer", "manual", "local_ocr", "remote_ocr"}

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings

    def play(self, category: str):
        if self.settings.sound_muted or category not in self.CATEGORIES:
            return False
        volume = int(getattr(self.settings, "sound_volume", 50))
        if category == "timer":
            enabled = self.settings.sound_enabled
        elif category == "manual":
            enabled = self.settings.incoming_alert_sound_enabled
        else:
            enabled = self.settings.ocr_sound_enabled
        if not enabled:
            return False
        return play_alert(enabled, self.settings.custom_sound_path, volume)

    def stop(self, category=None):
        stop_alert_sound()
