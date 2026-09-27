"""Linux 平台实现。"""

from __future__ import annotations

from pathlib import Path

from core.models import FORMAT_RAR

from .detection import RAR_TOOL_NAMES, SEVENZIP_TOOL_NAMES, find_tool, resolve_tool
from .filename_rules import validate_filename


class LinuxArchivePlatform:
    """Linux 上的 rar / 7-Zip 命令行检测与文件名校验。"""

    def executable_candidates(self, kind: str = "rar") -> tuple[str, ...]:
        # 非 rar（7z / zip）一律视为 7z 家族工具。
        return RAR_TOOL_NAMES if kind == FORMAT_RAR else SEVENZIP_TOOL_NAMES

    def find_tool(self, kind: str = "rar") -> Path | None:
        return find_tool(kind)

    def resolve_tool(
        self, configured: str, config_dir: Path, kind: str = "rar"
    ) -> Path:
        return resolve_tool(configured, config_dir, kind)

    def background_switch(self) -> tuple[str, ...]:
        return ()

    def validate_filename(self, raw: str) -> str:
        return validate_filename(raw)


__all__ = ["LinuxArchivePlatform"]
