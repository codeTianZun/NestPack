"""显示 RAR 官网安装指引，下载 7-Zip 到程序同目录。"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from platforms.tool_installer import (  # noqa: E402
    ToolInstallError,
    emit_install_plan,
    install_requested_tools,
)


def build_parser() -> argparse.ArgumentParser:
    """创建外部压缩工具安装脚本的参数解析器。"""
    parser = argparse.ArgumentParser(
        description="RAR 官网安装指引与 7-Zip 自动安装（含许可材料）。"
    )
    parser.add_argument(
        "--tool",
        choices=("rar", "7z", "all"),
        default="all",
        help="rar 显示安装指引，7z 自动安装，all 执行两项（默认）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="已存在也重新下载安装",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="只查看下载地址与目标位置，不安装",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """解析参数并把公共安装异常转换为脚本退出码。"""
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.list:
            emit_install_plan(arguments.tool)
        else:
            install_requested_tools(arguments.tool, arguments.force)
    except ToolInstallError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
