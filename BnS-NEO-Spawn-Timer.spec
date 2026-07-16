# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = [('icon.ico', '.')], [], []
for package in ('paddle', 'paddleocr', 'paddlex', 'shapely', 'pyclipper'):
    d, b, h = collect_all(package); datas += d; binaries += b; hiddenimports += h
for distribution in ('paddlex', 'imagesize', 'opencv-contrib-python', 'pyclipper', 'pypdfium2', 'python-bidi', 'shapely'):
    datas += copy_metadata(distribution)
datas += [('models', 'models')]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BnS-NEO-Spawn-Timer-Beta',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True,
    name='BnS-NEO-Spawn-Timer-Beta',
)
