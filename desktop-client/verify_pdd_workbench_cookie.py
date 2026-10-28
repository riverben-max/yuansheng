# -*- coding: utf-8 -*-
"""拼多多商家工作台（PddWorkbench / 多多客服）本地 Cookie 只读校验脚本。

用途：在不修改任何业务代码、不启动/重启客户端的前提下，验证能否从拼多多桌面客户端
（CEF / Chromium 104 内核）的用户数据目录读取并解密出 mms.pinduoduo.com 的登录 Cookie，
以判断“拼多多走本地软件采集”方案是否可行。

安全约定（务必遵守）：
- 全程只读，不写入、不删除客户端任何文件（Cookie 库以只读/复制副本方式打开）。
- 绝不打印任何 Cookie 明文值或解密结果；只输出 Cookie 名称、所属域名、明文长度，
  以及“必需字段是否齐全”的判定。

依赖：仅用标准库 + Windows 自带 DPAPI / CNG(bcrypt)，无需额外 pip 安装。
      若环境恰好装了 cryptography，则优先使用它解 AES-GCM。

用法：
    python verify_pdd_workbench_cookie.py
    python verify_pdd_workbench_cookie.py "C:\\Users\\Public\\Documents\\PDD\\PddBrowser104\\User Data"
"""
from __future__ import annotations

import base64
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

# 统一把输出编码设为 UTF-8，规避 Windows 控制台/重定向的 GBK 编码问题
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 拼多多桌面客户端 CEF 用户数据默认目录（实地核实路径）
DEFAULT_USER_DATA_DIR = r"C:\Users\Public\Documents\PDD\PddBrowser104\User Data"

# mms.pinduoduo.com 客服绩效采集所需的 Cookie 必需字段
# 与 pdd_workload_capture.normalize_pdd_cookie_header 的校验保持一致
REQUIRED_EXACT = ("PASS_ID", "JSESSIONID")
REQUIRED_PREFIX = ("mms_", "windows_app_shop_token_")
PDD_HOST_MARKERS = ("pinduoduo.com", "yangkeduo.com")


# --------------------- DPAPI：解 Local State 里的 AES 主密钥 ---------------------
def _dpapi_unprotect(data: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    buf_in = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buf_in, ctypes.POINTER(ctypes.c_byte)))
    blob_out = DATA_BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    ):
        raise OSError(f"CryptUnprotectData 失败：Windows error {ctypes.get_last_error()}")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        if blob_out.pbData:
            kernel32.LocalFree(blob_out.pbData)


def load_aes_key(user_data_dir: Path) -> bytes:
    local_state = user_data_dir / "Local State"
    raw = json.loads(local_state.read_text(encoding="utf-8"))
    encrypted_key_b64 = raw["os_crypt"]["encrypted_key"]
    blob = base64.b64decode(encrypted_key_b64)
    if blob[:5] != b"DPAPI":
        raise ValueError("os_crypt.encrypted_key 非 DPAPI 前缀，可能是 app-bound 加密，无法本地解。")
    return _dpapi_unprotect(blob[5:])


# --------------------- AES-256-GCM：解 v10/v11 cookie 值 ---------------------
def _aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    # 优先用 cryptography（若已安装），否则回落到 Windows CNG(bcrypt)，零额外依赖。
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        return AESGCM(key).decrypt(nonce, ciphertext + tag, None)
    except ImportError:
        return _aes_gcm_decrypt_cng(key, nonce, ciphertext, tag)


