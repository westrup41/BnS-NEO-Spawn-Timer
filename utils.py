from datetime import datetime, timedelta
from config import WORLD_BOSS_SCHEDULE, MSK

def s(value: int, scale: float) -> int:
    return max(1, int(round(value * scale)))

def fmt_seconds(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

def split_duration(total_seconds: int):
    total_seconds = max(0, int(total_seconds))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return days, f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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

def next_custom_event(schedule: dict, now_local=None):
    state = custom_event_state(schedule, now_local)
    return state["name"], state["target"], state["seconds"]

def custom_event_state(schedule: dict, now_local=None, appearance_seconds: int = 300):
    # Event follows the local clock and weekday configured on the user's PC.
    now_local = now_local or datetime.now().astimezone()
    targets = []
    for weekday in range(7):
        rows = schedule.get(str(weekday), []) if isinstance(schedule, dict) else []
        for row in rows:
            time_text = str(row.get("time") or "")
            try:
                hour, minute = map(int, time_text.split(":"))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    continue
            except Exception:
                continue
            base_days = weekday - now_local.weekday()
            base = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=base_days)
            name = str(row.get("name") or "No_Text")
            for week_shift in (-7, 0, 7):
                targets.append((base + timedelta(days=week_shift), name))
    if not targets:
        return {"name": "No_Text", "target": None, "seconds": None, "phase": "idle"}
    recent = [item for item in targets if 0 <= (now_local - item[0]).total_seconds() < appearance_seconds]
    if recent:
        target, name = max(recent, key=lambda item: item[0])
        return {"name": name, "target": target, "seconds": None, "phase": "appearing"}
    future = [item for item in targets if item[0] > now_local]
    if not future:
        return {"name": "No_Text", "target": None, "seconds": None, "phase": "idle"}
    target, name = min(future, key=lambda item: item[0])
    return {
        "name": name,
        "target": target,
        "seconds": int((target - now_local).total_seconds()),
        "phase": "countdown",
    }
