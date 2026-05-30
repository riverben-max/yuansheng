from __future__ import annotations

import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from browser_debug_setup import (
    BROWSER_DEBUG_PORT,
    BROWSER_EXE_NAMES,
    PLATFORM_COOKIE_DOMAINS,
    BrowserDebugError,
    BrowserNotReadyError,
    ShortcutModifyError,
    _has_debug_port_arg,
    _port_is_open,
    _shortcut_search_dirs,
    add_debug_port_to_shortcut,
    create_debug_shortcut,
    detect_browser_debug_status,
    find_browser_shortcuts,
    grab_cookies_via_cdp,
)


class TestPortIsOpen(unittest.TestCase):
    def test_returns_false_for_closed_port(self) -> None:
        self.assertFalse(_port_is_open(59999, timeout=0.1))

    def test_returns_true_for_open_port(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        try:
            self.assertTrue(_port_is_open(port, timeout=1.0))
        finally:
            server.close()


class TestHasDebugPortArg(unittest.TestCase):
    def test_detects_present_arg(self) -> None:
        self.assertTrue(_has_debug_port_arg("--remote-debugging-port=9527", 9527))

    def test_detects_absent_arg(self) -> None:
        self.assertFalse(_has_debug_port_arg("--some-other-flag", 9527))

    def test_detects_different_port(self) -> None:
        self.assertFalse(_has_debug_port_arg("--remote-debugging-port=9222", 9527))

    def test_detects_arg_among_others(self) -> None:
        args = "--no-first-run --remote-debugging-port=9527 --disable-gpu"
        self.assertTrue(_has_debug_port_arg(args, 9527))


class TestShortcutSearchDirs(unittest.TestCase):
    def test_returns_list_of_paths(self) -> None:
        dirs = _shortcut_search_dirs()
        self.assertIsInstance(dirs, list)
        for d in dirs:
            self.assertIsInstance(d, Path)


class TestFindBrowserShortcuts(unittest.TestCase):
    @patch("browser_debug_setup._read_shortcut")
    @patch("browser_debug_setup._shortcut_search_dirs")
    def test_finds_matching_shortcuts(self, mock_dirs, mock_read) -> None:
        tmp = Path(tempfile.mkdtemp())
        lnk_file = tmp / "360极速浏览器X.lnk"
        lnk_file.write_text("")
        mock_dirs.return_value = [tmp]
        mock_read.return_value = {
            "path": str(lnk_file),
            "target": r"D:\workapp\360\360ChromeX\Chrome\Application\360ChromeX.exe",
            "arguments": "",
            "working_dir": "",
        }
        results = find_browser_shortcuts()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["target"], r"D:\workapp\360\360ChromeX\Chrome\Application\360ChromeX.exe")
        self.assertFalse(results[0]["has_debug_port"])

    @patch("browser_debug_setup._read_shortcut")
    @patch("browser_debug_setup._shortcut_search_dirs")
    def test_filters_by_exe_path(self, mock_dirs, mock_read) -> None:
        tmp = Path(tempfile.mkdtemp())
        lnk_file = tmp / "browser.lnk"
        lnk_file.write_text("")
        mock_dirs.return_value = [tmp]
        mock_read.return_value = {
            "path": str(lnk_file),
            "target": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "arguments": "",
            "working_dir": "",
        }
        results = find_browser_shortcuts(browser_exe_path=r"D:\other\360ChromeX.exe")
        self.assertEqual(len(results), 0)

    @patch("browser_debug_setup._read_shortcut")
    @patch("browser_debug_setup._shortcut_search_dirs")
    def test_detects_existing_debug_port(self, mock_dirs, mock_read) -> None:
        tmp = Path(tempfile.mkdtemp())
        lnk_file = tmp / "chrome.lnk"
        lnk_file.write_text("")
        mock_dirs.return_value = [tmp]
        mock_read.return_value = {
            "path": str(lnk_file),
            "target": r"C:\chrome.exe",
            "arguments": "--remote-debugging-port=9527",
            "working_dir": "",
        }
        results = find_browser_shortcuts()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["has_debug_port"])


