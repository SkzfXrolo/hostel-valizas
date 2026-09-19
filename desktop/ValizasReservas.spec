# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / 'assets' / 'rooms'), 'assets/rooms'),
        (str(root / 'assets' / 'logo.webp'), 'assets'),
        (str(root / 'assets' / 'bg-hero.webp'), 'assets'),
        (str(root / 'assets' / 'bg-night.webp'), 'assets'),
        (str(root / 'assets' / 'bg-front.webp'), 'assets'),
        (str(root / 'whatsapp-bridge' / 'package.json'), 'whatsapp-bridge'),
        (str(root / 'whatsapp-bridge' / 'index.js'), 'whatsapp-bridge'),
        (str(root / 'whatsapp-bridge' / 'package-lock.json'), 'whatsapp-bridge'),
    ],
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ValizasReservas',
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
)
