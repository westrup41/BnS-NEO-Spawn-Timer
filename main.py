import sys, os, json, subprocess
from pathlib import Path

# PaddleOCR probes the Windows environment through short-lived helper
# processes. In a windowed build they must stay invisible as well.
if os.name == "nt" and getattr(sys, "frozen", False):
    _original_popen = subprocess.Popen
    class _HiddenPopen(_original_popen):
        def __init__(self, *args, **kwargs):
            kwargs["creationflags"] = int(kwargs.get("creationflags", 0)) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            super().__init__(*args, **kwargs)
    subprocess.Popen = _HiddenPopen

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSharedMemory
from app import MainWindow
from config import APP_VERSION

def main():
    if os.environ.get("BNS_V5_OCR_SELFTEST") == "1":
        try:
            import cv2, numpy as np
            from services.chat_ocr import create_engine
            image=np.zeros((150,620,3),dtype=np.uint8)
            cv2.putText(image,"M1K TREE",(20,90),cv2.FONT_HERSHEY_SIMPLEX,1.4,(255,255,255),2)
            result=list(create_engine().predict(image));payload={"ok":True,"result_count":len(result)}
        except Exception as exc:
            import traceback;payload={"ok":False,"error":str(exc),"traceback":traceback.format_exc()}
        path=Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path.cwd()
        (path/"v5_ocr_selftest.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        return
    app = QApplication(sys.argv)
    
    shared = QSharedMemory("BnSNeoSpawnTimer")
    
    if not shared.create(1):
        print("Программа уже запущена.")
        return
    app.shared_memory = shared
    app.setApplicationName("B&S NEO Spawn Timer")
    app.setApplicationDisplayName("B&S NEO Spawn Timer")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("westrup")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
