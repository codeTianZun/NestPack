"""压缩执行：计划快照、进度转发与用户取消。"""

from __future__ import annotations

import re
import threading

from PySide6.QtCore import QObject

from core.compression import CompressionPlan, CompressionResult, run_compression
from gui.tasks.threading import BackgroundTask, TaskWorker

PERCENT_PATTERN = re.compile(r"(\d+)\s*%")


class CompressionWorker(TaskWorker):
    """在独立线程中执行压缩，避免主窗口卡死。"""

    def __init__(self, plan: CompressionPlan, cancel_event: threading.Event) -> None:
        super().__init__("打包失败")
        self.plan = plan
        self.cancel_event = cancel_event
        self._total = plan.total_layers
        self._current_layer = 1

    def execute(self) -> CompressionResult:
        self.log.emit("开始打包…")
        result = run_compression(
            self.plan,
            progress_cb=self._on_progress,
            cancel_event=self.cancel_event,
            output_cb=self._on_output,
        )
        self.log.emit(f"全部打包完成，共 {result.plan.total_layers} 层。")
        return result

    def _on_progress(self, number: int, total: int, message: str) -> None:
        if number < total:
            self._current_layer = number + 1
        self.log.emit(message)
        self.progress.emit(number, total, message)

    def _on_output(self, line: str) -> None:
        """转发归档工具输出到日志，并解析其中的百分比进度。"""
        self.log.emit(line)
        if self.plan.config.show_winrar_gui:
            return
        match = PERCENT_PATTERN.search(line)
        if match:
            self.progress.emit(
                self._current_layer - 1,
                self._total,
                f"第 {self._current_layer}/{self._total} 层压缩中：{match.group(1)}%",
            )


class CompressionTask(BackgroundTask):
    """执行一次已确定的压缩计划，持有本次用户取消事件。"""

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._cancel_event = threading.Event()

    def start(self, plan: CompressionPlan) -> None:
        """以独立取消事件启动计划。"""
        self._cancel_event = threading.Event()
        self._start(CompressionWorker(plan, self._cancel_event))

    def cancel(self) -> None:
        """请求 core 停止，并等待线程的完成通知。"""
        self._cancel_event.set()
