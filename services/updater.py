import json
import urllib.request
from datetime import datetime, timedelta

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

        return {
            "version": data.get("tag_name", ""),
            "url": data.get("html_url", ""),
            "body": data.get("body", "")
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
            return latest != APP_VERSION
        
    def check(self, force=False):
        if not force and not self.should_check():
            return None

        self.settings.last_update_check = datetime.now().isoformat()
        self.settings.save()

        try:
            latest = self.fetch_latest()
        except Exception:
            return None

        if not latest:
            return None

        if not self.versions_different(latest["version"]):
            return None

        return latest