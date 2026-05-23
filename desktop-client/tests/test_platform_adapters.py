from __future__ import annotations

import unittest

from platform_adapters import PlatformAdapterNotRegisteredError, default_capture_adapters, select_capture_adapter


def qn_capture(_state, _log):
    return {"platform": "qn"}


def jd_capture(_state, _log):
    return {"platform": "jd"}


def pdd_capture(_state, _log):
    return {"platform": "pdd"}


def douyin_capture(_state, _log):
    return {"platform": "douyin"}


class PlatformAdapterTests(unittest.TestCase):
    def test_default_capture_adapters_registers_qn_jd_pdd_and_douyin(self) -> None:
        adapters = default_capture_adapters(qn_capture, jd_capture, pdd_capture, douyin_capture)

        self.assertIs(select_capture_adapter("qn", adapters), qn_capture)
        self.assertIs(select_capture_adapter("jd", adapters), jd_capture)
        self.assertIs(select_capture_adapter("pdd", adapters), pdd_capture)
        self.assertIs(select_capture_adapter("douyin", adapters), douyin_capture)

    def test_unknown_platform_normalizes_to_qn(self) -> None:
        adapters = default_capture_adapters(qn_capture, jd_capture, pdd_capture)

        self.assertIs(select_capture_adapter("bad", adapters), qn_capture)

    def test_known_platform_without_adapter_fails_instead_of_falling_back_to_qn(self) -> None:
        adapters = {"qn": qn_capture}

        with self.assertRaises(PlatformAdapterNotRegisteredError):
            select_capture_adapter("jd", adapters)
        with self.assertRaises(PlatformAdapterNotRegisteredError):
            select_capture_adapter("pdd", adapters)


if __name__ == "__main__":
    unittest.main()
