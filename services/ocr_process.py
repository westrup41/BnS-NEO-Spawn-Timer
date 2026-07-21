import json
import re
import time

from PySide6.QtCore import QObject, QProcess, Signal

from services.ocr_pack import OCR_WORKER


class OCRProcess(QObject):
    ready = Signal(); scan = Signal(list, float); error = Signal(str); stopped = Signal()

    def __init__(self, region, confidence, contrast, parent=None):
        super().__init__(parent)
        self.pause_until = 0.0; self.buffer = b""; self.process = QProcess(self)
        self.process.setProgram(str(OCR_WORKER))
        self.process.setArguments([
            "--region", ",".join(str(int(region[key])) for key in ("left", "top", "width", "height")),
            "--confidence", str(int(confidence)), "--contrast", "1" if contrast else "0",
        ])
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(self.read_error)
        self.process.finished.connect(lambda *_: self.stopped.emit())

    def start(self): self.process.start()
    def stop(self):
        if self.process.state() != QProcess.NotRunning: self.process.terminate()
    def wait(self, milliseconds=5000): return self.process.waitForFinished(milliseconds)
    def pause(self, seconds=30): self.pause_until = max(self.pause_until, time.monotonic() + seconds)
    def read_error(self):
        value = bytes(self.process.readAllStandardError()).decode("utf-8", "replace").strip()
        if not value:
            return
        # Paddle prints normal model-initialization messages to stderr. They are
        # diagnostic noise, not scan failures, so keep them out of the UI log.
        clean_lines = []
        for line in value.splitlines():
            plain = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line).strip()
            if not plain or "Creating model:" in plain or "DeprecationWarning:" in plain:
                continue
            clean_lines.append(plain)
        if clean_lines:
            self.error.emit("\n".join(clean_lines))
    def read_output(self):
        self.buffer += bytes(self.process.readAllStandardOutput())
        while b"\n" in self.buffer:
            raw, self.buffer = self.buffer.split(b"\n", 1)
            try: message = json.loads(raw.decode("utf-8"))
            except Exception: continue
            kind = message.get("type")
            if kind == "ready": self.ready.emit()
            elif kind == "error": self.error.emit(str(message.get("text") or "Ошибка сканера чата"))
            elif kind == "scan" and time.monotonic() >= self.pause_until:
                self.scan.emit(message.get("lines") or [], float(message.get("elapsed") or 0))
