from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import os


PROTECTED_TEXT_PREFIX = "dpapi:v1:"


class SecureStorageError(RuntimeError):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def protect_text(plaintext: str) -> str:
    value = str(plaintext or "")
    if not value:
        raise SecureStorageError("Cannot encrypt empty value.")
    encrypted = _crypt_protect(value.encode("utf-8"))
    return PROTECTED_TEXT_PREFIX + base64.b64encode(encrypted).decode("ascii")


def unprotect_text(protected_text: str) -> str:
    value = str(protected_text or "")
    if not value.startswith(PROTECTED_TEXT_PREFIX):
        raise SecureStorageError("Cannot decrypt protected value: unsupported format.")
    encoded = value[len(PROTECTED_TEXT_PREFIX):]
    try:
        encrypted = base64.b64decode(encoded.encode("ascii"), validate=True)
        plaintext = _crypt_unprotect(encrypted)
        return plaintext.decode("utf-8")
    except SecureStorageError:
        raise
    except Exception as exc:
        raise SecureStorageError(f"Cannot decrypt protected value: {exc}") from exc


def _require_windows() -> None:
    if os.name != "nt":
        raise SecureStorageError("Windows DPAPI secure storage is only available on Windows.")


def _crypt_protect(data: bytes) -> bytes:
    _require_windows()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    in_buffer = ctypes.create_string_buffer(data)
    in_blob = _DataBlob(len(data), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_byte)))
    out_blob = _DataBlob()

    if not crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise SecureStorageError(f"Cannot encrypt value with DPAPI: Windows error {ctypes.get_last_error()}.")

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)


def _crypt_unprotect(data: bytes) -> bytes:
    _require_windows()
    if not data:
        raise SecureStorageError("Cannot decrypt protected value: empty ciphertext.")

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    in_buffer = ctypes.create_string_buffer(data)
    in_blob = _DataBlob(len(data), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_byte)))
    out_blob = _DataBlob()

    if not crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise SecureStorageError(f"Cannot decrypt protected value: Windows error {ctypes.get_last_error()}.")

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)
