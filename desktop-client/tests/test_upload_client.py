from __future__ import annotations

import os
import hashlib
import hmac
import uuid
import unittest
from unittest.mock import patch

from upload_client import (
    EMPLOYEE_UPLOAD_PATH,
    UploadClientError,
    build_employee_upload_payload,
    resolve_upload_auth,
    upload_employee_payload,
)
from pdd_workload_capture import parse_pdd_workload_payload


class UploadClientContractTests(unittest.TestCase):
    def test_upload_path_matches_backend_spider_upload_endpoint(self) -> None:
        self.assertEqual(EMPLOYEE_UPLOAD_PATH, "/spider/upload")

    def test_build_employee_upload_payload_maps_desktop_fields_to_backend_dto(self) -> None:
        payload = build_employee_upload_payload(
            {
                "shopId": 42,
                "platform": "pdd",
                "loginAccount": "拼多多远盛店",
                "recordDate": "2026-05-17",
                "subAccount": "屿你服饰星星",
                "consultationCount": 7,
                "receiveCount": 8,
                "validReceiveCount": 6,
                "conversionRate": 50,
                "firstReplyTime": 3,
                "avgReplyTime": 12,
                "salesAmount": 123.45,
                "wwReplyRate": 80,
                "satisfaction": 99.5,
                "rawMetrics": {"source": "pdd_cs_report_detail"},
            }
        )

        self.assertEqual(
            payload,
            {
                "platformType": 3,
                "loginAccount": "拼多多远盛店",
                "recordDate": "2026-05-17",
                "subAccount": "屿你服饰星星",
                "consultationCount": 7,
                "receptionCount": 8,
                "effectiveReceptionCount": 6,
                "conversionRate": 50,
                "firstResponseTime": 3,
                "avgResponseTime": 12,
                "salesAmount": 123.45,
                "responseRate3m": 80,
                "responseRate30s": None,
                "replyRate": 80,
                "satisfaction": 99.5,
                "shopSatisfaction": None,
                "rawMetrics": {"source": "pdd_cs_report_detail"},
            },
        )

    def test_build_employee_upload_payload_requires_login_account(self) -> None:
        with self.assertRaisesRegex(UploadClientError, "loginAccount"):
            build_employee_upload_payload({"platform": "qn"})

    def test_resolve_upload_auth_requires_configured_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("upload_client._load_auth_config", return_value={}):
                with self.assertRaisesRegex(UploadClientError, "未配置上传签名凭据"):
                    resolve_upload_auth()

    def test_resolve_upload_auth_reads_environment_credentials(self) -> None:
        with patch.dict(
            os.environ,
            {"YUANSHENG_RPA_APP_KEY": "env-key", "YUANSHENG_RPA_SECRET_KEY": "env-secret"},
            clear=True,
        ):
            self.assertEqual(resolve_upload_auth(), ("env-key", "env-secret"))

    def test_upload_signature_binds_timestamp_request_id_nonce_and_request_body_with_hmac(self) -> None:
        captured = {}

        class FakeResponse:
            status_code = 200
            text = '{"code":200}'

            def json(self):
                return {"code": 200, "msg": "ok", "data": {}}

        def fake_post(url, content, headers, timeout):
            captured.update({"url": url, "content": content, "headers": headers, "timeout": timeout})
            return FakeResponse()

        with (
            patch.dict(
                os.environ,
                {"YUANSHENG_RPA_APP_KEY": "env-key", "YUANSHENG_RPA_SECRET_KEY": "env-secret"},
                clear=True,
            ),
            patch("upload_client.time.time", return_value=1779000000),
            patch("upload_client.uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")),
            patch("upload_client.secrets.token_urlsafe", return_value="nonce-token"),
            patch("upload_client.httpx.post", side_effect=fake_post),
        ):
            upload_employee_payload(
                "http://example.test",
                {"platform": "pdd", "loginAccount": "shop", "recordDate": "2026-05-17"},
            )

        body = '{"loginAccount":"shop","platformType":3,"recordDate":"2026-05-17","subAccount":null,"consultationCount":null,"receptionCount":null,"effectiveReceptionCount":null,"conversionRate":null,"firstResponseTime":null,"avgResponseTime":null,"salesAmount":null,"responseRate3m":null,"responseRate30s":null,"replyRate":null,"satisfaction":null,"shopSatisfaction":null,"rawMetrics":null}'
        expected_body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        expected_sign = hmac.new(
            b"env-secret",
            f"env-key\n1779000000\n12345678-1234-5678-1234-567812345678\nnonce-token\n{EMPLOYEE_UPLOAD_PATH}\n{expected_body_hash}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(captured["content"], body.encode("utf-8"))
        self.assertEqual(captured["headers"]["X-Request-Id"], "12345678-1234-5678-1234-567812345678")
        self.assertEqual(captured["headers"]["X-Nonce"], "nonce-token")
        self.assertEqual(captured["headers"]["X-Body-SHA256"], expected_body_hash)
        self.assertEqual(captured["headers"]["X-Sign"], expected_sign)

    def test_pdd_payload_exposes_sales_amount_for_backend_upload(self) -> None:
        payload = parse_pdd_workload_payload(
            {
                "success": True,
                "result": {
                    "data": [
                        {
                            "cs_name": "屿你服饰星星",
                            "cs_sales_amount": 12345,
                        }
                    ]
                },
            },
            {"recordDate": "2026-05-17"},
            {"shopName": "拼多多远盛店"},
        )

        self.assertEqual(payload["salesAmount"], 123.45)


if __name__ == "__main__":
    unittest.main()
