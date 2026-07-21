import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal


WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


class _NativeFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, event_type, message):
        try:
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == WM_HOTKEY:
                self.callback(int(msg.wParam))
                return True, 0
        except Exception:
            pass
        return False, 0


class GlobalHotkeyManager(QObject):
    triggered = Signal(str)

    def __init__(self, application, parent=None):
        super().__init__(parent)
        self.application = application
        self.filter = _NativeFilter(self._trigger)
        self.application.installNativeEventFilter(self.filter)
        self.actions = {}
        self.user32 = ctypes.windll.user32

    def clear(self):
        for identifier in list(self.actions):
            try: self.user32.UnregisterHotKey(None, identifier)
            except Exception: pass
        self.actions.clear()

    def register(self, mappings: dict):
        self.clear()
        failed = []
        for offset, (action, sequence) in enumerate(mappings.items()):
            parsed = self._parse(sequence)
            if not parsed:
                continue
            modifiers, key = parsed
            identifier = 0xB500 + offset
            if self.user32.RegisterHotKey(None, identifier, modifiers | MOD_NOREPEAT, key):
                self.actions[identifier] = action
            else:
                failed.append(action)
        return failed

    def _trigger(self, identifier):
        action = self.actions.get(identifier)
        if action: self.triggered.emit(action)

    @staticmethod
    def _parse(sequence):
        parts = [part.strip() for part in str(sequence or "").replace("Meta", "Win").split("+") if part.strip()]
        if not parts: return None
        modifiers = 0
        mapping = {"ctrl": MOD_CONTROL, "control": MOD_CONTROL, "alt": MOD_ALT,
                   "shift": MOD_SHIFT, "win": MOD_WIN}
        for part in parts[:-1]:
            modifiers |= mapping.get(part.casefold(), 0)
        key_name = parts[-1].upper()
        if len(key_name) == 1 and key_name.isalnum(): key = ord(key_name)
        elif key_name.startswith("F") and key_name[1:].isdigit() and 1 <= int(key_name[1:]) <= 24:
            key = 0x70 + int(key_name[1:]) - 1
        else:
            key = {"SPACE": 0x20, "TAB": 0x09, "HOME": 0x24, "END": 0x23,
                   "PAGEUP": 0x21, "PAGEDOWN": 0x22, "INSERT": 0x2D}.get(key_name)
        return (modifiers, key) if key else None

    def shutdown(self):
        self.clear()
        try: self.application.removeNativeEventFilter(self.filter)
        except Exception: pass

