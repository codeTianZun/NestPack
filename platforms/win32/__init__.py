"""Windows 平台实现。"""

from __future__ import annotations

from pathlib import Path

from .detection import (
    executable_candidates,
    find_tool,
    resolve_tool,
)
from .filename_rules import validate_filename


class Win32ArchivePlatform:
    """Windows 上的 WinRAR / 7-Zip 检测与文件名校验。"""

    def executable_candidates(self, kind: str = "rar") -> tuple[str, ...]:
        return executable_candidates(kind)

    def find_tool(self, kind: str = "rar") -> Path | None:
        return find_tool(kind)

    def resolve_tool(
        self, configured: str, config_dir: Path, kind: str = "rar"
    ) -> Path:
        return resolve_tool(configured, config_dir, kind)

    def background_switch(self) -> tuple[str, ...]:
        # -inul 禁止一切错误弹窗：-ibck 隐藏了 WinRAR 窗口，此时弹出的
        # 模态错误框用户看不见，进程会永远停在等待点击上，错误只能
        # 经退出码上报。
        return ("-ibck", "-inul")

    def validate_filename(self, raw: str) -> str:
        return validate_filename(raw)


__all__ = ["Win32ArchivePlatform"]
