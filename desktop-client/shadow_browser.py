from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import socket
import subprocess
import time
from typing import Any, Callable, Iterable, Mapping
import winreg

import psutil

DEFAULT_REMOTE_PORT = 9222
DEFAULT_DISK_CACHE_SIZE = 10 * 1024 * 1024
WINDOW_SIZE = "1280,900"
HIDDEN_POSITION = "-2000,-2000"
VISIBLE_POSITION = "120,120"
APP_DIR_NAME = "YuanshengDataAssistant"


class ShadowBrowserError(RuntimeError):
    """Base error for shadow browser lifecycle failures."""


class ChromeNotFoundError(ShadowBrowserError):
    """Raised when Chrome cannot be located on the local machine."""


class PortOccupiedError(ShadowBrowserError):
    """Raised when the target debug port is occupied by a non-shadow process."""


@dataclass
class ShadowBrowserSession:
    page: Any
    chrome_path: str
    profile_dir: str
    port: int
    pid: int | None
    launched: bool
    restarted: bool


def default_shadow_profile_dir() -> Path:
    base_dir = os.environ.get("LOCALAPPDATA")
    if base_dir:
        return Path(base_dir) / APP_DIR_NAME / "shadow-chrome"
    return Path.home() / "AppData" / "Local" / APP_DIR_NAME / "shadow-chrome"


def resolve_chrome_path(config: Mapping[str, Any] | None = None) -> str:
    configured = str((config or {}).get("chromePath") or "").strip()
    if configured and Path(configured).exists():
        return configured

    for key_path in (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
    ):
        registry_path = _read_registry_default(winreg.HKEY_CURRENT_USER, key_path)
        if registry_path and Path(registry_path).exists():
            return registry_path
        registry_path = _read_registry_default(winreg.HKEY_LOCAL_MACHINE, key_path)
        if registry_path and Path(registry_path).exists():
            return registry_path

    for candidate in _common_chrome_paths():
        if candidate.exists():
            return str(candidate)

    raise ChromeNotFoundError("未找到 Chrome。请先安装 Chrome，或在配置中指定 chromePath。")


def attach_or_recover_shadow_browser(
    config: Mapping[str, Any],
    log: Callable[[str], None],
    auto_launch: bool = False,
    force_restart: bool = False,
    visible: bool = False,
) -> ShadowBrowserSession:
    chrome_path = resolve_chrome_path(config)
    port = _resolve_port(config)
    profile_dir = _resolve_profile_dir(config)
    profile_dir.mkdir(parents=True, exist_ok=True)

    if force_restart:
        killed = _kill_shadow_processes(profile_dir, port, log)
        if killed:
            log("已停止原有影子浏览器，准备按新窗口策略重启。")

    if not force_restart:
        attached = _try_attach_session(chrome_path, profile_dir, port, launched=False, restarted=False)
        if attached:
            return attached

    port_open = _port_is_open(port)
    if port_open:
        shadow_processes = _find_shadow_processes(profile_dir, port)
        if shadow_processes:
            _kill_process_list(shadow_processes, log)
            if _wait_for_port_close(port, timeout=6):
                log("检测到残留影子浏览器端口占用，已完成清理。")
            else:
                raise ShadowBrowserError(f"影子浏览器端口 {port} 清理失败，请稍后重试。")
        else:
            raise PortOccupiedError(f"调试端口 {port} 已被其他程序占用，无法启动影子浏览器。")

    if not auto_launch:
        raise ShadowBrowserError("影子浏览器未启动。请先点击“重新登录”打开浏览器。")

    process = _launch_shadow_browser(chrome_path, profile_dir, port, visible=visible)
    session = _wait_for_attach(chrome_path, profile_dir, port, launched=True, restarted=force_restart)
    if session.pid is None:
        session.pid = process.pid
    return session


def ensure_shadow_browser(
    config: Mapping[str, Any],
    log: Callable[[str], None],
    force_restart: bool = False,
    visible: bool = False,
) -> ShadowBrowserSession:
    return attach_or_recover_shadow_browser(
        config=config,
        log=log,
        auto_launch=True,
        force_restart=force_restart,
        visible=visible,
    )


def show_shadow_browser_for_login(config: Mapping[str, Any], log: Callable[[str], None]) -> ShadowBrowserSession:
    return ensure_shadow_browser(config=config, log=log, force_restart=True, visible=True)


def shutdown_shadow_browser(config: Mapping[str, Any], log: Callable[[str], None]) -> int:
    profile_dir = _resolve_profile_dir(config)
    port = _resolve_port(config)
    killed = _kill_shadow_processes(profile_dir, port, log)
    if killed and not _wait_for_port_close(port, timeout=6):
        raise ShadowBrowserError(f"影子浏览器端口 {port} 仍未释放。")
    return killed


