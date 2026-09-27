"""可压缩性探测：为 auto 压缩级别选择仅存储或最高压缩。

输入已是压缩数据时，继续高强度压缩通常收益有限。本模块用 zlib
试压样本，节省低于 5% 时选择仅存储。
"""

from __future__ import annotations

import heapq
import zlib
from collections.abc import Iterator
from pathlib import Path

from core.cancellation import Cancellation
from core.models import LayerConfig

# 超过该大小的文件只取首/中/尾三段样本，样本总量约 64KB。
WHOLE_FILE_LIMIT = 256 * 1024
SAMPLE_LIMIT = 64 * 1024
# 试压后大小低于原始 95% 才认为可压缩。
SAVINGS_THRESHOLD = 0.95
# 文件夹取最大的若干文件作样本，避免“大量文本 + 一个视频”被单个
# 最大的不可压缩文件代表而误判为整体不可压缩。
FOLDER_SAMPLE_FILES = 3


def _collect_sample(path: Path, cancellation: Cancellation) -> bytes:
    """收集用于试压的样本：小文件整读，大文件取首/中/尾三段。"""
    cancellation.check()
    size = path.stat().st_size
    if size <= WHOLE_FILE_LIMIT:
        return path.read_bytes()

    chunk_size = SAMPLE_LIMIT // 3
    result = bytearray()
    for offset in (0, (size - chunk_size) // 2, size - chunk_size):
        cancellation.check()
        with path.open("rb") as stream:
            stream.seek(offset)
            result += stream.read(chunk_size)
    return bytes(result)


def _iter_file_sizes(directory: Path, cancellation: Cancellation) -> Iterator[tuple[int, Path]]:
    """遍历目录中文件及其大小，stat 失败的项跳过（供 heapq.nlargest 消费）。"""
    for candidate in directory.rglob("*"):
        cancellation.check()
        if candidate.is_file():
            try:
                size = candidate.stat().st_size
            except OSError:
                continue
            yield (size, candidate)


def probe(source: Path, cancellation: Cancellation) -> int:
    """探测压缩级别：可压缩返回 5，不可压缩返回 0。

    文件夹取其中最大的几个文件，把各自样本合并后整体试压；空文件夹
    没有样本，按可压缩处理。用 heapq.nlargest 取前若干大文件，避免
    对全部条目做完整排序。
    """
    cancellation.check()
    samples: list[bytes] = []
    if source.is_dir():
        largest = heapq.nlargest(FOLDER_SAMPLE_FILES, _iter_file_sizes(source, cancellation))
        if not largest:
            return 5
        for _size, candidate in largest:
            samples.append(_collect_sample(candidate, cancellation))
    else:
        samples.append(_collect_sample(source, cancellation))

    sample = b"".join(samples)
    compressed_size = len(zlib.compress(sample, level=1))
    if compressed_size >= len(sample) * SAVINGS_THRESHOLD:
        return 0
    return 5


def resolve_compression_level(
    layer: LayerConfig,
    source: Path,
    is_first_layer: bool,
    cancellation: Cancellation,
) -> int:
    """显式级别直接使用；auto 对首层采样，后续层选择仅存储。"""
    if isinstance(layer.compression_level, int):
        return layer.compression_level
    if is_first_layer:
        return probe(source, cancellation)
    # auto 模式下，第 2 层起输入为上一层归档，使用仅存储级别。
    return 0
