"""压缩任务的输入作用域：来源暂存、别名与清理。"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from core.cancellation import Cancellation
from core.filesystem import stage_source, temporary_directory

from .models import TaskPlan
from .privacy import source_alias


@contextmanager
def task_source(
    task: TaskPlan, hide_source_name: bool, cancellation: Cancellation,
) -> Iterator[Path]:
    """提供就绪的首层输入，并在任务结束时清理准备过程中产生的文件。"""
    cancellation.check()
    if len(task.sources) == 1:
        source = task.sources[0]
        if hide_source_name:
            with source_alias(source, cancellation) as alias:
                yield alias
        else:
            yield source
        return

    with temporary_directory(task.output_directory) as staging:
        for source in task.sources:
            name = uuid.uuid4().hex[:12] if hide_source_name else source.name
            stage_source(source, staging / name, cancellation)
        cancellation.check()
        yield staging
