from datetime import datetime, timedelta
from config import WORLD_BOSS_SCHEDULE, MSK

def s(value: int, scale: float) -> int:
    return max(1, int(round(value * scale)))

def fmt_seconds(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

def next_world_boss(now_msk=None):
    now_msk = now_msk or datetime.now(MSK)
    best_target = None
    best_name = "—"
    best_delta = timedelta(days=365)
    for weekday, hour, minute, name in WORLD_BOSS_SCHEDULE:
        days_ahead = weekday - now_msk.weekday()
        if days_ahead < 0:
            days_ahead += 7
        target = now_msk.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
        if target <= now_msk:
            target += timedelta(days=7)
        delta = target - now_msk
        if delta < best_delta:
            best_delta = delta
            best_target = target
            best_name = name
    return best_name, best_target, int(best_delta.total_seconds())