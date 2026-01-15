# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
mediapipe_data = collect_data_files('mediapipe')

hidden_imports = [
    'mediapipe', 'cv2', 'requests', 'engineio.async_drivers.threading', 'flask_socketio'
]

a = Analysis(
    ['plantgrower.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('JSON', 'JSON'), # <--- IMPORTING YOUR JSON FOLDER
        ('cert.pem', '.'),
        ('key.pem', '.')
    ] + mediapipe_data,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    name='plantgrower',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='plantgrower.app',
    icon=None,
    bundle_identifier=None,
)