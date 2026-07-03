from datetime import timedelta, timezone

APP_VERSION = "v3.0"
SETTINGS_FILE = "boss_timer_settings.json"
USER_SOUNDS_DIR = "user_sounds"
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma"}
FEEDBACK_WEBHOOK_URL = "https://discord.com/api/webhooks/1518467190511108108/mCPyupFdNGFzwYyQRPPWE0yyewj-6_gMYSdDb4Oj5K7QnLTes63xJv1urS_eF5cARNhR"
MSK = timezone(timedelta(hours=3))

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