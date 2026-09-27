"""执行期间的协作式停止：合并用户取消与内部失败信号。"""

from __future__ import annotations

import threading


class CancelledError(RuntimeError):
    """当前执行收到停止请求。"""


class Cancellation:
    """一次执行共用的停止信号，用户事件由调用方持有。"""

    def __init__(self, user_event: threading.Event | None = None) -> None:
        self._user_event = user_event
        self._stopped = threading.Event()

    def stop(self) -> None:
        """请求本次执行的所有任务停止。"""
        self._stopped.set()

    def check(self) -> None:
        """在可中断阶段检查停止请求。"""
        if self._stopped.is_set() or (
            self._user_event is not None and self._user_event.is_set()
        ):
            raise CancelledError("操作已取消")
