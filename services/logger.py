from datetime import datetime
from paths import LOGS_DIR


def log(message: str):
    now = datetime.now()

    logfile = LOGS_DIR / f"{now:%Y-%m-%d}.log"

    try:
        with logfile.open("a", encoding="utf-8") as f:
            f.write(f"[{now:%H:%M:%S}] {message}\n")
    except Exception:
        pass