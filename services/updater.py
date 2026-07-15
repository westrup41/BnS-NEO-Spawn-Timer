import json
import hashlib
import os
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from config import APP_VERSION, GITHUB_URL

LATEST_RELEASE_URL = (
    GITHUB_URL.replace("https://github.com/", "https://api.github.com/repos/")
    + "/releases/latest"
)


class UpdateManager:

    def __init__(self, settings):
        self.settings = settings

    def should_check(self):
        interval = self.settings.update_check_interval

        if interval == "never":
            return False

        if not self.settings.last_update_check:
            return True

        try:
            last = datetime.fromisoformat(self.settings.last_update_check)
        except Exception:
            return True

        now = datetime.now()

        if interval == "week":
            return now - last >= timedelta(days=7)

        if interval == "month":
            return now - last >= timedelta(days=30)

        return False

    def fetch_latest(self):
        request = urllib.request.Request(
            LATEST_RELEASE_URL,
            headers={
                "User-Agent": "BNS-NEO-Spawn-Timer"
            }
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode())

        assets = data.get("assets") if isinstance(data.get("assets"), list) else []
        exe = next((item for item in assets if str(item.get("name", "")).casefold() == "bns-neo-spawn-timer.exe"), {})
        checksum = next((item for item in assets if str(item.get("name", "")).casefold() == "bns-neo-spawn-timer.exe.sha256"), {})
        return {
            "version": data.get("tag_name", ""),
            "url": data.get("html_url", ""),
            "body": data.get("body", ""),
            "exe_url": exe.get("browser_download_url", ""),
            "exe_name": exe.get("name", "BnS-NEO-Spawn-Timer.exe"),
            "digest": str(exe.get("digest") or ""),
            "sha256_url": checksum.get("browser_download_url", ""),
        }

    def versions_different(self, latest):
        def normalize(version):
            version = version.lower().strip()

            if version.startswith("v"):
                version = version[1:]

            return tuple(int(part) for part in version.split("."))

        try:
            return normalize(latest) > normalize(APP_VERSION)
        except Exception:
            return False
        
    def check(self, force=False):
        return self.check_with_status(force=force).get("update")

    def check_with_status(self, force=False):
        if not force and not self.should_check():
            return {"status": "skipped", "update": None}

        try:
            latest = self.fetch_latest()
        except Exception as exc:
            return {"status": "error", "update": None, "error": str(exc)}

        if not latest:
            return {"status": "error", "update": None}

        self.settings.last_update_check = datetime.now().isoformat()
        self.settings.save()

        if not self.versions_different(latest["version"]):
            return {"status": "current", "update": None, "latest": latest.get("version", "")}

        return {"status": "update", "update": latest}

    def download_verified(self, update: dict):
        exe_url = str(update.get("exe_url") or "")
        if not exe_url:
            raise RuntimeError("В релизе нет exe-файла")
        request = urllib.request.Request(exe_url, headers={"User-Agent": "BNS-NEO-Spawn-Timer"})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read(300 * 1024 * 1024)
        actual = hashlib.sha256(payload).hexdigest().lower()
        expected = ""
        digest = str(update.get("digest") or "")
        if digest.lower().startswith("sha256:"):
            expected = digest.split(":", 1)[1].strip().lower()
        if not expected and update.get("sha256_url"):
            checksum_request = urllib.request.Request(
                update["sha256_url"], headers={"User-Agent": "BNS-NEO-Spawn-Timer"}
            )
            with urllib.request.urlopen(checksum_request, timeout=15) as response:
                expected = response.read(4096).decode("ascii", "ignore").strip().split()[0].lower()
        if len(expected) != 64 or actual != expected:
            raise RuntimeError("SHA-256 новой версии не совпадает или отсутствует")
        from paths import APP_DIR
        update_dir = APP_DIR / "updates"
        update_dir.mkdir(parents=True, exist_ok=True)
        target_name = Path(str(update.get("exe_name") or "BnS-NEO-Spawn-Timer.exe")).name
        if target_name.casefold() != "bns-neo-spawn-timer.exe":
            raise RuntimeError("Неверное имя exe-файла обновления")
        target = update_dir / target_name
        target.write_bytes(payload)
        return target

    def install_and_restart(self, downloaded_path):
        if not getattr(sys, "frozen", False):
            raise RuntimeError("Автозамена доступна только в собранной версии")
        current = os.path.abspath(sys.executable)
        downloaded = os.path.abspath(str(downloaded_path))
        script = os.path.join(tempfile.gettempdir(), "bns_neo_update.ps1")
        escaped_current = current.replace("'", "''")
        escaped_downloaded = downloaded.replace("'", "''")
        body = (
            f"$pidToWait={os.getpid()}\n"
            "Wait-Process -Id $pidToWait -ErrorAction SilentlyContinue\n"
            f"Copy-Item -LiteralPath '{escaped_downloaded}' -Destination '{escaped_current}' -Force\n"
            f"Start-Process -FilePath '{escaped_current}'\n"
            "Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force\n"
        )
        with open(script, "w", encoding="utf-8-sig") as file:
            file.write(body)
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
