"""后台任务的信号转发、运行状态与 QThread 资源回收。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

from core.cancellation import CancelledError


class TaskWorker(QObject):
    """在线程中执行任务，将结果、错误和完成通知交回任务对象。"""

    log = Signal(str)
    progress = Signal(int, int, str)
    completed = Signal(object)
    cancelled = Signal()
    failed = Signal(str)
    finished = Signal()

    def __init__(self, failure_label: str) -> None:
        super().__init__()
        self._failure_label = failure_label

    def execute(self) -> object:
        """由具体任务实现阻塞操作并返回结果。"""
        raise NotImplementedError

    @Slot()
    def run(self) -> None:
        try:
            self.completed.emit(self.execute())
        except CancelledError:
            self.log.emit("已取消。")
            self.cancelled.emit()
        except Exception as error:
            self.log.emit(f"{self._failure_label}：{error}")
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


class BackgroundTask(QObject):
    """在主线程持有 worker 与线程，直到线程退出才释放引用并恢复空闲。"""

    log = Signal(str)
    progress = Signal(int, int, str)
    completed = Signal(object)
    cancelled = Signal()
    failed = Signal(str)
    active_changed = Signal(bool)
    finished = Signal()

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: TaskWorker | None = None

    @property
    def active(self) -> bool:
        """线程正在运行或尚未完成回收。"""
        return self._thread is not None

    def _start(self, worker: TaskWorker) -> None:
        if self.active:
            raise RuntimeError("当前后台任务尚未结束")
        thread = QThread(self)
        self._thread = thread
        self._worker = worker
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self.log)
        worker.progress.connect(self.progress)
        worker.completed.connect(self.completed)
        worker.cancelled.connect(self.cancelled)
        worker.failed.connect(self.failed)
        worker.finished.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._finish)
        thread.finished.connect(thread.deleteLater)
        self.active_changed.emit(True)
        thread.start()

    @Slot()
    def _finish(self) -> None:
        self._worker = None
        self._thread = None
        self.active_changed.emit(False)
        self.finished.emit()
