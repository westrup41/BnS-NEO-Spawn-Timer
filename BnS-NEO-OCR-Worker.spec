# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = [('models', 'models')], [], []
for package in ('paddle', 'paddleocr', 'paddlex', 'shapely', 'pyclipper'):
    d, b, h = collect_all(package); datas += d; binaries += b; hiddenimports += h
for distribution in ('paddlex', 'imagesize', 'opencv-contrib-python', 'pyclipper', 'pypdfium2', 'python-bidi', 'shapely'):
    datas += copy_metadata(distribution)
a = Analysis(['ocr_worker.py'], pathex=[], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['PySide6'], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='BnS-NEO-OCR-Worker', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=True, console=False, disable_windowed_traceback=False,
          icon=['icon.ico'])
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name='BnS-NEO-OCR-Worker')
