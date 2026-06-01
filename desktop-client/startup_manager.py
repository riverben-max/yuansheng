from __future__ import annotations

import os
from pathlib import Path
import sys
import winreg

RUN_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "远盛数据助手"


def ensure_autostart(
    enabled: bool,
    app_name: str = APP_NAME,
    base_dir: Path | None = None,
    executable: str | None = None,
    script_path: str | None = None,
    frozen: bool | None = None,
) -> None:
    command = build_startup_command(
        base_dir=base_dir,
        executable=executable,
        script_path=script_path,
        frozen=frozen,
    )
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_SUBKEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as handle:
        if enabled:
            winreg.SetValueEx(handle, app_name, 0, winreg.REG_SZ, command)
            return
        try:
            winreg.DeleteValue(handle, app_name)
        except FileNotFoundError:
            return


def is_autostart_enabled(app_name: str = APP_NAME) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_SUBKEY, 0, winreg.KEY_READ) as handle:
            value, _ = winreg.QueryValueEx(handle, app_name)
            return bool(str(value).strip())
    except OSError:
        return False


def build_startup_command(
    base_dir: Path | None = None,
    executable: str | None = None,
    script_path: str | None = None,
    frozen: bool | None = None,
) -> str:
    # frozen 模式优先用 YUANSHENG_MAIN_EXE（由 Tauri 主程序在 spawn sidecar 时注入），
    # 这样开机自启写到注册表的命令是 Tauri 主程序而不是 sidecar.exe。
    # sidecar.exe 自启没 UI、前端定时器不跑、客户感知不到软件已启动。
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        main_exe = (executable or os.environ.get("YUANSHENG_MAIN_EXE") or sys.executable)
        return f'"{main_exe}"'

    runtime_executable = str(executable or sys.executable)
    root_dir = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parent
    entry_script = script_path or str(root_dir / "main.py")
    executable_path = Path(runtime_executable)
    pythonw = executable_path.with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else executable_path
    return f'"{runner}" "{entry_script}"'
