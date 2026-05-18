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

from platform_config import QN_LOGIN_URL
from spider_core import EMPLOYEE_TARGET_URL

DEFAULT_REMOTE_PORT = 9222
DEFAULT_DISK_CACHE_SIZE = 10 * 1024 * 1024
LOGIN_START_URL = QN_LOGIN_URL
WINDOW_SIZE = "1280,900"
VISIBLE_POSITION = "120,120"
HIDDEN_POSITION = VISIBLE_POSITION
APP_DIR_NAME = "YuanshengDataAssistant"


class ShadowBrowserError(RuntimeError):
    """Base error for shadow browser lifecycle failures."""


class ChromeNotFoundError(ShadowBrowserError):
    """Raised when Chrome cannot be located on the local machine."""


class PortOccupiedError(ShadowBrowserError):
    """Raised when the target debug port is occupied by a non-shadow process."""


class DrissionTempBrowserDetected(ShadowBrowserError):
    """Raised when DrissionPage temporary Chrome owns the target debug port."""


@dataclass
class DevToolsEndpoint:
    port: int
    browser_path: str


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
    config = config or {}
    if _normalize_browser_engine(config.get("browserEngine")) == "edge":
        edge_path = _resolve_edge_path(config)
        if edge_path:
            return edge_path

    configured = str(config.get("chromePath") or "").strip()
    if configured and Path(configured).exists():
        return configured

    for key_path in _browser_registry_paths("chrome.exe"):
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


def _resolve_edge_path(config: Mapping[str, Any]) -> str:
    configured = str(config.get("edgePath") or "").strip()
    if configured and Path(configured).exists():
        return configured

    for key_path in _browser_registry_paths("msedge.exe"):
        registry_path = _read_registry_default(winreg.HKEY_CURRENT_USER, key_path)
        if registry_path and Path(registry_path).exists():
            return registry_path
        registry_path = _read_registry_default(winreg.HKEY_LOCAL_MACHINE, key_path)
        if registry_path and Path(registry_path).exists():
            return registry_path

    for candidate in _common_edge_paths():
        if candidate.exists():
            return str(candidate)
    return ""


def attach_or_recover_shadow_browser(
    config: Mapping[str, Any],
    log: Callable[[str], None],
    auto_launch: bool = False,
    force_restart: bool = False,
    visible: bool = False,
) -> ShadowBrowserSession:
    chrome_path = resolve_chrome_path(config)
    profile_dir = _resolve_profile_dir(config)
    profile_dir.mkdir(parents=True, exist_ok=True)
    port = _resolve_attach_port(config, profile_dir)

    if force_restart:
        killed = _kill_shadow_processes(profile_dir, port, log)
        if killed:
            log("已停止原有影子浏览器，准备按新窗口策略重启。")

    if not force_restart:
        attached = _try_attach_session(chrome_path, profile_dir, port, launched=False, restarted=False)
        if attached:
            return attached

    port_open = port > 0 and _port_is_open(port)
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

    launch_port = _resolve_launch_port(config)
    _remove_devtools_active_port(profile_dir)
    process = _launch_shadow_browser(chrome_path, profile_dir, launch_port, visible=visible, startup_url=_resolve_startup_url(config))
    if launch_port == 0:
        endpoint = _wait_for_devtools_active_port(profile_dir)
        if endpoint is None:
            _kill_shadow_processes(profile_dir, 0, log)
            raise ShadowBrowserError("登录窗口启动异常：Chrome 未生成 DevToolsActivePort。")
        port = endpoint.port
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
    session = ensure_shadow_browser(config=config, log=log, force_restart=True, visible=True)
    _open_startup_page_for_login(session.page, _resolve_startup_url(config), log)
    if not show_shadow_browser_window(session.page, log):
        log("影子浏览器已按可见窗口参数启动，但运行时窗口位置校正失败。")
    return session


