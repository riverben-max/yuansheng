"""Chrome Cookie 数据库读写工具。

将 Cookie 字符串注入到 Chrome profile 的 SQLite 数据库，
或从数据库中读取 Cookie 拼为 header 字符串。
"""
from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import List, Tuple

_CHROME_EPOCH = datetime.datetime(1601, 1, 1)
_DEFAULT_EXPIRE_DAYS = 30
_TAOBAO_DOMAINS = (".taobao.com", ".m.taobao.com", ".alicdn.com")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cookies (
    creation_utc INTEGER NOT NULL,
    host_key TEXT NOT NULL,
    top_frame_site_key TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    encrypted_value BLOB NOT NULL DEFAULT x'',
    path TEXT NOT NULL DEFAULT '/',
    expires_utc INTEGER NOT NULL DEFAULT 0,
    is_secure INTEGER NOT NULL DEFAULT 1,
    is_httponly INTEGER NOT NULL DEFAULT 0,
    last_access_utc INTEGER NOT NULL DEFAULT 0,
    has_expires INTEGER NOT NULL DEFAULT 1,
    is_persistent INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 1,
    samesite INTEGER NOT NULL DEFAULT -1,
    source_scheme INTEGER NOT NULL DEFAULT 2,
    source_port INTEGER NOT NULL DEFAULT 443,
    last_update_utc INTEGER NOT NULL DEFAULT 0,
    source_type INTEGER NOT NULL DEFAULT 0,
    has_cross_site_ancestor INTEGER NOT NULL DEFAULT 0
)
"""


def _now_chrome_utc() -> int:
    delta = datetime.datetime.utcnow() - _CHROME_EPOCH
    return int(delta.total_seconds() * 1_000_000)


def _parse_cookie_header(cookie_header: str) -> List[Tuple[str, str]]:
    parts = []
    for part in str(cookie_header or "").split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name.strip():
            parts.append((name.strip(), value.strip()))
    return parts


def _cookies_db_path(profile_dir: Path) -> Path:
    return profile_dir / "Default" / "Network" / "Cookies"


def inject_cookies_to_profile(profile_dir: Path, cookie_header: str, domain: str = ".taobao.com") -> int:
    """将 Cookie header 字符串写入 Chrome profile 的 Cookies 数据库。返回写入条数。"""
    import shutil

    cookies = _parse_cookie_header(cookie_header)
    if not cookies:
        return 0

    db_path = _cookies_db_path(profile_dir)
    # 确保目录存在，删除旧的损坏文件
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for f in db_path.parent.glob("Cookies*"):
        try:
            f.unlink()
        except OSError:
            pass

    now = _now_chrome_utc()
    expires = now + _DEFAULT_EXPIRE_DAYS * 24 * 3600 * 1_000_000

    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(_CREATE_TABLE_SQL)
    c.execute("DELETE FROM cookies WHERE host_key = ?", (domain,))
    for name, value in cookies:
        c.execute(
            "INSERT INTO cookies (creation_utc, host_key, top_frame_site_key, name, value, encrypted_value, path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires, is_persistent, priority, samesite, source_scheme, source_port, last_update_utc, source_type, has_cross_site_ancestor) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (now, domain, "", name, value, b"", "/", expires, 1, 0, now, 1, 1, 1, -1, 2, 443, now, 0, 0),
        )
    conn.commit()
    conn.close()
    return len(cookies)


def read_cookies_from_profile(profile_dir: Path, domain_filter: str = ".taobao.com") -> str:
    """从 Chrome profile 的 Cookies 数据库读取指定域名的 Cookie，返回 header 字符串。"""
    import os, tempfile, time

    db_path = _cookies_db_path(profile_dir)
    if not db_path.exists():
        return ""

    # 等待浏览器进程完全释放文件
    time.sleep(2)

    # 复制数据库文件避免锁冲突
    tmp = os.path.join(tempfile.gettempdir(), "ys_cookie_read.db")
    os.system(f'cmd /c copy /Y "{db_path}" "{tmp}" >nul 2>&1')
    if not os.path.exists(tmp) or os.path.getsize(tmp) < 100:
        return ""

    try:
        conn = sqlite3.connect(tmp)
        c = conn.cursor()
        c.execute(
            "SELECT name, value FROM cookies WHERE host_key = ? AND value != '' ORDER BY creation_utc",
            (domain_filter,),
        )
        rows = c.fetchall()
        conn.close()
    except sqlite3.OperationalError:
        rows = []
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    if not rows:
        return ""
    return "; ".join(f"{name}={value}" for name, value in rows)
