from datetime import timedelta, timezone
from paths import APP_DIR
from paths import APP_DIR, USER_SOUNDS_DIR

APP_VERSION = "v4.2"
APP_NAME = "B&S NEO Spawn Timer"
AUTHOR = "westrup"
GITHUB_URL = "https://github.com/westrup41/BnS-NEO-Spawn-Timer"
TELEGRAM_URL = "https://t.me/westrup"
DISCORD_NAME = "@westrup"
SETTINGS_FILE = APP_DIR / "settings.json"
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma"}
FEEDBACK_WEBHOOK_URL = "https://discord.com/api/webhooks/1518467190511108108/mCPyupFdNGFzwYyQRPPWE0yyewj-6_gMYSdDb4Oj5K7QnLTes63xJv1urS_eF5cARNhR"
MSK = timezone(timedelta(hours=3))
PROTOCOL_VERSION = 2
CHAT_MAX_MESSAGES = 100
CHAT_MAX_LENGTH = 120
CHAT_COOLDOWN = 30
CHAT_MESSAGE_COOLDOWN = 3
CHAT_DUPLICATE_SECONDS = 30
SPAWN_EFFECT_SECONDS = 60
BLINK_INTERVAL_MS = 500
NETWORK_TOPIC = "bnsneo"

# Public half of the application owner's Ed25519 moderation key.  The private
# half is never shipped with the program and is kept by the owner only.
ADMIN_PUBLIC_KEY = "OBMALWu+aVgF0T9arkjVrjGrSL2N6NWgR5rvQwKr0X8="

COLORS = {
    "bg_main": "#313338", "bg_card": "#2B2D31", "bg_panel": "#24262B",
    "bg_input": "#1E1F22", "border": "#3A3D45", "border_soft": "#343741",
    "text_main": "#DBDEE1", "text_soft": "#B5BAC1", "text_muted": "#949BA4",
    "text_disabled": "#6D7480", "accent": "#5865F2", "accent_hover": "#4752C4",
    "danger": "#DA373C", "danger_hover": "#B92B30", "success": "#23A559",
    "success_hover": "#1E8E4B", "timer_hot": "#F23F43",
}

WORLD_BOSS_SCHEDULE = [
    (0, 21, 0, "Древний дракон"), (1, 21, 0, "Полуденный дракон"),
    (2, 21, 0, "Священный дракон"), (3, 21, 0, "Небесный бивень"),
    (4, 21, 0, "Сюань У"), (5, 15, 0, "Полуденный дракон"),
    (5, 21, 0, "Небесный бивень"), (6, 15, 0, "Небесный бивень"),
    (6, 21, 0, "Священный дракон"),
]

BLOCKS = [
    {
        "key": "block1",
        "title": "Императорское древо",
        "names": ["Канал 1", "Канал 2", "Канал 3"],
        "start": timedelta(hours=2),
        "end": timedelta(hours=5),
    },
]

TIMER_DEFS = {name: block for block in BLOCKS for name in block["names"]}
ALL_TIMER_NAMES = list(TIMER_DEFS.keys())
