# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['../sidplayer.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../stil_reader.py', '.'),
        ('../nowplaying_mac.py', '.'),
        ('../gb64_reader.py', '.'),
        ('../ezrad_portrait.png', '.'),
    ],
    hiddenimports=['sounddevice', 'numpy'],
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
    a.binaries,
    a.datas,
    [],
    name='SIDPlayer',
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
    icon=['../assets/commodore.icns'],
)
import subprocess, os

APP_VERSION = '6.4'

app = BUNDLE(
    exe,
    name='SIDPlayer.app',
    icon='../assets/commodore.icns',
    bundle_identifier='com.ezrad.sidplayer',
    version=APP_VERSION,
    info_plist={
        'CFBundleShortVersionString': APP_VERSION,
        'CFBundleVersion': APP_VERSION,
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13',
    },
)

# PyInstaller ignora CFBundleShortVersionString nell'info_plist — lo scriviamo via PlistBuddy
_plist = os.path.join(DISTPATH, 'SIDPlayer.app', 'Contents', 'Info.plist')
if os.path.exists(_plist):
    for _cmd in [
        f"Set :CFBundleShortVersionString {APP_VERSION}",
        f"Set :CFBundleVersion {APP_VERSION}",
    ]:
        subprocess.run(['/usr/libexec/PlistBuddy', '-c', _cmd, _plist], check=False)
