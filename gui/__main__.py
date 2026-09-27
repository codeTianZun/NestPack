"""Windows 图形界面入口：python -m gui。"""

import sys


def main() -> int:
    """在加载 Qt 前检查运行平台。"""
    if sys.platform != "win32":
        print("NestPack 图形界面仅支持 Windows；Linux 请使用 python3 -m cli。", file=sys.stderr)
        return 1

    from gui.main import main as run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
