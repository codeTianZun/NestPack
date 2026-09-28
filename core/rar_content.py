"""RAR 文件头定位，支持原始归档与 Windows / Linux 自解压前缀。"""

from __future__ import annotations

import zlib
from pathlib import Path

RAR5_SIGNATURE = b"Rar!\x1a\x07\x01\x00"
RAR4_SIGNATURE = b"Rar!\x1a\x07\x00"
MAX_SFX_SIZE = 1 << 20


def _valid_header(data: bytes, offset: int, signature: bytes) -> bool:
    start = offset + len(signature)
    if signature == RAR4_SIGNATURE:
        header = data[start:start + 7]
        return len(header) == 7 and header[2] == 0x73
    cursor = start + 4
    size = 0
    shift = 0
    while cursor < len(data) and shift < 28:
        byte = data[cursor]
        cursor += 1
        size |= (byte & 0x7f) << shift
        if byte & 0x80 == 0:
            end = cursor + size
            return (
                size > 0 and end <= len(data) and data[cursor] in (1, 4)
                and zlib.crc32(data[start + 4:end])
                == int.from_bytes(data[start:start + 4], "little")
            )
        shift += 7
    return False


def rar_signature_offset(path: Path) -> int | None:
    """定位归档头；自解压只在可执行前缀内搜索并检查首个 RAR 块。"""
    try:
        with path.open("rb") as stream:
            prefix = stream.read(8)
            if prefix.startswith((RAR4_SIGNATURE, RAR5_SIGNATURE)):
                return 0
            if not prefix.startswith((b"MZ", b"\x7fELF")):
                return None
            data = prefix + stream.read(MAX_SFX_SIZE + (2 << 20))
    except OSError:
        return None
    candidates: list[int] = []
    for signature in (RAR5_SIGNATURE, RAR4_SIGNATURE):
        offset = data.find(signature, 1, MAX_SFX_SIZE + len(signature))
        while offset >= 0:
            if _valid_header(data, offset, signature):
                candidates.append(offset)
                break
            offset = data.find(signature, offset + 1, MAX_SFX_SIZE + len(signature))
    return min(candidates) if candidates else None
