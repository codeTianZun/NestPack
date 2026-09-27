"""归档平台适配接口。

core 层只依赖本协议，不直接 import 任何平台特定模块。工具检测按
格式 kind（"rar" / "7z" / "zip"）区分，候选程序必须支持对应格式。
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ArchivePlatform(Protocol):
    """平台相关的可执行文件检测、文件名校验与后台开关。"""

    def executable_candidates(self, kind: str = "rar") -> tuple[str, ...]:
        """用于 PATH 搜索的可执行文件名。"""
        ...

    def find_tool(self, kind: str = "rar") -> Path | None:
        """自动检测指定格式的命令行工具路径；找不到返回 None。"""
        ...

    def resolve_tool(
        self, configured: str, config_dir: Path, kind: str = "rar"
    ) -> Path:
        """把 auto 或配置中的路径解析为可执行文件，失败抛 ConfigError。"""
        ...

    def background_switch(self) -> tuple[str, ...]:
        """后台运行开关参数；没有该概念的平台返回空元组。"""
        ...

    def validate_filename(self, raw: str) -> str:
        """校验归档文件名合法性并按平台规则修正；失败抛 ValueError。

        扩展名补全（.rar / .7z / .zip）由 core 按层格式处理，不在此进行。
        """
        ...