def launch_shadow_browser_for_login(config: Mapping[str, Any], log: Callable[[str], None]) -> ShadowBrowserSession:
    chrome_path = resolve_chrome_path(config)
    port = _resolve_launch_port(config)
    profile_dir = _resolve_profile_dir(config)
    profile_dir.mkdir(parents=True, exist_ok=True)
    kill_drission_temp_browsers(port, log)

    if port > 0 and _port_is_open(port):
        shadow_processes = _find_shadow_processes(profile_dir, port)
        if shadow_processes:
            _kill_process_list(shadow_processes, log)
            if not _wait_for_port_close(port, timeout=6):
                raise ShadowBrowserError(f"影子浏览器端口 {port} 清理失败，请稍后重试。")
        else:
            raise PortOccupiedError(f"调试端口 {port} 已被其他程序占用，无法启动登录窗口。")

    _remove_devtools_active_port(profile_dir)
    process = _launch_shadow_browser(
        chrome_path=chrome_path,
        profile_dir=profile_dir,
        port=port,
        visible=True,
        startup_url=_resolve_login_startup_url(config),
    )
    runtime_port = port
    if port == 0:
        endpoint = _wait_for_devtools_active_port(profile_dir)
        if endpoint is None:
            _kill_shadow_processes(profile_dir, 0, log)
            raise ShadowBrowserError("登录窗口启动异常：Chrome 未生成 DevToolsActivePort。")
        runtime_port = endpoint.port
    log(f"登录窗口已打开（PID={process.pid}，端口={runtime_port}）。")
    return ShadowBrowserSession(
        page=None,
        chrome_path=chrome_path,
        profile_dir=str(profile_dir),
        port=runtime_port,
        pid=process.pid,
        launched=True,
        restarted=False,
    )


def hide_shadow_browser_window(page: Any, log: Callable[[str], None] | None = None) -> bool:
    # 采集时不再隐藏浏览器。保留函数名兼容旧调用，但实际只校正到可见区域。
    return show_shadow_browser_window(page, log)


def show_shadow_browser_window(page: Any, log: Callable[[str], None] | None = None) -> bool:
    return _move_shadow_browser_window(page, VISIBLE_POSITION, WINDOW_SIZE, log=log, action_name="显示影子浏览器")


def shutdown_shadow_browser(config: Mapping[str, Any], log: Callable[[str], None]) -> int:
    profile_dir = _resolve_profile_dir(config)
    port = _resolve_attach_port(config, profile_dir)
    killed = _kill_shadow_processes(profile_dir, port, log)
    if killed and port > 0 and not _wait_for_port_close(port, timeout=6):
        raise ShadowBrowserError(f"影子浏览器端口 {port} 仍未释放。")
    return killed


def is_shadow_browser_running(config: Mapping[str, Any]) -> bool:
    profile_dir = _resolve_profile_dir(config)
    port = _resolve_attach_port(config, profile_dir)
    expected_pid = int(config.get("shadowChromePid") or 0)
    processes = _find_shadow_processes(profile_dir, port)
    if not expected_pid:
        return bool(processes)
    for process in processes:
        if process.pid == expected_pid:
            return True
    return bool(processes)


def shadow_browser_closed_reason(config: Mapping[str, Any]) -> str:
    expected_pid = _positive_int(config.get("shadowChromePid"))
    active_port = _positive_int(config.get("activeChromePort"))
    if expected_pid <= 0:
        return ""
    if not psutil.pid_exists(expected_pid):
        return "登录窗口进程已退出。"
    if active_port > 0 and not _port_is_open(active_port):
        return f"登录窗口调试端口 {active_port} 已关闭。"
    return ""


def build_shadow_launch_command(
    chrome_path: str,
    port: int,
    profile_dir: Path,
    visible: bool,
    startup_url: str = EMPLOYEE_TARGET_URL,
) -> list[str]:
    position = VISIBLE_POSITION
    url = startup_url.strip() or "about:blank"
    return [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--window-position={position}",
        f"--window-size={WINDOW_SIZE}",
        f"--disk-cache-size={DEFAULT_DISK_CACHE_SIZE}",
        url,
    ]


