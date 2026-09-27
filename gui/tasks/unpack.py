"""解包执行：工具解析、候选密码快照与用户取消。"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject

from core.models import FORMAT_7Z
from core.unpack import unpack_archive
from gui.tasks.threading import BackgroundTask, TaskWorker
from platforms import resolve_optional_tool


class UnpackWorker(TaskWorker):
    """在独立线程中逐层解包。"""

    def __init__(
        self,
        rar_tool: Path | None,
        sevenzip_tool: Path | None,
        archive: Path,
        output_dir: Path,
        candidates: list[str],
        layer_limit: int | None,
        cancel_event: threading.Event,
    ) -> None:
        super().__init__("解包失败")
        self._rar_tool = rar_tool
        self._sevenzip_tool = sevenzip_tool
        self._archive = archive
        self._output_dir = output_dir
        self._candidates = list(candidates)
        self._layer_limit = layer_limit
        self._cancel_event = cancel_event

    def execute(self) -> list[Path]:
        self.log.emit(
            f"WinRAR：{self._rar_tool}"
            if self._rar_tool else "WinRAR：未检测到（遇到 rar 层时无法解）"
        )
        self.log.emit(
            f"7-Zip：{self._sevenzip_tool}"
            if self._sevenzip_tool else "7-Zip：未检测到（遇到 7z / zip 层时无法解）"
        )
        self.log.emit(f"解包输出目录：{self._output_dir}")
        self.log.emit("开始解包…")
        entries = unpack_archive(
            self._archive,
            self._output_dir,
            rar_tool=self._rar_tool,
            sevenzip_tool=self._sevenzip_tool,
            candidates=self._candidates,
            layer_limit=self._layer_limit,
            cancel_event=self._cancel_event,
            output_cb=self.log.emit,
        )
        self.log.emit(f"解包完成，共恢复 {len(entries)} 个条目。")
        return entries


class UnpackTask(BackgroundTask):
    """解析本次解包工具并持有执行期间的取消事件。"""

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._cancel_event = threading.Event()

    def start(
        self,
        archive: Path,
        output_dir: Path,
        candidates: list[str],
        layer_limit: int | None,
        *,
        winrar_configured: str,
        sevenzip_configured: str,
        config_dir: Path,
    ) -> None:
        """解析工具后启动解包，输入错误直接交给调用方展示。"""
        if not archive.is_file():
            raise ValueError(f"找不到压缩包：{archive}")
        rar_tool = resolve_optional_tool(winrar_configured, config_dir)
        sevenzip_tool = resolve_optional_tool(sevenzip_configured, config_dir, kind=FORMAT_7Z)
        if rar_tool is None and sevenzip_tool is None:
            raise ValueError("未找到任何可用的压缩命令行（WinRAR 与 7z 均未检测到）。")
        self._cancel_event = threading.Event()
        self._start(UnpackWorker(
            rar_tool, sevenzip_tool, archive, output_dir, candidates,
            layer_limit, self._cancel_event,
        ))

    def cancel(self) -> None:
        """请求停止解包，已解内容的保留由 core 处理。"""
        self._cancel_event.set()
