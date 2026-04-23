from __future__ import annotations

import sys

try:
    from desktop_app import run
except ModuleNotFoundError as exc:
    if exc.name == "PySide6":
        print("缺少 PySide6，无法启动桌面版远盛数据助手。")
        print("请先执行：python -m pip install -r requirements.txt")
        sys.exit(1)
    raise


if __name__ == "__main__":
    raise SystemExit(run())