def _launch_shadow_browser(
    chrome_path: str,
    profile_dir: Path,
    port: int,
    visible: bool,
    startup_url: str,
) -> subprocess.Popen[str]:
    command = build_shadow_launch_command(chrome_path, port, profile_dir, visible=visible, startup_url=startup_url)
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

    if port <= 0:
        endpoint = _read_devtools_active_port(profile_dir)
        if endpoint is None:
            raise ShadowBrowserError("等待登录检测：Chrome 调试端口尚未就绪。")
        port = endpoint.port

    if _find_drission_temp_processes(port):
        raise DrissionTempBrowserDetected(f"检测到 DrissionPage 临时浏览器占用端口 {port}。")
    if _port_is_open(port) and not _find_shadow_processes(profile_dir, port):
        raise PortOccupiedError(f"调试端口 {port} 已被其他 Chrome 占用，无法接管目标登录窗口。")

    co = ChromiumOptions()
    co.set_paths(browser_path=chrome_path, local_port=port, user_data_path=str(profile_dir))
    co.existing_only(True)
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


def _resolve_launch_port(config: Mapping[str, Any]) -> int:
    try:
        raw = config.get("chromePort")
        if raw is None or str(raw).strip() == "":
            return DEFAULT_REMOTE_PORT
        return int(raw)
    except Exception:
        return DEFAULT_REMOTE_PORT


def _resolve_attach_port(config: Mapping[str, Any], profile_dir: Path) -> int:
    active_port = _positive_int(config.get("activeChromePort"))
    if active_port:
        return active_port
    endpoint = _read_devtools_active_port(profile_dir)
    if endpoint is not None:
        return endpoint.port
    raw_port = config.get("chromePort")
    if raw_port is None or str(raw_port).strip() == "":
        return DEFAULT_REMOTE_PORT
    try:
        return int(raw_port)
    except Exception:
        return DEFAULT_REMOTE_PORT


def _positive_int(raw: Any) -> int:
    try:
        value = int(raw)
    except Exception:
        return 0
    return value if value > 0 else 0


def _resolve_profile_dir(config: Mapping[str, Any]) -> Path:
    raw = str(config.get("shadowChromeProfileDir") or config.get("chromeUserDataDir") or "").strip()
    return Path(raw) if raw else default_shadow_profile_dir()


def _resolve_startup_url(config: Mapping[str, Any]) -> str:
    return str(config.get("shadowChromeStartupUrl") or EMPLOYEE_TARGET_URL).strip() or EMPLOYEE_TARGET_URL


def _resolve_login_startup_url(config: Mapping[str, Any]) -> str:
    return str(config.get("shadowChromeStartupUrl") or LOGIN_START_URL).strip() or LOGIN_START_URL


def _move_shadow_browser_window(
    page: Any,
    position: str,
    size: str,
    log: Callable[[str], None] | None,
    action_name: str,
) -> bool:
    try:
        x_text, y_text = position.split(",", 1)
        width_text, height_text = size.split(",", 1)
        page.set.window.normal()
        page.set.window.size(int(width_text), int(height_text))
        page.set.window.location(int(x_text), int(y_text))
        return True
    except Exception as exc:
        if log is not None:
            log(f"{action_name}失败：{exc}")
        return False


def _open_startup_page_for_login(page: Any, startup_url: str, log: Callable[[str], None]) -> None:
    try:
        current_url = str(getattr(page, "url", "") or "")
        if _is_noise_or_unrelated_page(current_url):
            page.get(startup_url)
            time.sleep(1)
        log(f"当前接管页面：{getattr(page, 'title', '') or '--'} {getattr(page, 'url', '') or '--'}")
    except Exception as exc:
        log(f"登录页导航失败：{exc}")


