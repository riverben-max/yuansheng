from __future__ import annotations

import os
from pathlib import Path
from unittest import mock
import unittest

from startup_manager import build_startup_command


class StartupManagerTests(unittest.TestCase):
    def test_build_startup_command_for_script_mode_prefers_pythonw(self) -> None:
        command = build_startup_command(
            base_dir=Path(r"D:\Tools\work_project\desktop-client"),
            executable=r"C:\Python312\python.exe",
            script_path=r"D:\Tools\work_project\desktop-client\main.py",
            frozen=False,
        )
        self.assertEqual(command, '"C:\\Python312\\python.exe" "D:\\Tools\\work_project\\desktop-client\\main.py"')

    def test_build_startup_command_for_frozen_mode_uses_single_executable(self) -> None:
        command = build_startup_command(
            executable=r"D:\Apps\远盛数据助手.exe",
            frozen=True,
        )
        self.assertEqual(command, '"D:\\Apps\\远盛数据助手.exe"')

    def test_build_startup_command_frozen_prefers_yuansheng_main_exe_env(self) -> None:
        """sidecar 进程的 sys.executable 是 sidecar.exe，靠 YUANSHENG_MAIN_EXE 拿到 Tauri 主程序路径。"""
        with mock.patch.dict(os.environ, {"YUANSHENG_MAIN_EXE": r"C:\Program Files\远盛数据助手\yuansheng-data-assistant.exe"}, clear=False):
            command = build_startup_command(frozen=True)
        self.assertEqual(command, r'"C:\Program Files\远盛数据助手\yuansheng-data-assistant.exe"')

    def test_build_startup_command_frozen_explicit_executable_overrides_env(self) -> None:
        """显式传入的 executable 优先级最高，覆盖环境变量。"""
        with mock.patch.dict(os.environ, {"YUANSHENG_MAIN_EXE": r"C:\wrong\path.exe"}, clear=False):
            command = build_startup_command(
                executable=r"D:\correct\path.exe",
                frozen=True,
            )
        self.assertEqual(command, r'"D:\correct\path.exe"')


if __name__ == "__main__":
    unittest.main()
