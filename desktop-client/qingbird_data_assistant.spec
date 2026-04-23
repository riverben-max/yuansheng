# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project_dir = Path(SPEC).resolve().parent
datas = [
    (str(project_dir / "README.md"), "."),
    (str(project_dir / "resources" / "yuansheng_logo.png"), "resources"),
    (str(project_dir / "resources" / "yuansheng_logo.ico"), "resources"),
]
hiddenimports = (
    collect_submodules("PySide6.QtWebEngineCore")
    + collect_submodules("PySide6.QtWebEngineWidgets")
    + collect_submodules("DrissionPage")
)

a = Analysis(
    ["main.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="远盛数据助手",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(project_dir / "resources" / "yuansheng_logo.ico"),
    version=str(project_dir / "version_info.txt"),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="远盛数据助手",
)