class TestAddDebugPortToShortcut(unittest.TestCase):
    @patch("browser_debug_setup._write_shortcut_arguments")
    @patch("browser_debug_setup._read_shortcut")
    def test_adds_port_when_missing(self, mock_read, mock_write) -> None:
        mock_read.return_value = {
            "path": r"C:\test.lnk",
            "target": r"C:\chrome.exe",
            "arguments": "--no-first-run",
            "working_dir": "",
        }
        result = add_debug_port_to_shortcut(r"C:\test.lnk", 9527)
        self.assertTrue(result["modified"])
        self.assertIn("--remote-debugging-port=9527", result["arguments"])
        mock_write.assert_called_once()

    @patch("browser_debug_setup._write_shortcut_arguments")
    @patch("browser_debug_setup._read_shortcut")
    def test_skips_when_already_present(self, mock_read, mock_write) -> None:
        mock_read.return_value = {
            "path": r"C:\test.lnk",
            "target": r"C:\chrome.exe",
            "arguments": "--no-first-run --remote-debugging-port=9527",
            "working_dir": "",
        }
        result = add_debug_port_to_shortcut(r"C:\test.lnk", 9527)
        self.assertFalse(result["modified"])
        mock_write.assert_not_called()

    @patch("browser_debug_setup._write_shortcut_arguments")
    @patch("browser_debug_setup._read_shortcut")
    def test_replaces_different_port(self, mock_read, mock_write) -> None:
        mock_read.return_value = {
            "path": r"C:\test.lnk",
            "target": r"C:\chrome.exe",
            "arguments": "--remote-debugging-port=9222",
            "working_dir": "",
        }
        result = add_debug_port_to_shortcut(r"C:\test.lnk", 9527)
        self.assertTrue(result["modified"])
        self.assertIn("--remote-debugging-port=9527", result["arguments"])
        self.assertNotIn("9222", result["arguments"])


class TestDetectBrowserDebugStatus(unittest.TestCase):
    @patch("browser_debug_setup._find_browser_processes")
    def test_not_running(self, mock_procs) -> None:
        mock_procs.return_value = []
        result = detect_browser_debug_status(9527)
        self.assertEqual(result["status"], "not_running")

    @patch("browser_debug_setup._port_is_open")
    @patch("browser_debug_setup._process_has_debug_port")
    @patch("browser_debug_setup._find_browser_processes")
    def test_running_with_debug(self, mock_procs, mock_has_port, mock_port_open) -> None:
        proc = MagicMock()
        mock_procs.return_value = [proc]
        mock_has_port.return_value = True
        mock_port_open.return_value = True
        result = detect_browser_debug_status(9527)
        self.assertEqual(result["status"], "running_with_debug")

    @patch("browser_debug_setup._port_is_open")
    @patch("browser_debug_setup._process_has_debug_port")
    @patch("browser_debug_setup._find_browser_processes")
    def test_running_no_debug(self, mock_procs, mock_has_port, mock_port_open) -> None:
        proc = MagicMock()
        mock_procs.return_value = [proc]
        mock_has_port.return_value = False
        mock_port_open.return_value = False
        result = detect_browser_debug_status(9527)
        self.assertEqual(result["status"], "running_no_debug")

    @patch("browser_debug_setup._port_is_open")
    @patch("browser_debug_setup._process_has_debug_port")
    @patch("browser_debug_setup._find_browser_processes")
    def test_port_occupied_other(self, mock_procs, mock_has_port, mock_port_open) -> None:
        proc = MagicMock()
        mock_procs.return_value = [proc]
        mock_has_port.return_value = False
        mock_port_open.return_value = True
        result = detect_browser_debug_status(9527)
        self.assertEqual(result["status"], "port_occupied_other")


class TestGrabCookiesViaCdp(unittest.TestCase):
    @patch("browser_debug_setup._port_is_open")
    def test_raises_when_port_closed(self, mock_port) -> None:
        mock_port.return_value = False
        with self.assertRaises(BrowserNotReadyError):
            grab_cookies_via_cdp(9527, ["jinritemai.com"])

    @patch("browser_debug_setup._port_is_open")
    def test_filters_cookies_by_domain(self, mock_port) -> None:
        mock_port.return_value = True
        mock_page = MagicMock()
        mock_page.title = "Test"
        mock_page.cookies.return_value = [
            {"name": "session_id", "value": "abc123", "domain": ".jinritemai.com"},
            {"name": "token", "value": "xyz", "domain": ".jinritemai.com"},
            {"name": "unrelated", "value": "skip", "domain": ".google.com"},
            {"name": "sub", "value": "val", "domain": "pigeon.jinritemai.com"},
        ]

        mock_chromium_page_cls = MagicMock(return_value=mock_page)
        mock_chromium_opts_cls = MagicMock()
        mock_drission = MagicMock()
        mock_drission.ChromiumPage = mock_chromium_page_cls
        mock_drission.ChromiumOptions = mock_chromium_opts_cls
        with patch.dict("sys.modules", {"DrissionPage": mock_drission}):
            from browser_debug_setup import grab_cookies_via_cdp as _grab
            result = _grab(9527, ["jinritemai.com"])

        self.assertIn("session_id=abc123", result)
        self.assertIn("token=xyz", result)
        self.assertIn("sub=val", result)
        self.assertNotIn("unrelated", result)
        self.assertNotIn("google", result)

    @patch("browser_debug_setup._port_is_open")
    def test_returns_empty_when_no_matching_cookies(self, mock_port) -> None:
        mock_port.return_value = True
        mock_page = MagicMock()
        mock_page.title = "Test"
        mock_page.cookies.return_value = [
            {"name": "ga", "value": "123", "domain": ".google.com"},
        ]

        mock_chromium_page_cls = MagicMock(return_value=mock_page)
        mock_chromium_opts_cls = MagicMock()
        mock_drission = MagicMock()
        mock_drission.ChromiumPage = mock_chromium_page_cls
        mock_drission.ChromiumOptions = mock_chromium_opts_cls
        with patch.dict("sys.modules", {"DrissionPage": mock_drission}):
            from browser_debug_setup import grab_cookies_via_cdp as _grab
            result = _grab(9527, ["jinritemai.com"])

        self.assertEqual(result, "")