def _is_noise_or_unrelated_page(url: str) -> bool:
    normalized = str(url or "").strip().lower()
    if not normalized:
        return True
    if normalized.startswith(("about:blank", "chrome://newtab", "chrome://new-tab-page")):
        return True
    return "google." in normalized and not any(marker in normalized for marker in ("taobao.com", "tmall.com", "myseller"))


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


def _read_devtools_active_port(profile_dir: Path) -> DevToolsEndpoint | None:
    path = profile_dir / "DevToolsActivePort"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    try:
        port = int(lines[0])
    except ValueError:
        return None
    browser_path = lines[1] if len(lines) > 1 else ""
    return DevToolsEndpoint(port=port, browser_path=browser_path)


def _wait_for_devtools_active_port(profile_dir: Path, timeout: float = 8.0) -> DevToolsEndpoint | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        endpoint = _read_devtools_active_port(profile_dir)
        if endpoint is not None:
            return endpoint
        time.sleep(0.2)
    return _read_devtools_active_port(profile_dir)


def _remove_devtools_active_port(profile_dir: Path) -> None:
    try:
        (profile_dir / "DevToolsActivePort").unlink(missing_ok=True)
    except OSError:
        pass


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


def kill_drission_temp_browsers(port: int, log: Callable[[str], None]) -> int:
    if port <= 0:
        return 0
    processes = _find_drission_temp_processes(port)
    if not processes:
        return 0
    _kill_process_list(processes, log)
    return len(processes)


def _find_drission_temp_processes(port: int) -> list[psutil.Process]:
    if port <= 0:
        return []
    matches: list[psutil.Process] = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = process.info.get("cmdline") or []
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if _cmdline_matches_drission_temp_process(cmdline, port, process.info.get("name")):
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
    matched_profile = False
    for index, token in enumerate(parts):
        value = token.strip()
        if value.startswith("--user-data-dir="):
            matched_profile = _normalize_path(value.split("=", 1)[1]) == normalized_target
            continue
        if value == "--user-data-dir" and index + 1 < len(parts):
            matched_profile = _normalize_path(parts[index + 1]) == normalized_target
    return matched_profile


def _cmdline_matches_drission_temp_process(
    cmdline: Iterable[str],
    port: int,
    process_name: str | None = None,
) -> bool:
    parts = [str(item) for item in cmdline if item]
    if not parts:
        return False
    if process_name and "chrome" not in process_name.lower():
        return False
    matched_port = False
    matched_drission_profile = False
    marker = f"\\temp\\drissionpage\\userdata\\{port}"
    for index, token in enumerate(parts):
        value = token.strip()
        if value == f"--remote-debugging-port={port}":
            matched_port = True
            continue
        if value == "--remote-debugging-port" and index + 1 < len(parts) and parts[index + 1].strip() == str(port):
            matched_port = True
            continue
        if value.startswith("--user-data-dir="):
            matched_drission_profile = marker in _normalize_path(value.split("=", 1)[1])
            continue
        if value == "--user-data-dir" and index + 1 < len(parts):
            matched_drission_profile = marker in _normalize_path(parts[index + 1])
    return matched_port and matched_drission_profile


def _normalize_path(raw: str) -> str:
    return str(Path(raw.strip().strip('"')).expanduser()).replace("/", "\\").lower()


def _read_registry_default(root: int, sub_key: str) -> str:
    try:
        with winreg.OpenKey(root, sub_key) as handle:
            value, _ = winreg.QueryValueEx(handle, "")
            return str(value).strip()
    except OSError:
        return ""


def _normalize_browser_engine(raw: Any) -> str:
    return str(raw or "").strip().lower()


def _browser_registry_paths(exe_name: str) -> tuple[str, str]:
    return (
        rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}",
        rf"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}",
    )


def _common_chrome_paths() -> list[Path]:
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe")
    return candidates


def _common_edge_paths() -> list[Path]:
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Microsoft" / "Edge" / "Application" / "msedge.exe")
    return candidates
