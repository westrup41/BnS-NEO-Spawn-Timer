import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QVBoxLayout,
)
from dialogs.message_dialog import MessageDialog

from paths import APP_DIR
from styles import Style
from utils import s


OCR_DIR = APP_DIR / "ocr"
OCR_WORKER = OCR_DIR / "BnS-NEO-OCR-Worker.exe"
RELEASES_API = "https://api.github.com/repos/westrup41/BnS-NEO-Spawn-Timer/releases?per_page=10"
ASSET_NAMES = ("BnS-NEO-Spawn-Timer-OCR.zip", "BnS-NEO-OCR.zip")
DOWNLOAD_SIZE_TEXT = "примерно 0,3 ГБ"


class ComponentDownloadDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        scale = parent.settings.app_scale if parent else 1.0
        self._cancelled = False
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowModality(Qt.WindowModal)
        self.setStyleSheet(Style.main(scale))
        self.setFixedWidth(s(440, scale))

        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        shell = QFrame(); shell.setObjectName("Shell"); root.addWidget(shell)
        layout = QVBoxLayout(shell); layout.setContentsMargins(s(22, scale), s(18, scale), s(22, scale), s(18, scale)); layout.setSpacing(s(14, scale))
        title = QLabel("Загрузка компонентов"); title.setObjectName("SectionTitle"); title.setAlignment(Qt.AlignCenter); layout.addWidget(title)
        self.amount = QLabel("Подготовка загрузки…"); self.amount.setAlignment(Qt.AlignCenter); layout.addWidget(self.amount)
        self.bar = QProgressBar(); self.bar.setRange(0, 100); self.bar.setValue(0); self.bar.setTextVisible(False); layout.addWidget(self.bar)
        buttons = QHBoxLayout(); buttons.addStretch(1)
        cancel = QPushButton("Отмена"); cancel.setObjectName("Ghost"); cancel.clicked.connect(self.cancel); buttons.addWidget(cancel); buttons.addStretch(1); layout.addLayout(buttons)

    def cancel(self):
        self._cancelled = True

    def reject(self):
        self._cancelled = True
        super().reject()

    def wasCanceled(self):
        return self._cancelled

    def set_transfer(self, loaded: int, total: int):
        loaded_mb = loaded / (1024 * 1024)
        if total > 0:
            total_mb = total / (1024 * 1024)
            self.amount.setText(f"{loaded_mb:.0f} из {total_mb:.0f} МБ")
            self.bar.setValue(min(90, int(loaded * 90 / total)))
        else:
            self.amount.setText(f"Загружено {loaded_mb:.0f} МБ")

    def set_phase(self, text: str, value: int):
        self.amount.setText(text)
        self.bar.setValue(value)


def installed():
    return OCR_WORKER.is_file()


def migrate_bundled_ocr():
    if installed() or not getattr(sys, "frozen", False):
        return installed()
    executable_dir = Path(sys.executable).resolve().parent
    candidates = (executable_dir / "BnS-NEO-OCR-Worker", executable_dir / "ocr")
    for source in candidates:
        if source.resolve() == OCR_DIR.resolve():
            continue
        if not (source / OCR_WORKER.name).is_file():
            continue
        try:
            OCR_DIR.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(OCR_DIR))
            return installed()
        except Exception:
            try:
                shutil.copytree(source, OCR_DIR, dirs_exist_ok=True)
                if installed():
                    shutil.rmtree(source, ignore_errors=True)
                    return True
            except Exception:
                pass
    return False


def install_with_prompt(parent):
    if installed(): return True
    prompt = MessageDialog(
        parent, "Компоненты сканера чата",
        f"Хотите загрузить компоненты объёмом {DOWNLOAD_SIZE_TEXT}?",
        ok_text="Скачать", cancel_text="Отмена", ok_first=True,
        center_buttons=True, minimum_width=440,
    )
    if not prompt.exec_result(): return False
    progress = ComponentDownloadDialog(parent); progress.show(); QApplication.processEvents()
    archive = Path(tempfile.gettempdir()) / "bns-neo-ocr.zip"
    staging = APP_DIR / "ocr.new"
    try:
        request = urllib.request.Request(RELEASES_API, headers={"User-Agent": "BnS-NEO-Spawn-Timer"})
        with urllib.request.urlopen(request, timeout=30) as response: releases = json.load(response)
        url = ""
        for release in releases if isinstance(releases, list) else []:
            assets = {str(item.get("name")): str(item.get("browser_download_url")) for item in release.get("assets", [])}
            url = next((assets[name] for name in ASSET_NAMES if name in assets), "")
            if url: break
        if not url: raise RuntimeError("Пакет компонентов не найден в релизах")
        req = urllib.request.Request(url, headers={"User-Agent": "BnS-NEO-Spawn-Timer"})
        with urllib.request.urlopen(req, timeout=60) as response, open(archive, "wb") as output:
            total = int(response.headers.get("Content-Length") or 0); loaded = 0
            while True:
                if progress.wasCanceled(): raise RuntimeError("Загрузка отменена")
                chunk = response.read(1024 * 1024)
                if not chunk: break
                output.write(chunk); loaded += len(chunk)
                progress.set_transfer(loaded, total)
                QApplication.processEvents()
        progress.set_phase("Распаковка компонентов…", 92); QApplication.processEvents()
        if staging.exists(): shutil.rmtree(staging)
        staging.mkdir(parents=True)
        with zipfile.ZipFile(archive) as bundle:
            root = staging.resolve()
            for member in bundle.infolist():
                target = (staging / member.filename).resolve()
                if root not in target.parents and target != root: raise RuntimeError("Повреждённый пакет сканера чата")
            bundle.extractall(staging)
        candidates = list(staging.rglob(OCR_WORKER.name))
        if not candidates: raise RuntimeError("Компонент сканера чата не найден в архиве")
        source_root = candidates[0].parent
        if OCR_DIR.exists(): shutil.rmtree(OCR_DIR)
        shutil.move(str(source_root), str(OCR_DIR))
        progress.set_phase("Компоненты установлены", 100); QApplication.processEvents()
        return installed()
    except Exception as exc:
        MessageDialog(parent, "Ошибка загрузки компонентов", str(exc)).exec(); return False
    finally:
        progress.close()
        archive.unlink(missing_ok=True)
        if staging.exists(): shutil.rmtree(staging, ignore_errors=True)
