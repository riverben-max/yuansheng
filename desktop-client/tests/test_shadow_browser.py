from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import shadow_browser
from shadow_browser import (
    build_shadow_launch_command,
    default_shadow_profile_dir,
    _cmdline_matches_shadow_process,
    _read_devtools_active_port,
    _resolve_attach_port,
)


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
        self.assertIn("--window-position=120,120", command)
        self.assertIn("--disk-cache-size=10485760", command)
        self.assertNotIn("--new-window", command)

    def test_build_shadow_launch_command_allows_auto_debug_port(self) -> None:
        command = build_shadow_launch_command(
            chrome_path=r"C:\Chrome\chrome.exe",
            port=0,
            profile_dir=Path(r"D:\shadow-profile"),
            visible=True,
        )

        self.assertIn("--remote-debugging-port=0", command)

    def test_read_devtools_active_port_parses_runtime_port_and_browser_path(self) -> None:
        with self.subTest("valid file"):
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                profile_dir = Path(temp_dir)
                (profile_dir / "DevToolsActivePort").write_text(
                    "45678\n/devtools/browser/abc\n",
                    encoding="utf-8",
                    newline="\n",
                )

                endpoint = _read_devtools_active_port(profile_dir)

            self.assertIsNotNone(endpoint)
            self.assertEqual(endpoint.port, 45678)
            self.assertEqual(endpoint.browser_path, "/devtools/browser/abc")

        with self.subTest("missing file"):
            self.assertIsNone(_read_devtools_active_port(Path(r"D:\does-not-exist")))

    def test_resolve_attach_port_prefers_active_then_devtools_then_legacy_port(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            profile_dir = Path(temp_dir)
            (profile_dir / "DevToolsActivePort").write_text(
                "45678\n/devtools/browser/auto\n",
                encoding="utf-8",
                newline="\n",
            )

            self.assertEqual(
                _resolve_attach_port({"chromePort": 9222, "activeChromePort": 46789}, profile_dir),
                46789,
            )
            self.assertEqual(_resolve_attach_port({"chromePort": 9222}, profile_dir), 45678)

        self.assertEqual(_resolve_attach_port({"chromePort": 9222}, Path(r"D:\missing-profile")), 9222)
        self.assertEqual(_resolve_attach_port({"chromePort": 0}, Path(r"D:\missing-profile")), 0)

    def test_build_visible_shadow_launch_command_resets_window_position(self) -> None:
        command = build_shadow_launch_command(
            chrome_path=r"C:\Chrome\chrome.exe",
            port=9333,
            profile_dir=Path(r"D:\shadow-profile"),
            visible=True,
        )
        self.assertIn("--window-position=120,120", command)
        self.assertIn("--window-size=1280,900", command)

    def test_cmdline_match_primarily_uses_profile_dir(self) -> None:
        cmdline = [
            r"C:\Chrome\chrome.exe",
            "--remote-debugging-port=45678",
            "--user-data-dir=D:\\shadow-profile",
        ]
        self.assertTrue(_cmdline_matches_shadow_process(cmdline, Path(r"D:\shadow-profile"), 0, "chrome.exe"))
        self.assertTrue(_cmdline_matches_shadow_process(cmdline, Path(r"D:\shadow-profile"), 9222, "chrome.exe"))
        self.assertFalse(_cmdline_matches_shadow_process(cmdline, Path(r"D:\other-profile"), 0, "chrome.exe"))

    def test_cmdline_match_identifies_drission_temp_browser_for_port(self) -> None:
        cmdline = [
            r"C:\Chrome\chrome.exe",
            "--remote-debugging-port=9222",
            r"--user-data-dir=C:\Users\Test\AppData\Local\Temp\DrissionPage\userData\9222",
        ]

        self.assertTrue(shadow_browser._cmdline_matches_drission_temp_process(cmdline, 9222, "chrome.exe"))
        self.assertFalse(shadow_browser._cmdline_matches_drission_temp_process(cmdline, 9223, "chrome.exe"))

    def test_kill_drission_temp_processes_only_matches_target_port(self) -> None:
        killed = []

        class FakeProcess:
            def __init__(self, pid, cmdline):
                self.pid = pid
                self.info = {"pid": pid, "name": "chrome.exe", "cmdline": cmdline}

            def terminate(self):
                killed.append(("terminate", self.pid))

        matching = FakeProcess(
            1001,
            [
                r"C:\Chrome\chrome.exe",
                "--remote-debugging-port=9222",
                r"--user-data-dir=C:\Users\Test\AppData\Local\Temp\DrissionPage\userData\9222",
            ],
        )
        other = FakeProcess(
            1002,
            [
                r"C:\Chrome\chrome.exe",
                "--remote-debugging-port=9223",
                r"--user-data-dir=C:\Users\Test\AppData\Local\Temp\DrissionPage\userData\9223",
            ],
        )

        with (
            patch("shadow_browser.psutil.process_iter", return_value=[matching, other]),
            patch("shadow_browser.psutil.wait_procs", return_value=([], [])),
        ):
            count = shadow_browser.kill_drission_temp_browsers(9222, lambda _message: None)

        self.assertEqual(count, 1)
        self.assertEqual(killed, [("terminate", 1001)])

    def test_try_attach_session_uses_existing_profile_without_auto_launch(self) -> None:
        calls = {}

        class FakeOptions:
            def set_paths(self, **kwargs):
                calls["paths"] = kwargs
                return self

            def existing_only(self, on_off=True):
                calls["existing_only"] = on_off
                return self

        class FakePage:
            title = "千牛登录"

            def __init__(self, options):
                calls["page_options"] = options

        with (
            patch("shadow_browser._find_shadow_pid", return_value=1234),
            patch.dict(
                "sys.modules",
                {
                    "DrissionPage": SimpleNamespace(
                        ChromiumOptions=FakeOptions,
                        ChromiumPage=FakePage,
                    )
                },
            ),
        ):
            session = shadow_browser._try_attach_session(
                chrome_path=r"C:\Chrome\chrome.exe",
                profile_dir=Path(r"D:\shadow-profile"),
                port=9222,
                launched=False,
                restarted=False,
            )

        self.assertEqual(calls["paths"]["browser_path"], r"C:\Chrome\chrome.exe")
        self.assertEqual(calls["paths"]["local_port"], 9222)
        self.assertEqual(calls["paths"]["user_data_path"], r"D:\shadow-profile")
        self.assertTrue(calls["existing_only"])
        self.assertEqual(session.pid, 1234)

    def test_launch_shadow_browser_for_login_starts_process_without_attaching_page(self) -> None:
        logs = []
        launch_calls = []

        def fake_launch(chrome_path, profile_dir, port, visible, startup_url):
            launch_calls.append((chrome_path, profile_dir, port, visible, startup_url))
            return SimpleNamespace(pid=4567)

        with (
            patch("shadow_browser.resolve_chrome_path", return_value=r"C:\Chrome\chrome.exe"),
            patch("shadow_browser._port_is_open", return_value=False),
            patch("shadow_browser._launch_shadow_browser", side_effect=fake_launch),
            patch("shadow_browser._wait_for_attach", side_effect=AssertionError("should not attach")),
        ):
            session = shadow_browser.launch_shadow_browser_for_login(
                {
                    "shadowChromeProfileDir": r"D:\shadow-profile",
                    "chromePort": 9333,
                },
                logs.append,
            )

        self.assertIsNone(session.page)
        self.assertEqual(session.pid, 4567)
        self.assertEqual(session.profile_dir, r"D:\shadow-profile")
        self.assertEqual(session.port, 9333)
        self.assertEqual(launch_calls[0][4], shadow_browser.LOGIN_START_URL)
        self.assertTrue(any("登录窗口启动诊断：准备启动" in item for item in logs))
        self.assertTrue(any("Chrome 进程已创建" in item for item in logs))
        self.assertTrue(any("登录窗口已打开" in item for item in logs))

    def test_launch_shadow_browser_for_login_uses_configured_startup_url(self) -> None:
        launch_calls = []

        def fake_launch(chrome_path, profile_dir, port, visible, startup_url):
            launch_calls.append((chrome_path, profile_dir, port, visible, startup_url))
            return SimpleNamespace(pid=4567)

        with (
            patch("shadow_browser.resolve_chrome_path", return_value=r"C:\Chrome\chrome.exe"),
            patch("shadow_browser._port_is_open", return_value=False),
            patch("shadow_browser._launch_shadow_browser", side_effect=fake_launch),
            patch("shadow_browser._wait_for_attach", side_effect=AssertionError("should not attach")),
        ):
            shadow_browser.launch_shadow_browser_for_login(
                {
                    "shadowChromeProfileDir": r"D:\shadow-profile",
                    "chromePort": 9333,
                    "shadowChromeStartupUrl": "https://passport.jd.com/new/login.aspx",
                },
                lambda _message: None,
            )

        self.assertEqual(launch_calls[0][4], "https://passport.jd.com/new/login.aspx")

    def test_launch_shadow_browser_for_login_resolves_auto_port_from_devtools_file(self) -> None:
        logs = []
        launch_calls = []

        def fake_launch(chrome_path, profile_dir, port, visible, startup_url):
            launch_calls.append((chrome_path, profile_dir, port, visible, startup_url))
            (profile_dir / "DevToolsActivePort").write_text(
                "45678\n/devtools/browser/auto\n",
                encoding="utf-8",
                newline="\n",
            )
            return SimpleNamespace(pid=4567)

        with (
            patch("shadow_browser.resolve_chrome_path", return_value=r"C:\Chrome\chrome.exe"),
            patch("shadow_browser._launch_shadow_browser", side_effect=fake_launch),
            patch("shadow_browser._wait_for_attach", side_effect=AssertionError("should not attach")),
        ):
            session = shadow_browser.launch_shadow_browser_for_login(
                {
                    "shadowChromeProfileDir": r"D:\shadow-profile",
                    "chromePort": 0,
                },
                logs.append,
            )

        self.assertEqual(launch_calls[0][2], 0)
        self.assertEqual(session.port, 45678)
        self.assertTrue(any("DevTools 调试端口已就绪" in item for item in logs))
        self.assertTrue(any("端口=45678" in item for item in logs))

    def test_launch_shadow_browser_for_login_closes_profile_when_devtools_file_is_missing(self) -> None:
        shutdown_calls = []

        with (
            patch("shadow_browser.resolve_chrome_path", return_value=r"C:\Chrome\chrome.exe"),
            patch("shadow_browser._launch_shadow_browser", return_value=SimpleNamespace(pid=4567)),
            patch("shadow_browser._wait_for_devtools_active_port", return_value=None),
            patch("shadow_browser._kill_shadow_processes", side_effect=lambda profile, port, log: shutdown_calls.append((profile, port)) or 1),
        ):
            with self.assertRaises(shadow_browser.ShadowBrowserError) as context:
                shadow_browser.launch_shadow_browser_for_login(
                    {
                        "shadowChromeProfileDir": r"D:\shadow-profile",
                        "chromePort": 0,
                    },
                    lambda _message: None,
                )

        self.assertIn("登录窗口启动异常", str(context.exception))
        self.assertEqual(shutdown_calls, [(Path(r"D:\shadow-profile"), 0)])


if __name__ == "__main__":
    unittest.main()
