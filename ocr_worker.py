import argparse
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


if os.name == "nt":
    # Some Paddle dependencies start short-lived helper processes while the
    # models are initialized. Force every such process to stay invisible.
    _original_popen = subprocess.Popen

    class _HiddenPopen(_original_popen):
        def __init__(self, *args, **kwargs):
            kwargs["creationflags"] = int(kwargs.get("creationflags", 0)) | subprocess.CREATE_NO_WINDOW
            startup = kwargs.get("startupinfo") or subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startup
            super().__init__(*args, **kwargs)

    subprocess.Popen = _HiddenPopen


def send(kind, **values):
    # PyInstaller's windowed bootloader may expose stdout through a legacy
    # Windows code page. Write bytes directly so any recognized Unicode
    # character (for example ②) reaches the main process without crashing.
    payload = (json.dumps({"type": kind, **values}, ensure_ascii=False) + "\n").encode("utf-8")
    stream = getattr(sys.stdout, "buffer", None)
    if stream is not None:
        stream.write(payload); stream.flush()
    else:
        os.write(1, payload)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--region", required=True); parser.add_argument("--confidence", type=int, default=45); parser.add_argument("--contrast", default="0")
    args = parser.parse_args(); left, top, width, height = map(int, args.region.split(",")); region = {"left": left, "top": top, "width": width, "height": height}
    import cv2, mss, numpy as np
    from paddleocr import PaddleOCR
    model_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "models"
    ocr = PaddleOCR(text_detection_model_name="PP-OCRv5_mobile_det", text_detection_model_dir=str(model_root / "PP-OCRv5_mobile_det"), text_recognition_model_name="eslav_PP-OCRv5_mobile_rec", text_recognition_model_dir=str(model_root / "eslav_PP-OCRv5_mobile_rec"), use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False, enable_mkldnn=False, cpu_threads=max(2, min(8, os.cpu_count() or 4)))
    send("ready")
    with mss.MSS() as grabber:
        while True:
            started = time.perf_counter(); shot = np.asarray(grabber.grab(region)); frame = cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)
            if args.contrast == "1":
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB); light, a, b = cv2.split(lab); frame = cv2.cvtColor(cv2.merge((cv2.createCLAHE(2.2, (8, 8)).apply(light), a, b)), cv2.COLOR_LAB2BGR)
            result = list(ocr.predict(frame)); rows = []
            if result:
                data = result[0].json.get("res", {}); boxes = data.get("rec_boxes", [])
                for index, (text, score) in enumerate(zip(data.get("rec_texts", []), data.get("rec_scores", []))):
                    if str(text).strip() and float(score) >= args.confidence / 100:
                        box = boxes[index] if index < len(boxes) else [0, index, 0, 0]; rows.append((float(box[1]), float(box[0]), str(text).strip(), round(float(score) * 100, 1)))
            rows.sort(); send("scan", lines=[{"text": row[2], "confidence": row[3]} for row in rows], elapsed=time.perf_counter() - started); time.sleep(.35)


if __name__ == "__main__":
    try: main()
    except Exception:
        try: send("error", text=traceback.format_exc())
        except Exception: pass
        raise SystemExit(1)
