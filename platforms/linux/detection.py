"""Linux 上的 rar / 7-Zip 命令行程序检测。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from core.filesystem import normalize_user_path
from core.models import FORMAT_RAR, ConfigError
from platforms.tools import tool_directory_candidates

RAR_TOOL_NAMES = ("rar",)
# 7zz 是 7-Zip 官方 Linux 版（全格式）；7z 来自 p7zip；7za 是独立版。
# 均可创建 / 解开 zip。
SEVENZIP_TOOL_NAMES = ("7zz", "7z", "7za")


def find_tool(kind: str = "rar") -> Path | None:
    """依次从程序同目录 dependencies 与 PATH 查找命令行工具。"""
    # kind 按格式名传入，非 rar（7z / zip）一律视为 7z 家族工具。
    names = RAR_TOOL_NAMES if kind == FORMAT_RAR else SEVENZIP_TOOL_NAMES

    # 程序同目录 dependencies（内置安装入口的落盘位置）最优先。
    for directory in tool_directory_candidates(kind):
        for name in names:
            candidate = directory / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate.resolve()

    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found).resolve()
    return None


def resolve_tool(
    configured_path: str, config_directory: Path, kind: str = "rar"
) -> Path:
    """将 auto 或配置中的具体路径转换成可执行文件路径。"""
    if configured_path.strip().lower() == "auto":
        detected = find_tool(kind)
        if detected:
            return detected
        if kind != FORMAT_RAR:
            raise ConfigError(
                "sevenzip_path 为 auto，但没有找到 7z 命令；"
                "请安装 7-Zip / p7zip，或填写完整路径"
            )
        raise ConfigError(
            "winrar_path 为 auto，但没有找到 rar 命令；"
            "请安装 rarlab 官方 rar 命令行，或填写完整路径"
        )

    executable = normalize_user_path(configured_path, config_directory)
    if not executable.is_file():
        raise ConfigError(f"找不到命令行程序：{executable}")
    if not os.access(executable, os.X_OK):
        raise ConfigError(f"程序没有执行权限：{executable}")
    return executable
