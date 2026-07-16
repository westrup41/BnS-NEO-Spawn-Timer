from pathlib import Path
import os

APP_NAME = "BnS-NEO-Spawn-Timer"

APP_DIR = Path(os.getenv("LOCALAPPDATA")) / APP_NAME

APP_DIR.mkdir(parents=True, exist_ok=True)

LOGS_DIR = APP_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

USER_SOUNDS_DIR = APP_DIR / "user_sounds"
USER_SOUNDS_DIR.mkdir(exist_ok=True)

CHAT_PREVIEW_PATH = APP_DIR / "chat_tracker_preview.png"
CHAT_LOG_PATH = APP_DIR / "chat_tracker_journal.json"
