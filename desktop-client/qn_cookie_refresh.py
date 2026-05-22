"""千牛 Cookie 刷新：注入 Cookie 到影子浏览器 → 启动浏览器访问页面 → 通过 DevTools 读取刷新后的 Cookie → 关闭。"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping

from chrome_cookie_store import inject_cookies_to_profile
from secure_storage import unprotect_text
from shadow_browser import resolve_chrome_path

QN_REFRESH_URL = "https://myseller.taobao.com/home.htm/QnworkbenchHome/"
REFRESH_WAIT_SECONDS = 15
DEBUG_PORT = 19222
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
        log("千牛 Cookie 刷新：通过 DevTools 读取 Cookie...")
        new_cookie = _read_cookies_via_devtools()
    finally:
        _kill_browser(process, log)

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
    cmd = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        f"--remote-debugging-port={DEBUG_PORT}",
    ] + _LAUNCH_FLAGS + [QN_REFRESH_URL]
    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )


def _read_cookies_via_devtools() -> str:
    """通过 Chrome DevTools Protocol 读取所有 taobao.com 域的 Cookie。"""
    try:
        url = f"http://127.0.0.1:{DEBUG_PORT}/json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            pages = json.loads(resp.read().decode("utf-8"))
        if not pages:
            return ""
        # 用第一个页面的 ws 地址通过 HTTP 接口获取 cookie
        # CDP 的 Network.getAllCookies 需要 WebSocket，用 /json/protocol 太复杂
        # 简单方案：用 CDP HTTP endpoint 直接发命令
        ws_url = pages[0].get("webSocketDebuggerUrl", "")
        if not ws_url:
            return ""
        # 用 HTTP 发 CDP 命令获取 Cookie
        browser_url = f"http://127.0.0.1:{DEBUG_PORT}/json/version"
        with urllib.request.urlopen(browser_url, timeout=5) as resp:
            version_info = json.loads(resp.read().decode("utf-8"))
        browser_ws = version_info.get("webSocketDebuggerUrl", "")
        if not browser_ws:
            return ""
        # 通过简单 HTTP 方式：直接用 page 的 evaluate 执行 document.cookie
        page_id = pages[0].get("id", "")
        eval_url = f"http://127.0.0.1:{DEBUG_PORT}/json/evaluate?id={page_id}"
        # 更简单：直接用 requests 到 CDP endpoint
        # 最简单方案：用 websocket-free 的方式 - 读 DevTools 的 /json/protocol 不行
        # 真正简单的方案：通过页面执行 JS 获取 cookie
        import websocket
        ws = websocket.create_connection(ws_url, timeout=5)
        ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
        result = json.loads(ws.recv())
        ws.close()
        cookies = result.get("result", {}).get("cookies", [])
        parts = []
        for c in cookies:
            domain = c.get("domain", "")
            if ".taobao.com" in domain or "taobao.com" in domain:
                parts.append(f"{c['name']}={c['value']}")
        return "; ".join(parts)
    except ImportError:
        # websocket 库不可用，回退到 SQLite 读取
        return ""
    except Exception:
        return ""


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
        parent.wait(timeout=5)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=5)
        except Exception:
            pass
    time.sleep(2)
    log("千牛 Cookie 刷新：浏览器已关闭。")
