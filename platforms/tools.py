"""外部压缩工具目录约定。

脚本或打包后可执行文件同目录的 ``dependencies/{rar,7z}/`` 是各平台
工具检测链的优先查找位置。7-Zip 安装入口把下载的工具放在
``dependencies/7z/``。
"""

from __future__ import annotations

from pathlib import Path

from core.models import FORMAT_7Z, FORMAT_RAR, FORMAT_ZIP, SCRIPT_DIRECTORY

TOOLS_DIRECTORY = SCRIPT_DIRECTORY / "dependencies"

# zip 与 7z 共用同一 7-Zip 命令行程序。
TOOLS_SUBDIRECTORIES: dict[str, tuple[str, ...]] = {
    FORMAT_RAR: ("rar",),
    FORMAT_7Z: ("7z",),
    FORMAT_ZIP: ("7z",),
}


def tool_directory_candidates(kind: str) -> tuple[Path, ...]:
    """返回 kind 工具在 dependencies 下的候选目录。"""
    return tuple(
        TOOLS_DIRECTORY / subdirectory
        for subdirectory in TOOLS_SUBDIRECTORIES.get(kind, ())
    )
