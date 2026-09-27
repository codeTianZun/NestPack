"""解包工作目录的生命周期：成功后清理，失败或取消时保留已解内容。"""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from core.cancellation import Cancellation
from core.filesystem import cleanup_path

WORK_DIRECTORY_NAME = ".nestpack_unpack_tmp"


@contextmanager
def unpack_workspace(
    output_dir: Path,
    cancellation: Cancellation,
    output_cb: Callable[[str], None] | None,
) -> Iterator[Path]:
    """准备本次解包的工作目录，重跑时清空上次现场。"""
    cancellation.check()
    output_dir.mkdir(parents=True, exist_ok=True)
    work = output_dir / WORK_DIRECTORY_NAME
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    try:
        yield work
    except BaseException as error:
        if output_cb is not None:
            try:
                output_cb(f"解包中断（{error}），已解出的内容保留在：{work}")
            except Exception:
                # 提示回调失败时仍传播导致解包中断的原始异常。
                pass
        raise
    else:
        cleanup_path(work)