class TestPlatformCookieDomains(unittest.TestCase):
    def test_all_platforms_have_domains(self) -> None:
        for platform in ("douyin", "qn", "jd", "pdd"):
            self.assertIn(platform, PLATFORM_COOKIE_DOMAINS)
            self.assertGreater(len(PLATFORM_COOKIE_DOMAINS[platform]), 0)


if __name__ == "__main__":
    unittest.main()



class TestCreateDebugShortcut(unittest.TestCase):
    def test_creates_shortcut_on_desktop(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_exe = os.path.join(tmpdir, "360ChromeX.exe")
            open(fake_exe, "w").close()
            created_links = {}

            def fake_create(lnk_path, target, arguments, working_dir=""):
                created_links["lnk"] = lnk_path
                created_links["target"] = target
                created_links["arguments"] = arguments

            with patch("browser_debug_setup._create_shortcut", side_effect=fake_create), \
                 patch.dict(os.environ, {"USERPROFILE": tmpdir}):
                os.makedirs(os.path.join(tmpdir, "Desktop"), exist_ok=True)
                result = create_debug_shortcut(fake_exe, port=9527)

            self.assertTrue(result["created"])
            self.assertIn("--remote-debugging-port=9527", created_links["arguments"])
            self.assertEqual(created_links["target"], fake_exe)

    def test_raises_when_exe_not_found(self) -> None:
        with patch("browser_debug_setup._resolve_browser_exe", return_value=""):
            with self.assertRaises(ShortcutModifyError):
                create_debug_shortcut(browser_exe_path="nonexistent.exe")

    def test_raises_when_desktop_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_exe = os.path.join(tmpdir, "360ChromeX.exe")
            open(fake_exe, "w").close()
            with patch.dict(os.environ, {"USERPROFILE": tmpdir}):
                # Desktop subdir not created
                with self.assertRaises(ShortcutModifyError):
                    create_debug_shortcut(fake_exe)



# ─── 真实集成测试（不 mock win32com，验证 pywin32 真实可用）───
# 这些测试在 Windows 上运行真实 .lnk 读写，捕获 pywin32 缺失等环境问题。

@unittest.skipUnless(os.name == "nt", "Windows-only integration tests")
class TestRealShortcutIntegration(unittest.TestCase):
    def setUp(self) -> None:
        try:
            import win32com.client  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("pywin32 not installed - 这本来就是要捕获的环境问题，请安装 pywin32 后重跑")
        self.tmpdir = tempfile.mkdtemp()
        self.fake_exe = os.path.join(self.tmpdir, "fake_browser.exe")
        open(self.fake_exe, "w").close()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_read_modify_real_shortcut(self) -> None:
        """端到端：真实创建 .lnk → 读取 → 添加调试端口 → 验证写入正确"""
        from browser_debug_setup import _create_shortcut, _read_shortcut, add_debug_port_to_shortcut
        lnk_path = os.path.join(self.tmpdir, "test.lnk")

        # 创建（无参数）
        _create_shortcut(lnk_path, self.fake_exe, "", self.tmpdir)
        self.assertTrue(os.path.exists(lnk_path))

        # 读取
        info = _read_shortcut(lnk_path)
        self.assertEqual(info["target"].lower(), self.fake_exe.lower())
        self.assertEqual(info["arguments"], "")

        # 修改：添加调试端口
        result = add_debug_port_to_shortcut(lnk_path, port=9527)
        self.assertTrue(result["modified"])
        self.assertIn("--remote-debugging-port=9527", result["arguments"])

        # 再次读取确认持久化
        info2 = _read_shortcut(lnk_path)
        self.assertIn("--remote-debugging-port=9527", info2["arguments"])

        # 幂等：再次添加不会重复
        result2 = add_debug_port_to_shortcut(lnk_path, port=9527)
        self.assertFalse(result2["modified"])

    def test_replaces_different_port_real(self) -> None:
        """真实快捷方式上替换端口"""
        from browser_debug_setup import _create_shortcut, _read_shortcut, add_debug_port_to_shortcut
        lnk_path = os.path.join(self.tmpdir, "test_replace.lnk")
        _create_shortcut(lnk_path, self.fake_exe, "--remote-debugging-port=9222 --no-first-run", self.tmpdir)

        result = add_debug_port_to_shortcut(lnk_path, port=9527)
        self.assertTrue(result["modified"])
        info = _read_shortcut(lnk_path)
        self.assertIn("--remote-debugging-port=9527", info["arguments"])
        self.assertNotIn("--remote-debugging-port=9222", info["arguments"])
        self.assertIn("--no-first-run", info["arguments"])
