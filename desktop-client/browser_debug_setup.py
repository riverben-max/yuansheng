from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Any, Dict, List, Mapping

import psutil

BROWSER_DEBUG_PORT = 9527

BROWSER_EXE_NAMES = {"360chromex.exe", "360chrome.exe"}

PLATFORM_COOKIE_DOMAINS: Dict[str, List[str]] = {
    "douyin": ["jinritemai.com", ".douyin.com", ".toutiao.com"],
    "qn": [".taobao.com", ".tmall.com", ".alibaba.com", ".alicdn.com"],
    "jd": [".jd.com", ".jd.hk"],
    "pdd": [".pinduoduo.com", ".yangkeduo.com"],
}

# 各平台登录页 URL（用于「在已运行的浏览器里新开标签页跳转登录」这种轻量场景）
PLATFORM_LOGIN_URLS: Dict[str, str] = {
    "douyin": "https://fxg.jinritemai.com",
    # 千牛：用 myseller 工作台首页而非登录页。未登录会自动跳 loginmyseller，登录后回到首页，
    # 首页加载时会调用 mtop 接口，触发 _m_h5_tk 颁发（千牛采集必需字段）。
    "qn": "https://myseller.taobao.com/home.htm/QnworkbenchHome/",
    "jd": "https://passport.jd.com/new/login.aspx?ReturnUrl=http%3A%2F%2Fkf.jd.com%2F",
    "pdd": "https://mms.pinduoduo.com/login/?redirectUrl=https%3A%2F%2Fmms.pinduoduo.com%2Fmms-chat%2Foverview%2Fmerchant",
}


class BrowserDebugError(RuntimeError):
    pass


class BrowserNotReadyError(BrowserDebugError):
    pass


class ShortcutModifyError(BrowserDebugError):
    pass


def _port_is_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


def _shortcut_search_dirs() -> List[Path]:
    dirs: List[Path] = []
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    if desktop.is_dir():
        dirs.append(desktop)
    public_desktop = Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop"
    if public_desktop.is_dir():
        dirs.append(public_desktop)
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        taskbar = Path(appdata) / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar"
        if taskbar.is_dir():
            dirs.append(taskbar)
        start_menu_user = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        if start_menu_user.is_dir():
            dirs.append(start_menu_user)
    programdata = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    start_menu_all = Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    if start_menu_all.is_dir():
        dirs.append(start_menu_all)
    return dirs


def _read_shortcut(lnk_path: str) -> Dict[str, str]:
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        return {
            "path": lnk_path,
            "target": str(shortcut.Targetpath or ""),
            "arguments": str(shortcut.Arguments or ""),
            "working_dir": str(shortcut.WorkingDirectory or ""),
        }
    except Exception as exc:
        raise ShortcutModifyError(f"读取快捷方式失败：{exc}") from exc


def _write_shortcut_arguments(lnk_path: str, arguments: str) -> None:
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        shortcut.Arguments = arguments
        shortcut.save()
    except Exception as exc:
        raise ShortcutModifyError(f"修改快捷方式失败：{exc}") from exc


def _create_shortcut(lnk_path: str, target: str, arguments: str, working_dir: str = "") -> None:
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        shortcut.Targetpath = target
        shortcut.Arguments = arguments
        shortcut.WorkingDirectory = working_dir or str(Path(target).parent)
        shortcut.save()
    except Exception as exc:
        raise ShortcutModifyError(f"创建快捷方式失败：{exc}") from exc


def _resolve_browser_exe() -> str:
    """解析"采集专用浏览器"的可执行路径（统一 360，不再 fallback 到 Google Chrome）。"""
    # 1. 优先使用正在运行的 360 进程的实际 exe 路径（客户可能装到非标准位置）
    running_360 = _get_running_360_exe()
    if running_360:
        return running_360
    # 2. 通过 shadow_browser 模块的 resolve_chrome_path（已经只查 360）
    try:
        from shadow_browser import resolve_chrome_path
        path = resolve_chrome_path()
        if path and Path(path).exists():
            return path
    except Exception:
        pass
    # 3. 候选标准位置兜底（只列 360）
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\360ChromeX\Chrome\Application\360ChromeX.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\360\360ChromeX\Chrome\Application\360ChromeX.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\360\360ChromeX\Chrome\Application\360ChromeX.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\360Chrome\Chrome\Application\360Chrome.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return ""


def create_debug_shortcut(
    browser_exe_path: str | None = None,
    port: int = BROWSER_DEBUG_PORT,
    shortcut_name: str = "抖店采集专用浏览器",
) -> Dict[str, Any]:
    target = (browser_exe_path or "").strip() or _resolve_browser_exe()
    if not target or not Path(target).exists():
        raise ShortcutModifyError("未找到浏览器可执行文件，无法创建快捷方式。请在配置中指定浏览器路径。")

    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    if not desktop.is_dir():
        raise ShortcutModifyError("未找到桌面目录，无法创建快捷方式。")

    lnk_path = str(desktop / f"{shortcut_name}.lnk")
    arguments = f"--remote-debugging-port={port}"
    _create_shortcut(lnk_path, target, arguments, str(Path(target).parent))
    return {"created": True, "path": lnk_path, "target": target, "arguments": arguments}