def _aes_gcm_decrypt_cng(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    PUCHAR = ctypes.POINTER(ctypes.c_ubyte)
    NTSTATUS = ctypes.c_long

    class BCRYPT_AUTH_INFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.ULONG),
            ("dwInfoVersion", wintypes.ULONG),
            ("pbNonce", PUCHAR),
            ("cbNonce", wintypes.ULONG),
            ("pbAuthData", PUCHAR),
            ("cbAuthData", wintypes.ULONG),
            ("pbTag", PUCHAR),
            ("cbTag", wintypes.ULONG),
            ("pbMacContext", PUCHAR),
            ("cbMacContext", wintypes.ULONG),
            ("cbAAD", wintypes.ULONG),
            ("cbData", ctypes.c_ulonglong),
            ("dwFlags", wintypes.ULONG),
        ]

    bcrypt = ctypes.WinDLL("bcrypt", use_last_error=True)
    bcrypt.BCryptOpenAlgorithmProvider.argtypes = [
        ctypes.POINTER(ctypes.c_void_p), wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.ULONG,
    ]
    bcrypt.BCryptOpenAlgorithmProvider.restype = NTSTATUS
    bcrypt.BCryptSetProperty.argtypes = [
        ctypes.c_void_p, wintypes.LPCWSTR, PUCHAR, wintypes.ULONG, wintypes.ULONG,
    ]
    bcrypt.BCryptSetProperty.restype = NTSTATUS
    bcrypt.BCryptGetProperty.argtypes = [
        ctypes.c_void_p, wintypes.LPCWSTR, PUCHAR, wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG), wintypes.ULONG,
    ]
    bcrypt.BCryptGetProperty.restype = NTSTATUS
    bcrypt.BCryptGenerateSymmetricKey.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), PUCHAR, wintypes.ULONG,
        PUCHAR, wintypes.ULONG, wintypes.ULONG,
    ]
    bcrypt.BCryptGenerateSymmetricKey.restype = NTSTATUS
    bcrypt.BCryptDecrypt.argtypes = [
        ctypes.c_void_p, PUCHAR, wintypes.ULONG, ctypes.c_void_p, PUCHAR, wintypes.ULONG,
        PUCHAR, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG), wintypes.ULONG,
    ]
    bcrypt.BCryptDecrypt.restype = NTSTATUS
    bcrypt.BCryptDestroyKey.argtypes = [ctypes.c_void_p]
    bcrypt.BCryptCloseAlgorithmProvider.argtypes = [ctypes.c_void_p, wintypes.ULONG]

    def _check(status: int, name: str) -> None:
        if status != 0:
            raise OSError(f"{name} 失败：NTSTATUS 0x{status & 0xFFFFFFFF:08x}")

    h_alg = ctypes.c_void_p()
    _check(bcrypt.BCryptOpenAlgorithmProvider(ctypes.byref(h_alg), "AES", None, 0),
           "BCryptOpenAlgorithmProvider")
    try:
        mode = ctypes.create_unicode_buffer("ChainingModeGCM")
        _check(bcrypt.BCryptSetProperty(h_alg, "ChainingMode",
                                        ctypes.cast(mode, PUCHAR), ctypes.sizeof(mode), 0),
               "BCryptSetProperty")

        obj_len = wintypes.ULONG(0)
        got = wintypes.ULONG(0)
        _check(bcrypt.BCryptGetProperty(h_alg, "ObjectLength",
                                        ctypes.cast(ctypes.byref(obj_len), PUCHAR),
                                        ctypes.sizeof(obj_len), ctypes.byref(got), 0),
               "BCryptGetProperty")
        key_object = (ctypes.c_ubyte * obj_len.value)()

        key_buf = (ctypes.c_ubyte * len(key)).from_buffer_copy(key)
        h_key = ctypes.c_void_p()
        _check(bcrypt.BCryptGenerateSymmetricKey(h_alg, ctypes.byref(h_key),
                                                 key_object, obj_len.value,
                                                 key_buf, len(key), 0),
               "BCryptGenerateSymmetricKey")
        try:
            info = BCRYPT_AUTH_INFO()
            ctypes.memset(ctypes.byref(info), 0, ctypes.sizeof(info))
            info.cbSize = ctypes.sizeof(info)
            info.dwInfoVersion = 1
            nonce_buf = (ctypes.c_ubyte * len(nonce)).from_buffer_copy(nonce)
            info.pbNonce = ctypes.cast(nonce_buf, PUCHAR)
            info.cbNonce = len(nonce)
            tag_buf = (ctypes.c_ubyte * len(tag)).from_buffer_copy(tag)
            info.pbTag = ctypes.cast(tag_buf, PUCHAR)
            info.cbTag = len(tag)

            ct_buf = (ctypes.c_ubyte * len(ciphertext)).from_buffer_copy(ciphertext)
            out_buf = (ctypes.c_ubyte * max(len(ciphertext), 1))()
            out_len = wintypes.ULONG(0)
            _check(bcrypt.BCryptDecrypt(h_key, ct_buf, len(ciphertext), ctypes.byref(info),
                                        None, 0, out_buf, len(out_buf),
                                        ctypes.byref(out_len), 0),
                   "BCryptDecrypt")
            return bytes(out_buf[: out_len.value])
        finally:
            bcrypt.BCryptDestroyKey(h_key)
    finally:
        bcrypt.BCryptCloseAlgorithmProvider(h_alg, 0)


def decrypt_cookie_value(value: str, encrypted_value: bytes, key: bytes) -> Tuple[str, int]:
    """返回 (状态, 明文长度)，不返回明文本身。

    状态：plain / v10 / dpapi / empty / error:* / unknown:*
    """
    if value:
        return ("plain", len(value))
    if not encrypted_value:
        return ("empty", 0)
    if encrypted_value[:3] in (b"v10", b"v11"):
        nonce = encrypted_value[3:15]
        ct_and_tag = encrypted_value[15:]
        ciphertext, tag = ct_and_tag[:-16], ct_and_tag[-16:]
        try:
            plain = _aes_gcm_decrypt(key, nonce, ciphertext, tag)
            return ("v10", len(plain))
        except Exception as exc:  # noqa: BLE001 - 校验脚本需吞掉所有异常并报告
            return (f"error:{type(exc).__name__}", 0)
    try:
        plain = _dpapi_unprotect(encrypted_value)
        return ("dpapi", len(plain))
    except Exception as exc:  # noqa: BLE001
        return (f"unknown:{type(exc).__name__}", 0)


