"""千牛 Cookie 刷新：注入 Cookie 到影子浏览器 → 启动浏览器访问页面 → 等待 _m_h5_tk 刷新 → 关闭 → 读取新 Cookie。"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from chrome_cookie_store import inject_cookies_to_profile, read_cookies_from_profile
from secure_storage import unprotect_text
from shadow_browser import resolve_chrome_path

QN_REFRESH_URL = "https://myseller.taobao.com/home.htm/QnworkbenchHome/"
REFRESH_WAIT_SECONDS = 15
REFRESH_TIMEOUT_SECONDS = 30
_LAUNCH_FLAGS = [
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-translate",
    "--disable-component-update",
    "--disable-hang-monitor",
    "--disable-crash-reporter",
    "--window-position=9999,9999",
    "--window-size=800,600",
]


class QnCookieRefreshError(RuntimeError):
    pass


def refresh_qn_cookie(
    state: Mapping[str, Any],
    log: Callable[[str], None],
    wait_seconds: float = REFRESH_WAIT_SECONDS,
) -> str:
    """刷新千牛 _m_h5_tk，返回完整的新 Cookie header。"""
    cookie_header = _load_cookie(state)
    profile_dir = Path(str(state.get("shadowChromeProfileDir") or state.get("chromeUserDataDir") or ""))
    if not profile_dir or str(profile_dir).strip() == "":
        raise QnCookieRefreshError("未配置影子浏览器 profile 目录。")

    chrome_path = resolve_chrome_path(state)
    log("千牛 Cookie 刷新：注入 Cookie 到浏览器 profile...")
    count = inject_cookies_to_profile(profile_dir, cookie_header)
    log(f"千牛 Cookie 刷新：已注入 {count} 条 Cookie。")

    log("千牛 Cookie 刷新：启动浏览器访问千牛页面...")
    process = _launch_browser(chrome_path, profile_dir)

    try:
        log(f"千牛 Cookie 刷新：等待 {wait_seconds} 秒让页面加载并刷新 token...")
        time.sleep(wait_seconds)
    finally:
        _kill_browser(process, log)

    log("千牛 Cookie 刷新：从 profile 读取刷新后的 Cookie...")
    new_cookie = read_cookies_from_profile(profile_dir)
    if not new_cookie:
        raise QnCookieRefreshError("千牛 Cookie 刷新失败：浏览器关闭后未能读取到 Cookie。")

    if "_m_h5_tk" not in new_cookie:
        log("千牛 Cookie 刷新：警告 - 新 Cookie 中未包含 _m_h5_tk，可能需要重新导入。")

    log(f"千牛 Cookie 刷新完成：新 Cookie 长度 {len(new_cookie)}。")
    return new_cookie


def _load_cookie(state: Mapping[str, Any]) -> str:
    protected = str(state.get("cookieProtected") or "").strip()
    if not protected:
        raise QnCookieRefreshError("千牛账号未保存 Cookie，请先通过导入Cookie粘贴 cURL。")
    try:
        cookie = str(unprotect_text(protected) or "").strip()
    except Exception as exc:
        raise QnCookieRefreshError(f"千牛 Cookie 解密失败：{exc}") from exc
    if not cookie:
        raise QnCookieRefreshError("千牛 Cookie 为空，请重新导入。")
    return cookie


def _launch_browser(chrome_path: str, profile_dir: Path) -> subprocess.Popen:
    cmd = [chrome_path, f"--user-data-dir={profile_dir}"] + _LAUNCH_FLAGS + [QN_REFRESH_URL]
    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )


def _kill_browser(process: subprocess.Popen, log: Callable[[str], None]) -> None:
    try:
        import psutil
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        parent.kill()
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
    log("千牛 Cookie 刷新：浏览器已关闭。")
