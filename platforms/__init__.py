"""平台适配：按 sys.platform 选择归档工具平台实现。

core 层只依赖本模块提供的 get_archive_platform()，不直接 import
任何平台特定模块，从而保证核心逻辑可以在 Windows 与 Linux 上复用。
"""

from __future__ import annotations

import sys
from pathlib import Path

from .base import ArchivePlatform

_PLATFORM: ArchivePlatform | None = None


def _create_platform() -> ArchivePlatform:
    if sys.platform == "win32":
        from .win32 import Win32ArchivePlatform

        return Win32ArchivePlatform()
    if sys.platform == "linux":
        from .linux import LinuxArchivePlatform

        return LinuxArchivePlatform()
    raise RuntimeError(f"不支持的平台：{sys.platform}；NestPack 仅支持 Windows 与 Linux。")


def get_archive_platform() -> ArchivePlatform:
    """返回当前系统的归档平台实现，结果缓存避免重复构造。"""
    global _PLATFORM
    if _PLATFORM is None:
        _PLATFORM = _create_platform()
    return _PLATFORM


def resolve_optional_tool(
    configured_path: str, config_directory: Path, kind: str = "rar"
) -> Path | None:
    """尽力解析工具路径：auto 未找到返回 None；显式路径无效仍抛 ConfigError。

    解包链路用：外层格式未知前不应因为缺某种工具而拒绝启动，只在
    真正解到对应格式时才要求工具可用。
    """
    if configured_path.strip().lower() == "auto":
        return get_archive_platform().find_tool(kind)
    return get_archive_platform().resolve_tool(configured_path, config_directory, kind)


__all__ = ["ArchivePlatform", "get_archive_platform", "resolve_optional_tool"]
