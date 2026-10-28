from __future__ import annotations

import unittest
from unittest.mock import patch

from desktop_app import CaptureWorker, YuanshengMainWindow, cookie_has_direct_api_markers, direct_api_cookie_state_label
from direct_api_capture import DirectApiCaptureError, DirectApiLoginRequiredError
from shadow_browser import ShadowBrowserError


class CaptureWorkerTests(unittest.TestCase):
    def test_capture_worker_uses_batch_when_login_accounts_are_configured(self) -> None:
        worker = CaptureWorker(
            {
                "directApiPreferred": True,
                "loginAccounts": [
                    {
                        "id": "account-1",
                        "displayName": "张三",
                        "enabled": True,
                        "profileDir": r"D:\profiles\zhangsan",
                        "chromePort": 9222,
                    }
                ],
            },
            "手动采集",
        )

        with patch("desktop_app.capture_enabled_accounts", return_value=[{"ok": True, "summary": "ok"}]) as batch_capture:
            results = worker._capture_batch_results()

        self.assertEqual(results, [{"ok": True, "summary": "ok"}])
        batch_capture.assert_called_once()

    def test_direct_api_failure_falls_back_to_external_capture(self) -> None:
        worker = CaptureWorker({"directApiPreferred": True}, "手动采集")

        with (
            patch("desktop_app.capture_with_direct_api", side_effect=DirectApiCaptureError("接口字段变化")),
            patch("desktop_app.capture_with_external_chrome", return_value={"subAccount": "林志玲"}) as external_capture,
        ):
            payload = worker._capture_payload()

        self.assertEqual(payload["subAccount"], "林志玲")
        external_capture.assert_called_once()

    def test_cookie_expired_falls_back_to_external_capture(self) -> None:
        worker = CaptureWorker({"directApiPreferred": True}, "手动采集")

        with (
            patch("desktop_app.capture_with_direct_api", side_effect=DirectApiLoginRequiredError("Cookie 已过期")),
            patch("desktop_app.capture_with_external_chrome", return_value={"subAccount": "林志玲"}) as external_capture,
        ):
            payload = worker._capture_payload()

        self.assertEqual(payload["subAccount"], "林志玲")
        external_capture.assert_called_once()

    def test_capture_refreshes_cookie_from_existing_shadow_before_direct_api(self) -> None:
        worker = CaptureWorker({"directApiPreferred": True, "directApiConfigPath": "direct_api_capture.json"}, "手动采集")
        cookie = "_m_h5_tk=abc_1777188499080; sn=x; unb=1; _tb_token_=token"

        with (
            patch("desktop_app.inspect_existing_shadow_browser_state", return_value={"cookieHeader": cookie}),
            patch("desktop_app.update_direct_api_cookie") as update_cookie,
            patch("desktop_app.capture_with_direct_api", return_value={"subAccount": "林志玲"}) as capture,
        ):
            payload = worker._capture_payload()

        self.assertEqual(payload["subAccount"], "林志玲")
        update_cookie.assert_called_once()
        capture.assert_called_once()

    def test_capture_uses_local_cookie_when_shadow_browser_is_not_open(self) -> None:
        worker = CaptureWorker({"directApiPreferred": True, "directApiConfigPath": "direct_api_capture.json"}, "手动采集")

        with (
            patch("desktop_app.inspect_existing_shadow_browser_state", side_effect=ShadowBrowserError("影子浏览器未启动")),
            patch("desktop_app.update_direct_api_cookie") as update_cookie,
            patch("desktop_app.capture_with_direct_api", return_value={"subAccount": "林志玲"}) as capture,
        ):
            payload = worker._capture_payload()

        self.assertEqual(payload["subAccount"], "林志玲")
        update_cookie.assert_not_called()
        capture.assert_called_once()

    def test_direct_api_cookie_status_text(self) -> None:
        self.assertEqual(direct_api_cookie_state_label("已刷新"), "接口 Cookie：已刷新")

    def test_cookie_marker_check_requires_mtop_and_user_marker(self) -> None:
        self.assertTrue(cookie_has_direct_api_markers("_m_h5_tk=abc_1777188499080; sn=x"))
        self.assertFalse(cookie_has_direct_api_markers("_m_h5_tk=abc_1777188499080"))


class FinishCaptureTests(unittest.TestCase):
    def _window(self) -> YuanshengMainWindow:
        class FakeLabel:
            def setText(self, _text: str) -> None:
                pass

        window = YuanshengMainWindow.__new__(YuanshengMainWindow)
        window.state = {}
        window.capture_reason = "每日自动采集"
        window.result_summary_label = FakeLabel()
        window._end_capture_ui = lambda: None
        window._log = lambda _message: None
        window._set_status = lambda *_args, **_kwargs: None
        window._set_alert_mode = lambda *_args, **_kwargs: None
        window._save_state = lambda: None
        window._refresh_schedule_hint = lambda: None
        window._remember_login_account = lambda _account: None
        return window

    def test_upload_failure_does_not_mark_daily_schedule_complete(self) -> None:
        window = self._window()
        payload = {"loginAccount": "远盛电商", "recordDate": "2026-04-25", "subAccount": "林志玲"}

        window._finish_capture(payload, aborted=False, signature="sig", upload_message="服务端上传失败：超时", upload_record=None)

        self.assertNotIn("lastRunDate", window.state)
        self.assertEqual(window.state["lastPayloadSignature"], "sig")

    def test_upload_success_marks_daily_schedule_complete(self) -> None:
        window = self._window()
        payload = {"loginAccount": "远盛电商", "recordDate": "2026-04-25", "subAccount": "林志玲"}

        window._finish_capture(
            payload,
            aborted=False,
            signature="sig",
            upload_message="服务端上传成功：上传成功。",
            upload_record={"uploadedAt": "2026-04-26 09:00:00"},
        )

        self.assertRegex(window.state.get("lastRunDate", ""), r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("sig", window.state["uploadHistory"])


if __name__ == "__main__":
    unittest.main()
