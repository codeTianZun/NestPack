"""来源别名、随机填充和时间戳；临时输入由各自作用域清理。"""

from __future__ import annotations

import os
import random
import time
import uuid
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from core.cancellation import Cancellation
from core.filesystem import cleanup_path, stage_source

TWO_YEARS_SECONDS = 2 * 365 * 24 * 3600
PADDING_MIN_BYTES = 16 * 1024
PADDING_MAX_BYTES = 1024 * 1024


@contextmanager
def source_alias(source: Path, cancellation: Cancellation) -> Iterator[Path]:
    """同目录创建随机别名；复制中断或使用完毕时清理别名。"""
    alias = source.parent / uuid.uuid4().hex[:12]
    try:
        try:
            stage_source(source, alias, cancellation)
        except OSError as error:
            raise RuntimeError(f"无法创建脱敏别名：{error}") from error
        yield alias
    finally:
        cleanup_path(alias)


@contextmanager
def padding_file(directory: Path, cancellation: Cancellation) -> Iterator[Path]:
    """创建当前层的随机填充文件，写入失败或层执行结束时清理。"""
    cancellation.check()
    padding = directory / f"{uuid.uuid4().hex[:12]}.dat"
    try:
        size = random.randint(PADDING_MIN_BYTES, PADDING_MAX_BYTES)
        padding.write_bytes(os.urandom(size))
        yield padding
    finally:
        cleanup_path(padding)


def randomize_timestamps(products: Iterable[Path], cancellation: Cancellation) -> None:
    """把即将交付的产物修改时间改为最近两年内的随机时刻。"""
    for product in products:
        cancellation.check()
        moment = time.time() - random.uniform(0, TWO_YEARS_SECONDS)
        os.utime(product, (moment, moment))
