from __future__ import annotations

from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
