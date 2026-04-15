# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['../sid_play_X.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../stil_reader.py', '.'),
        ('../sidplayer_banner.png', '.'),
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
    icon=['../commodore.icns'],
)
app = BUNDLE(
    exe,
    name='SIDPlayer.app',
    icon='../commodore.icns',
    bundle_identifier='com.ezrad.sidplayer',
)
