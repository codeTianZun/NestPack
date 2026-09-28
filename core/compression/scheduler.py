"""按压缩计划调度任务：合并暂存、独立来源并行与全局进度聚合。"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.cancellation import Cancellation, CancelledError
from core.models import COMPRESS_MODE_SEPARATE

from .layers import run_layer_stack
from .models import CompressionPlan, CompressionResult, TaskPlan, TaskResult
from .workspace import task_source

# separate 模式下来源互相独立；限制并发数以控制磁盘 I/O 争用。
MAX_PARALLEL_SOURCES = 3


class _ProgressCounter:
    """把“层开始/层完成”回调聚合成 progress_cb(number, total, message)。

    number 为全局已完成层数（单调不减），并行任务共用一个计数器时
    进度条不会来回跳。
    """

    def __init__(
        self,
        total: int,
        progress_cb: Callable[[int, int, str], None],
    ) -> None:
        self._total = total
        self._progress_cb = progress_cb
        self._lock = threading.Lock()
        self._completed = 0

    def started(self, message: str) -> None:
        with self._lock:
            self._progress_cb(self._completed, self._total, message)

    def completed(self, message: str) -> None:
        with self._lock:
            self._completed += 1
            self._progress_cb(self._completed, self._total, message)

    def attach(self, label: str = "") -> tuple[Callable[[str], None], Callable[[str], None]]:
        """返回 (on_layer_started, on_layer_completed) 回调对，可带来源前缀。"""
        return (
            lambda message: self.started(f"{label}{message}"),
            lambda message: self.completed(f"{label}{message}"),
        )


def run_compression(
    plan: CompressionPlan,
    progress_cb: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
    output_cb: Callable[[str], None] | None = None,
) -> CompressionResult:
    """执行计划；整次调用共用停止信号，按计划顺序返回已完成的任务。"""
    cancellation = Cancellation(cancel_event)
    cancellation.check()
    counter = _ProgressCounter(plan.total_layers, progress_cb) if progress_cb is not None else None
    try:
        if plan.config.compress_mode == COMPRESS_MODE_SEPARATE:
            tasks = _run_separate(plan, counter, cancellation, output_cb)
        else:
            tasks = (_run_task(plan, plan.tasks[0], counter, cancellation, output_cb),)
        return CompressionResult(plan=plan, tasks=tasks)
    except BaseException:
        cancellation.stop()
        raise


def _run_task(
    plan: CompressionPlan,
    task: TaskPlan,
    counter: _ProgressCounter | None,
    cancellation: Cancellation,
    output_cb: Callable[[str], None] | None,
) -> TaskResult:
    """在输入作用域内执行任务，所有退出路径都释放来源暂存文件。"""
    cancellation.check()
    config = plan.config
    task.output_directory.mkdir(parents=True, exist_ok=True)
    if counter is None:
        started = completed = None
    else:
        label = (
            f"[{task.sources[0].name}] "
            if config.compress_mode == COMPRESS_MODE_SEPARATE else ""
        )
        started, completed = counter.attach(label)
    with task_source(task, config.hide_source_name, cancellation) as source:
        return run_layer_stack(
            task, config, source, cancellation, output_cb,
            original_sources=plan.protected_inputs,
            on_layer_started=started, on_layer_completed=completed,
        )


def _run_separate(
    plan: CompressionPlan,
    counter: _ProgressCounter | None,
    cancellation: Cancellation,
    output_cb: Callable[[str], None] | None,
) -> tuple[TaskResult, ...]:
    """失败时停止同批任务，等待其清理完毕后传播首个真实错误。"""
    results: dict[int, TaskResult] = {}
    first_error: BaseException | None = None
    error_lock = threading.Lock()

    def run_task(task: TaskPlan) -> TaskResult:
        nonlocal first_error
        try:
            return _run_task(plan, task, counter, cancellation, output_cb)
        except BaseException as error:
            with error_lock:
                if first_error is None and not isinstance(error, CancelledError):
                    first_error = error
            cancellation.stop()
            raise

    worker_count = min(len(plan.tasks), MAX_PARALLEL_SOURCES)
    pool = ThreadPoolExecutor(max_workers=worker_count)
    try:
        futures = {pool.submit(run_task, task): index for index, task in enumerate(plan.tasks)}
        for future in as_completed(futures):
            try:
                results[futures[future]] = future.result()
            except Exception:
                # 工作线程已记录根因并广播停止，继续等待其余任务释放资源。
                continue
    except BaseException:
        # 主线程的 Ctrl+C 在等待线程池退出之前传递给运行中的任务。
        cancellation.stop()
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=True)

    if first_error is not None:
        raise first_error
    cancellation.check()
    return tuple(results[index] for index in range(len(plan.tasks)))