def build_shadow_launch_command(chrome_path: str, port: int, profile_dir: Path, visible: bool) -> list[str]:
    position = VISIBLE_POSITION if visible else HIDDEN_POSITION
    return [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--window-position={position}",
        f"--window-size={WINDOW_SIZE}",
        f"--disk-cache-size={DEFAULT_DISK_CACHE_SIZE}",
        "--new-window",
        "about:blank",
    ]


def _launch_shadow_browser(chrome_path: str, profile_dir: Path, port: int, visible: bool) -> subprocess.Popen[str]:
    command = build_shadow_launch_command(chrome_path, port, profile_dir, visible=visible)
    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )


def _wait_for_attach(
    chrome_path: str,
    profile_dir: Path,
    port: int,
    launched: bool,
    restarted: bool,
    timeout: float = 20.0,
) -> ShadowBrowserSession:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            session = _try_attach_session(chrome_path, profile_dir, port, launched=launched, restarted=restarted)
            if session:
                return session
        except Exception as exc:  # pragma: no cover - best effort retry around local browser startup
            last_error = exc
        time.sleep(0.5)
    if last_error is not None:
        raise ShadowBrowserError(f"影子浏览器启动后未能接管：{last_error}") from last_error
    raise ShadowBrowserError("影子浏览器启动后未能接管，请稍后重试。")


def _try_attach_session(
    chrome_path: str,
    profile_dir: Path,
    port: int,
    launched: bool,
    restarted: bool,
) -> ShadowBrowserSession | None:
    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
    except ModuleNotFoundError as exc:
        raise ShadowBrowserError("缺少 DrissionPage，无法接管影子浏览器。") from exc

    co = ChromiumOptions()
    co.set_local_port(port)
    try:
        page = ChromiumPage(co)
        _ = page.title
    except Exception:
        return None
    pid = _find_shadow_pid(profile_dir, port)
    return ShadowBrowserSession(
        page=page,
        chrome_path=chrome_path,
        profile_dir=str(profile_dir),
        port=port,
        pid=pid,
        launched=launched,
        restarted=restarted,
    )


def _resolve_port(config: Mapping[str, Any]) -> int:
    try:
        return int(config.get("chromePort") or DEFAULT_REMOTE_PORT)
    except Exception:
        return DEFAULT_REMOTE_PORT


def _resolve_profile_dir(config: Mapping[str, Any]) -> Path:
    raw = str(config.get("shadowChromeProfileDir") or config.get("chromeUserDataDir") or "").strip()
    return Path(raw) if raw else default_shadow_profile_dir()


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _wait_for_port_close(port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _port_is_open(port):
            return True
        time.sleep(0.2)
    return not _port_is_open(port)


def _find_shadow_pid(profile_dir: Path, port: int) -> int | None:
    processes = _find_shadow_processes(profile_dir, port)
    return processes[0].pid if processes else None


def _find_shadow_processes(profile_dir: Path, port: int) -> list[psutil.Process]:
    matches: list[psutil.Process] = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = process.info.get("cmdline") or []
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if _cmdline_matches_shadow_process(cmdline, profile_dir, port, process.info.get("name")):
            matches.append(process)
    return matches


def _kill_shadow_processes(profile_dir: Path, port: int, log: Callable[[str], None]) -> int:
    processes = _find_shadow_processes(profile_dir, port)
    if not processes:
        return 0
    _kill_process_list(processes, log)
    return len(processes)


def _kill_process_list(processes: Iterable[psutil.Process], log: Callable[[str], None]) -> None:
    for process in processes:
        try:
            log(f"正在清理残留影子浏览器进程 PID={process.pid}。")
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    _, alive = psutil.wait_procs(list(processes), timeout=4)
    for process in alive:
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def _cmdline_matches_shadow_process(
    cmdline: Iterable[str],
    profile_dir: Path,
    port: int,
    process_name: str | None = None,
) -> bool:
    parts = [str(item) for item in cmdline if item]
    if not parts:
        return False
    if process_name and "chrome" not in process_name.lower():
        return False
    normalized_target = _normalize_path(str(profile_dir))
    matched_port = False
    matched_profile = False
    for index, token in enumerate(parts):
        value = token.strip()
        if value == f"--remote-debugging-port={port}":
            matched_port = True
            continue
        if value == "--remote-debugging-port" and index + 1 < len(parts) and parts[index + 1].strip() == str(port):
            matched_port = True
            continue
        if value.startswith("--user-data-dir="):
            matched_profile = _normalize_path(value.split("=", 1)[1]) == normalized_target
            continue
        if value == "--user-data-dir" and index + 1 < len(parts):
            matched_profile = _normalize_path(parts[index + 1]) == normalized_target
    return matched_port and matched_profile


def _normalize_path(raw: str) -> str:
    return str(Path(raw.strip().strip('"')).expanduser()).replace("/", "\\").lower()


def _read_registry_default(root: int, sub_key: str) -> str:
    try:
        with winreg.OpenKey(root, sub_key) as handle:
            value, _ = winreg.QueryValueEx(handle, "")
            return str(value).strip()
    except OSError:
        return ""


def _common_chrome_paths() -> list[Path]:
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe")
    return candidates