def _has_debug_port_arg(arguments: str, port: int) -> bool:
    return f"--remote-debugging-port={port}" in arguments


def find_browser_shortcuts(browser_exe_path: str | None = None) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    search_dirs = _shortcut_search_dirs()
    for search_dir in search_dirs:
        for lnk_file in search_dir.rglob("*.lnk"):
            try:
                info = _read_shortcut(str(lnk_file))
            except ShortcutModifyError:
                continue
            target_lower = info["target"].lower()
            target_name = Path(target_lower).name
            if browser_exe_path:
                if os.path.normcase(info["target"]) != os.path.normcase(browser_exe_path):
                    continue
            else:
                if target_name not in BROWSER_EXE_NAMES:
                    continue
            results.append({
                "path": info["path"],
                "target": info["target"],
                "arguments": info["arguments"],
                "has_debug_port": _has_debug_port_arg(info["arguments"], BROWSER_DEBUG_PORT),
                "is_360": _is_360_target(info["target"]),
            })
    return results


def add_debug_port_to_shortcut(lnk_path: str, port: int = BROWSER_DEBUG_PORT) -> Dict[str, Any]:
    info = _read_shortcut(lnk_path)
    arguments = info["arguments"]
    if _has_debug_port_arg(arguments, port):
        return {"modified": False, "path": lnk_path, "arguments": arguments}
    import re
    arguments = re.sub(r"--remote-debugging-port=\d+", "", arguments).strip()
    new_arg = f"--remote-debugging-port={port}"
    arguments = f"{arguments} {new_arg}".strip() if arguments else new_arg
    _write_shortcut_arguments(lnk_path, arguments)
    return {"modified": True, "path": lnk_path, "arguments": arguments}


def _find_browser_processes() -> List[psutil.Process]:
    procs: List[psutil.Process] = []
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in BROWSER_EXE_NAMES:
                procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs


_THREESIXTY_EXE_NAMES = {"360chromex.exe", "360chrome.exe"}


def _get_running_360_exe() -> str:
    """从正在运行的 360 进程读取实际 exe 路径。客户可能没安装到标准位置或从应用启动器启动。"""
    for proc in _find_browser_processes():
        try:
            name = (proc.info.get("name") or "").lower()
            if name not in _THREESIXTY_EXE_NAMES:
                continue
            exe = proc.exe()
            if exe and Path(exe).exists():
                return exe
        except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
            continue
    return ""


def _is_360_target(target: str) -> bool:
    name = Path(target.lower()).name if target else ""
    return name in _THREESIXTY_EXE_NAMES


def _process_has_debug_port(proc: psutil.Process, port: int) -> bool:
    try:
        cmdline = proc.cmdline()
        for arg in cmdline:
            if arg.strip() == f"--remote-debugging-port={port}":
                return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return False


def detect_browser_debug_status(port: int = BROWSER_DEBUG_PORT) -> Dict[str, Any]:
    browser_procs = _find_browser_processes()
    if not browser_procs:
        return {"status": "not_running"}
    for proc in browser_procs:
        if _process_has_debug_port(proc, port):
            if _port_is_open(port):
                return {"status": "running_with_debug", "port": port}
            return {"status": "running_debug_port_not_ready", "port": port}
    if _port_is_open(port):
        return {"status": "port_occupied_other", "port": port}
    return {"status": "running_no_debug"}


