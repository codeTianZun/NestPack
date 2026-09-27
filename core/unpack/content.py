"""识别一层解出的内容：嵌套压缩包、分卷套或最终载荷。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.backends import ArchiveBackend, detect_archive_format, get_backend

# 识别载荷时忽略填充文件，包括当前的 12 位十六进制 .dat 名称，
# 以及已有归档中 stack_pad_ 加 8 位十六进制名的 .bin 文件。
PADDING_NAME_PATTERN = re.compile(
    r"^(?:stack_pad_[0-9a-f]{8}\.bin|[0-9a-f]{12}\.dat)$", re.IGNORECASE
)


@dataclass(frozen=True)
class ExtractedContent:
    """一层解压结果的分类：中间层（继续解）或最终载荷（停止）。"""

    is_intermediate: bool
    volumes: tuple[Path, ...]
    # 中间层为该层压缩包的格式（"rar" / "7z" / "zip"）；载荷为空串。
    archive_format: str = ""


def classify_extracted(directory: Path) -> ExtractedContent:
    """判断一层解出的内容是中间压缩层还是最终载荷。

    规则：忽略随机填充文件后，若剩余条目全部是文件且都带同一种
    受支持格式的文件头，并构成单个压缩包或从 1 开始连续编号的一套
    分卷，则视为中间层；否则视为载荷。载荷本身恰好只有一个压缩包
    文件时无法区分，会被当作中间层继续解开，此时可用 layer_limit
    强制指定层数。
    """
    entries = [
        entry
        for entry in directory.iterdir()
        if not PADDING_NAME_PATTERN.fullmatch(entry.name)
    ]
    files = [entry for entry in entries if entry.is_file()]
    if not files or len(files) != len(entries):
        return ExtractedContent(False, ())
    formats = {detect_archive_format(path) for path in files}
    if len(formats) != 1 or None in formats:
        return ExtractedContent(False, ())
    archive_format = next(iter(formats))
    if archive_format is None:
        return ExtractedContent(False, ())
    backend = get_backend(archive_format)
    volumes = _ordered_volume_set(files, backend)
    return ExtractedContent(volumes is not None, volumes or (), archive_format)


def _ordered_volume_set(
    files: list[Path], backend: ArchiveBackend
) -> tuple[Path, ...] | None:
    """把单个压缩包或连续分卷整理成有序列表；非法分卷组返回 None。"""
    if len(files) == 1:
        return (files[0],)
    matched: list[tuple[re.Match[str], Path]] = []
    for path in files:
        match = backend.volume_name_pattern.fullmatch(path.name)
        if match is None:
            return None
        matched.append((match, path))
    bases = {match.group(1).casefold() for match, _path in matched}
    if len(bases) != 1:
        return None
    numbered = sorted(
        (int(match.group(2)), path) for match, path in matched
    )
    numbers = [number for number, _path in numbered]
    if numbers != list(range(1, len(files) + 1)):
        return None
    return tuple(path for _number, path in numbered)
