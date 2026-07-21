import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QProgressDialog
from dialogs.message_dialog import MessageDialog

from config import APP_VERSION
from paths import APP_DIR


API_URL = "https://api.github.com/repos/westrup41/BnS-NEO-Spawn-Timer/releases/latest"
EXE_ASSET = "BnS-NEO-Spawn-Timer.exe"
AUTO_UPDATE_INTERVAL = timedelta(days=7)


def version_tuple(value):
    result = []
    for part in str(value).lower().lstrip("v").split("."):
        digits = ''.join(ch for ch in part if ch.isdigit())
        result.append(int(digits or 0))
    return tuple((result + [0, 0, 0])[:3])


class UpdateManager(QObject):
    checked = Signal(object, bool)

    def __init__(self, parent):
        super().__init__(parent); self.parent_window = parent; self.checked.connect(self._checked)

    def automatic_check_due(self, now=None):
        now = now or datetime.now(timezone.utc)
        try:
            previous = datetime.fromisoformat(self.parent_window.settings.last_auto_update_check)
            if previous.tzinfo is None:
                previous = previous.replace(tzinfo=timezone.utc)
            return now - previous >= AUTO_UPDATE_INTERVAL
        except (TypeError, ValueError):
            return True

    def check_automatic(self):
        """Run at most once per seven days; manual checks remain unrestricted."""
        now = datetime.now(timezone.utc)
        if not self.automatic_check_due(now):
            return False
        self.parent_window.settings.last_auto_update_check = now.isoformat()
        self.parent_window.settings.save()
        self.check(silent=True)
        return True

    def check(self, silent=True):
        def worker():
            try:
                request = urllib.request.Request(API_URL, headers={"User-Agent": "BnS-NEO-Spawn-Timer"})
                with urllib.request.urlopen(request, timeout=15) as response: payload = json.load(response)
                self.checked.emit(payload, silent)
            except Exception: self.checked.emit(None, silent)
        threading.Thread(target=worker, daemon=True).start()

    def _checked(self, payload, silent):
        if not payload:
            if not silent: MessageDialog(self.parent_window, "Обновление", "Не удалось проверить обновления.").exec()
            return
        remote = str(payload.get("tag_name") or "")
        if version_tuple(remote) <= version_tuple(APP_VERSION):
            if not silent: MessageDialog(self.parent_window, "Обновление", "Установлена актуальная версия.").exec()
            return
        if not MessageDialog(self.parent_window, "Обновление", f"Установить версию {remote}?", ok_text="Установить", cancel_text="Отмена").exec_result(): return
        assets = {str(item.get("name")): str(item.get("browser_download_url")) for item in payload.get("assets", [])}
        url = assets.get(EXE_ASSET)
        if not url: MessageDialog(self.parent_window, "Обновление", "Файл обновления не найден.").exec(); return
        self.download(url)

    def download(self, url):
        if not getattr(sys, "frozen", False): return
        progress = QProgressDialog("Загрузка обновления…", "Отмена", 0, 100, self.parent_window); progress.setMinimumDuration(0); progress.show()
        destination = APP_DIR / "updates" / EXE_ASSET; destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "BnS-NEO-Spawn-Timer"})
            with urllib.request.urlopen(request, timeout=60) as response, open(destination, "wb") as output:
                total = int(response.headers.get("Content-Length") or 0); loaded = 0
                while True:
                    if progress.wasCanceled(): return
                    chunk = response.read(1024 * 1024)
                    if not chunk: break
                    output.write(chunk); loaded += len(chunk)
                    if total: progress.setValue(int(loaded * 100 / total))
                    QApplication.processEvents()
            self.install(destination)
        except Exception as exc: MessageDialog(self.parent_window, "Ошибка обновления", str(exc)).exec()
        finally: progress.close()

    def install(self, source):
        target = Path(sys.executable).resolve(); script = APP_DIR / "updates" / "install_update.ps1"
        content = f"Start-Sleep -Milliseconds 1200\nCopy-Item -LiteralPath '{str(source).replace("'", "''")}' -Destination '{str(target).replace("'", "''")}' -Force\nStart-Process -FilePath '{str(target).replace("'", "''")}'\nRemove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force\n"
        script.write_text(content, encoding="utf-8-sig")
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script)], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.parent_window.quit_app()
