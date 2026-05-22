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
    import tempfile, shutil

    cookie_header = _load_cookie(state)
    chrome_path = resolve_chrome_path(state)

    # 使用临时 profile 目录（避免旧 profile 权限问题）
    tmp_profile = Path(tempfile.mkdtemp(prefix="ys_qn_refresh_"))
    try:
        log("千牛 Cookie 刷新：注入 Cookie 到浏览器 profile...")
        count = inject_cookies_to_profile(tmp_profile, cookie_header)
        log(f"千牛 Cookie 刷新：已注入 {count} 条 Cookie。")

        log("千牛 Cookie 刷新：启动浏览器访问千牛页面...")
        process = _launch_browser(chrome_path, tmp_profile)

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
    finally:
        shutil.rmtree(tmp_profile, ignore_errors=True)


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
    _ensure_port_free()
    cmd = [
        chrome_path,
        f"--user-data-dir={profile_dir}",
        f"--remote-debugging-port={DEBUG_PORT}",
        "--remote-allow-origins=*",
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


def _ensure_port_free() -> None:
    """确保 DEBUG_PORT 没被旧进程占用。"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(("127.0.0.1", DEBUG_PORT))
        if result == 0:
            # 端口被占，杀掉占用它的进程
            sock.close()
            try:
                import psutil
                for conn in psutil.net_connections(kind="tcp"):
                    if conn.laddr.port == DEBUG_PORT and conn.pid:
                        try:
                            psutil.Process(conn.pid).kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                time.sleep(2)
            except ImportError:
                pass
        else:
            sock.close()
    except Exception:
        sock.close()


def _read_cookies_via_devtools() -> str:
    """通过 Chrome DevTools Protocol 读取所有 taobao.com 域的 Cookie。"""
    try:
        import websocket
    except ImportError:
        return ""

    # 重试最多 3 次（等端口就绪）
    for attempt in range(3):
        try:
            version_url = f"http://127.0.0.1:{DEBUG_PORT}/json/version"
            req = urllib.request.Request(version_url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                version_info = json.loads(resp.read().decode("utf-8"))
            browser_ws = version_info.get("webSocketDebuggerUrl", "")
            if not browser_ws:
                time.sleep(2)
                continue

            ws = websocket.create_connection(browser_ws, timeout=10)
            ws.send(json.dumps({"id": 1, "method": "Storage.getCookies"}))
            result = json.loads(ws.recv())
            ws.close()

            cookies = result.get("result", {}).get("cookies", [])
            parts = []
            for c in cookies:
                domain = c.get("domain", "")
                if "taobao.com" in domain or "alicdn.com" in domain:
                    parts.append(f"{c['name']}={c['value']}")
            if parts:
                return "; ".join(parts)
            time.sleep(2)
        except Exception:
            time.sleep(3)
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