def collect_browser_diagnostics(port: int = BROWSER_DEBUG_PORT) -> List[str]:
    """收集浏览器调试状态详细信息，每行一条客户能看懂的中文，用于打印到运行日志。"""
    lines: List[str] = []
    procs = _find_browser_processes()
    port_open = _port_is_open(port)

    if not procs:
        lines.append(f"诊断 1/3：360 浏览器进程  →  ✗ 未运行")
    else:
        debug_procs = [p for p in procs if _process_has_debug_port(p, port)]
        if debug_procs:
            lines.append(f"诊断 1/3：360 浏览器进程  →  ✓ {len(debug_procs)}/{len(procs)} 个带调试端口启动")
        else:
            lines.append(f"诊断 1/3：360 浏览器进程  →  ✗ {len(procs)} 个进程在运行，但没有一个带调试端口启动")
            lines.append("            原因：浏览器是用任务栏固定图标/老快捷方式/系统自动恢复打开的，不是修改过的桌面快捷方式")

    if port_open:
        lines.append(f"诊断 2/3：调试端口 {port}    →  ✓ 在监听")
    else:
        lines.append(f"诊断 2/3：调试端口 {port}    →  ✗ 未监听（无法读取 Cookie）")

    # 第 3 项：扫描快捷方式状态，特别区分 360 和其他浏览器
    try:
        shortcuts = find_browser_shortcuts()
    except Exception:
        shortcuts = []
    sc_360 = [sc for sc in shortcuts if sc.get("is_360")]
    sc_other = [sc for sc in shortcuts if not sc.get("is_360")]
    if not shortcuts:
        lines.append("诊断 3/3：浏览器快捷方式  →  ✗ 未找到任何 360/Chrome 快捷方式")
    elif not sc_360:
        # 客户机器上没有 360 的快捷方式，但找到了别的浏览器（如 Chrome）
        lines.append(f"诊断 3/3：浏览器快捷方式  →  ⚠ 没找到 360 极速浏览器的快捷方式（只找到 {len(sc_other)} 个其他浏览器的）")
        lines.append("            软件已自动在桌面创建「抖店采集专用浏览器」快捷方式，请用它启动浏览器")
        for sc in sc_other:
            lines.append(f"            · {sc.get('path', '')}（其他浏览器，已忽略）")
    else:
        ready_360 = [sc for sc in sc_360 if sc.get("has_debug_port")]
        lines.append(f"诊断 3/3：360 浏览器快捷方式  →  ✓ {len(ready_360)}/{len(sc_360)} 个已带调试端口")
        for sc in sc_360:
            mark = "✓" if sc.get("has_debug_port") else "✗"
            lines.append(f"            {mark} {sc.get('path', '')}")

    # 给客户的具体下一步建议
    if procs and not any(_process_has_debug_port(p, port) for p in procs):
        lines.append("→ 解决：完全关闭浏览器（包括托盘退出、任务管理器结束所有 360ChromeX），再用桌面「360 极速浏览器X」或「抖店采集专用浏览器」图标双击打开。")
    elif not procs:
        lines.append("→ 解决：双击桌面「360 极速浏览器X」或「抖店采集专用浏览器」图标打开浏览器，登录抖店后台后再点「浏览器」按钮。")
    elif port_open and not any(_process_has_debug_port(p, port) for p in procs):
        lines.append(f"→ 解决：端口 {port} 被其他程序占用，请关闭占用程序后重试。")

    return lines


def grab_cookies_via_cdp(port: int, target_domains: List[str]) -> str:
    if not _port_is_open(port):
        raise BrowserNotReadyError(f"无法连接到浏览器调试端口 {port}，请确认浏览器已启动且带调试参数。")
    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
    except ModuleNotFoundError as exc:
        raise BrowserDebugError("缺少 DrissionPage，无法连接浏览器。") from exc

    co = ChromiumOptions()
    co.set_local_port(port)
    co.existing_only(True)
    page = None
    try:
        try:
            page = ChromiumPage(co)
            _ = page.title  # 触发实际连接，验证可用性
        except Exception as exc:
            raise BrowserNotReadyError(f"连接浏览器失败：{exc}") from exc

        try:
            cookies = page.cookies(all_domains=True)
        except Exception as exc:
            raise BrowserDebugError(f"读取 Cookie 失败：{exc}") from exc

        parts: List[str] = []
        for cookie in cookies:
            if not isinstance(cookie, Mapping):
                continue
            domain = str(cookie.get("domain") or "").lower()
            name = str(cookie.get("name") or "").strip()
            value = str(cookie.get("value") or "").strip()
            if not name:
                continue
            if not target_domains:
                parts.append(f"{name}={value}")
                continue
            for td in target_domains:
                td_lower = td.lower()
                if td_lower.startswith("."):
                    if domain == td_lower or domain.endswith(td_lower):
                        parts.append(f"{name}={value}")
                        break
                else:
                    if domain == td_lower or domain.endswith("." + td_lower):
                        parts.append(f"{name}={value}")
                        break
        return "; ".join(parts)
    finally:
        # 释放 DrissionPage 内部资源（不关闭浏览器，仅断开当前 session）
        if page is not None:
            try:
                page.disconnect()
            except Exception:
                pass


def open_url_in_existing_browser(port: int, url: str) -> bool:
    """在已运行的调试模式浏览器里新开一个标签页打开 ``url``。

    场景：客户的 360 已经在调试模式了（之前流程留下的），但还没登录目标平台。
    我们不重启浏览器（不打扰客户的其他标签），只新开一个 tab 跳到登录页。

    返回 True 表示新标签页已创建；失败抛 BrowserDebugError。
    """
    if not _port_is_open(port):
        raise BrowserNotReadyError(f"无法连接到浏览器调试端口 {port}，浏览器可能未运行。")
    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
    except ModuleNotFoundError as exc:
        raise BrowserDebugError("缺少 DrissionPage，无法连接浏览器。") from exc

    co = ChromiumOptions()
    co.set_local_port(port)
    co.existing_only(True)
    page = None
    try:
        try:
            page = ChromiumPage(co)
            _ = page.title  # 触发实际连接，验证可用性
        except Exception as exc:
            raise BrowserNotReadyError(f"连接浏览器失败：{exc}") from exc

        try:
            page.new_tab(url=url)
            return True
        except Exception as exc:
            raise BrowserDebugError(f"新开标签页失败：{exc}") from exc
    finally:
        if page is not None:
            try:
                page.disconnect()
            except Exception:
                pass
