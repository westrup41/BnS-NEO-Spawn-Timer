import os
import shutil
import struct
import math
import tempfile
import threading
import wave
import sys
from PySide6.QtCore import QTimer, QUrl

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_QT_MULTIMEDIA = True
except Exception:
    QAudioOutput = None
    QMediaPlayer = None
    HAS_QT_MULTIMEDIA = False

try:
    import winsound
    HAS_SOUND = True
except Exception:
    HAS_SOUND = False

from config import SUPPORTED_AUDIO_EXTENSIONS, USER_SOUNDS_DIR

ALERT_WAV_PATH = os.path.join(tempfile.gettempdir(), "bs_neo_soft_chime_v3.wav")
_MEDIA_PLAYERS = []

def ensure_alert_wav() -> str:
    if os.path.exists(ALERT_WAV_PATH) and os.path.getsize(ALERT_WAV_PATH) > 1024:
        return ALERT_WAV_PATH
    sample_rate = 44100
    volume = 0.13
    duration = 0.78
    notes = [
        (0.00, 523.25, 0.42, 1.00),
        (0.13, 659.25, 0.46, 0.82),
        (0.27, 783.99, 0.50, 0.68),
    ]
    frames = []
    count = int(sample_rate * duration)
    for index in range(count):
        t = index / sample_rate
        sample = 0.0
        for start, frequency, length, strength in notes:
            local_t = t - start
            if local_t < 0 or local_t > length:
                continue
            attack = min(1.0, local_t / 0.018)
            release = max(0.0, 1.0 - local_t / length)
            envelope = attack * release * release * strength
            tone = math.sin(2 * math.pi * frequency * local_t)
            shimmer = 0.16 * math.sin(2 * math.pi * frequency * 2.01 * local_t)
            sample += (tone + shimmer) * envelope
        sample *= volume
        frames.append(struct.pack("<h", max(-32767, min(32767, int(sample * 32767)))))
    with wave.open(ALERT_WAV_PATH, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(frames))
    return ALERT_WAV_PATH

def resolve_audio_path(path: str) -> str:
    path = (path or "").strip().strip('"')
    if not path: return ""
    if os.path.isabs(path): return path
    return str(USER_SOUNDS_DIR / path)

def copy_custom_sound_to_storage(source_path: str) -> str:
    source_path = resolve_audio_path(source_path)
    if not source_path or not os.path.exists(source_path):
        return ""
    ext = os.path.splitext(source_path)[1].lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        return ""
    folder = USER_SOUNDS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    dest_name = f"custom_timer_sound{ext}"
    dest = folder / dest_name
    if os.path.abspath(source_path) != os.path.abspath(dest):
        shutil.copy2(source_path, dest)
    return dest.name

def _finish_media_player(player):
    if getattr(player, "_finish_called", False): return
    player._finish_called = True
    callback = getattr(player, "_finish_callback", None)
    if callback is not None:
        try: callback()
        except Exception: pass

def _cleanup_media_player(player, call_callback: bool = True):
    try:
        if call_callback: _finish_media_player(player)
        if player in _MEDIA_PLAYERS: _MEDIA_PLAYERS.remove(player)
        player.stop()
        player.deleteLater()
    except Exception: pass

def _play_with_qt_multimedia(path: str, volume_percent: int = 100, on_finished=None) -> bool:
    if not HAS_QT_MULTIMEDIA: return False
    try:
        player = QMediaPlayer()
        audio_output = QAudioOutput()
        volume = max(0.0, min(1.0, float(volume_percent) / 100.0))
        audio_output.setVolume(volume)
        player.setAudioOutput(audio_output)
        player._audio_output = audio_output
        player._finish_callback = on_finished
        player._finish_called = False
        _MEDIA_PLAYERS.append(player)
        def finish_cleanup(*args):
            _finish_media_player(player)
            QTimer.singleShot(800, lambda: _cleanup_media_player(player, call_callback=False))
        try:
            player.mediaStatusChanged.connect(
                lambda status: finish_cleanup() if status in (QMediaPlayer.MediaStatus.EndOfMedia, QMediaPlayer.MediaStatus.InvalidMedia) else None
            )
            player.errorOccurred.connect(lambda *args: finish_cleanup())
        except Exception: pass
        player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        player.play()
        return True
    except Exception: return False

def _wav_duration_ms(path: str, default_ms: int = 1800) -> int:
    try:
        with wave.open(path, "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate() or 44100
            return max(300, int(frames * 1000 / rate) + 250)
    except Exception: return default_ms

def stop_alert_sound():
    for player in list(_MEDIA_PLAYERS):
        try:
            player.stop()
            _cleanup_media_player(player)
        except Exception: pass
    if HAS_SOUND:
        try: winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            try: winsound.PlaySound(None, 0)
            except Exception: pass

def play_alert(sound_enabled: bool, custom_sound_path: str = "", volume_percent: int = 50, on_finished=None) -> bool:
    try: volume_percent = max(0, min(100, int(volume_percent)))
    except Exception: volume_percent = 50
    if not sound_enabled or volume_percent <= 0:
        if on_finished is not None: QTimer.singleShot(0, on_finished)
        return False
    sound_path = resolve_audio_path(custom_sound_path)
    if sound_path and os.path.exists(sound_path):
        if _play_with_qt_multimedia(sound_path, volume_percent, on_finished=on_finished): return True
        ext = os.path.splitext(sound_path)[1].lower()
        if ext == ".wav" and HAS_SOUND:
            def wav_worker():
                try: winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception: pass
            threading.Thread(target=wav_worker, daemon=True).start()
            if on_finished is not None: QTimer.singleShot(_wav_duration_ms(sound_path), on_finished)
            return True
    default_path = ensure_alert_wav()
    if _play_with_qt_multimedia(default_path, volume_percent, on_finished=on_finished): return True
    if not HAS_SOUND:
        if on_finished is not None: QTimer.singleShot(0, on_finished)
        return False
    def worker():
        try: winsound.PlaySound(default_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            try:
                winsound.Beep(523, 120)
                winsound.Beep(659, 150)
            except Exception: pass
    threading.Thread(target=worker, daemon=True).start()
    if on_finished is not None: QTimer.singleShot(_wav_duration_ms(default_path), on_finished)
    return True
