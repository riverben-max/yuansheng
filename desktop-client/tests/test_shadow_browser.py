from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from shadow_browser import build_shadow_launch_command, default_shadow_profile_dir, _cmdline_matches_shadow_process


class ShadowBrowserTests(unittest.TestCase):
    def test_default_shadow_profile_dir_prefers_local_app_data(self) -> None:
        with patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\Test\AppData\Local"}, clear=False):
            profile_dir = default_shadow_profile_dir()
        self.assertEqual(profile_dir, Path(r"C:\Users\Test\AppData\Local\YuanshengDataAssistant\shadow-chrome"))

    def test_build_shadow_launch_command_contains_required_flags(self) -> None:
        command = build_shadow_launch_command(
            chrome_path=r"C:\Chrome\chrome.exe",
            port=9333,
            profile_dir=Path(r"D:\shadow-profile"),
            visible=False,
        )
        self.assertIn("--remote-debugging-port=9333", command)
        self.assertIn("--user-data-dir=D:\\shadow-profile", command)
        self.assertIn("--window-position=-2000,-2000", command)
        self.assertIn("--disk-cache-size=10485760", command)

    def test_cmdline_match_requires_port_and_profile_dir(self) -> None:
        cmdline = [
            r"C:\Chrome\chrome.exe",
            "--remote-debugging-port=9222",
            "--user-data-dir=D:\\shadow-profile",
        ]
        self.assertTrue(_cmdline_matches_shadow_process(cmdline, Path(r"D:\shadow-profile"), 9222, "chrome.exe"))
        self.assertFalse(_cmdline_matches_shadow_process(cmdline, Path(r"D:\other-profile"), 9222, "chrome.exe"))
        self.assertFalse(_cmdline_matches_shadow_process(cmdline, Path(r"D:\shadow-profile"), 9333, "chrome.exe"))


if __name__ == "__main__":
    unittest.main()