# --------------------- 读取 Cookie 库（只读） ---------------------
def _open_cookies_readonly(cookies_path: Path) -> sqlite3.Connection:
    """优先以 immutable 只读 URI 打开（不抢锁、不改文件）；失败则复制副本再读。"""
    try:
        uri = cookies_path.as_uri() + "?mode=ro&immutable=1"
        return sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        tmp = Path(tempfile.gettempdir()) / "ys_pdd_cookie_verify.db"
        shutil.copy2(cookies_path, tmp)
        return sqlite3.connect(str(tmp))


def read_profile_cookies(cookies_path: Path, key: bytes) -> List[Dict[str, object]]:
    conn = _open_cookies_readonly(cookies_path)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT host_key, name, value, encrypted_value FROM cookies"
        ).fetchall()
    finally:
        conn.close()

    result: List[Dict[str, object]] = []
    for row in rows:
        host = str(row["host_key"] or "")
        if not any(marker in host for marker in PDD_HOST_MARKERS):
            continue
        status, length = decrypt_cookie_value(
            row["value"], bytes(row["encrypted_value"] or b""), key
        )
        result.append({"host": host, "name": str(row["name"] or ""), "status": status, "len": length})
    return result


def required_summary(names: List[str]) -> Dict[str, bool]:
    present: Dict[str, bool] = {}
    for req in REQUIRED_EXACT:
        present[req] = any(name == req for name in names)
    for prefix in REQUIRED_PREFIX:
        present[prefix + "*"] = any(name.startswith(prefix) for name in names)
    return present


def main(argv: List[str]) -> int:
    user_data_dir = Path(argv[1]) if len(argv) > 1 else Path(DEFAULT_USER_DATA_DIR)
    print("=" * 68)
    print("拼多多本地客户端 Cookie 只读校验（不修改任何文件 / 不输出明文）")
    print(f"用户数据目录：{user_data_dir}")
    print("=" * 68)

    if not user_data_dir.is_dir():
        print(f"[X] 找不到用户数据目录：{user_data_dir}")
        print("    请确认拼多多商家工作台已安装并至少登录过一次，或手动传入正确路径。")
        return 2

    # 1) 解 AES 主密钥
    try:
        key = load_aes_key(user_data_dir)
        flag = "（符合 AES-256）" if len(key) == 32 else "（异常，预期 32 字节）"
        print(f"[OK] Local State 主密钥解密成功（DPAPI），AES key 长度 {len(key)} 字节 {flag}")
    except Exception as exc:  # noqa: BLE001
        print(f"[X] 主密钥解密失败：{exc}")
        print("    可能原因：当前 Windows 用户与运行客户端的用户不一致，或为 app-bound 加密。")
        return 3

    # 2) 枚举 profile
    profiles: List[Tuple[str, Path]] = []
    for child in sorted(user_data_dir.iterdir()):
        cookies = child / "Network" / "Cookies"
        if cookies.is_file():
            profiles.append((child.name, cookies))
    if not profiles:
        print("[X] 未发现任何包含 Network/Cookies 的 profile。")
        return 4
    print(f"[OK] 发现 {len(profiles)} 个 profile：{', '.join(name for name, _ in profiles)}")
    print("-" * 68)

    overall_ok = False
    for name, cookies_path in profiles:
        try:
            cookies = read_profile_cookies(cookies_path, key)
        except Exception as exc:  # noqa: BLE001
            print(f"[profile {name}] 读取失败：{type(exc).__name__}: {exc}")
            print("-" * 68)
            continue

        if not cookies:
            print(f"[profile {name}] 无 pinduoduo/yangkeduo 域 Cookie，跳过（可能未登录）。")
            print("-" * 68)
            continue

        names = [str(c["name"]) for c in cookies]
        present = required_summary(names)
        decrypted = sum(1 for c in cookies if str(c["status"]) in ("plain", "v10", "dpapi"))
        failed = [c for c in cookies if str(c["status"]).startswith(("error", "unknown"))]
        all_required = all(present.values())

        print(f"[profile {name}]")
        print(f"    pinduoduo 域 Cookie 数：{len(cookies)}，成功解密 {decrypted}，失败 {len(failed)}")
        print("    必需字段：" + "  ".join(f"{k}={'有' if v else '缺'}" for k, v in present.items()))
        print("    Cookie 名称清单：" + ", ".join(sorted(set(names))))
        if failed:
            print(f"    [!] 解密失败示例：{failed[0]['name']} -> {failed[0]['status']}")
        if all_required and decrypted > 0:
            print("    [OK] 该 profile 含完整必需字段且可解密，可用于拼多多本地采集。")
            overall_ok = True
        else:
            print("    [-] 必需字段不全或解密失败，可能该 profile 未登录目标店铺客服。")
        print("-" * 68)

    print("=" * 68)
    if overall_ok:
        print("结论：[OK] 可行。已从本地客户端读取并解密出含完整必需字段的 mms.pinduoduo.com 登录 Cookie。")
        print("      下一步即可把该 Cookie 来源接入现有 pdd_workload_capture 采集链路。")
        return 0
    print("结论：[X] 暂不可行/待确认。未找到含完整必需字段且可解密的 profile，")
    print("      请先在客户端登录目标店铺客服后重试。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
