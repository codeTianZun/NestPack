"""在 MP4 末端发布 ZIP 中央目录，兼容大文件与 ZIP64 定位。"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import BinaryIO

from core.cancellation import Cancellation
from core.models import ConfigError

from .mp4 import box_header, copy_range, read_exact

END = struct.Struct("<4s4H2IH")
ZIP64_END = struct.Struct("<4sQ2H2I4Q")
LOCATOR = struct.Struct("<4sIQI")


@dataclass(frozen=True)
class ZipDirectory:
    """原 ZIP 的目录范围与注释，载荷与原归档均保持原样。"""

    offset: int
    size: int
    entries: int
    comment: bytes


def read_directory(stream: BinaryIO, size: int) -> ZipDirectory:
    """读取 ZIP/ZIP64 末端记录，并校验单文件目录的范围。"""
    start = max(0, size - 65535 - END.size)
    stream.seek(start)
    tail = read_exact(stream, size - start)
    position = tail.rfind(b"PK\x05\x06")
    while position >= 0:
        if position + END.size <= len(tail):
            fields = END.unpack_from(tail, position)
            if position + END.size + fields[-1] == len(tail):
                break
        position = tail.rfind(b"PK\x05\x06", 0, position)
    else:
        raise ConfigError("ZIP 末端目录不完整，请选择完整的单文件归档。")
    _, disk, directory_disk, disk_entries, entries, directory_size, offset, _ = fields
    end_position = start + position
    directory_end = end_position
    if disk or directory_disk or disk_entries != entries:
        raise ConfigError("视频融合使用单文件 ZIP，请先将分卷套打包为一个外层归档。")
    if end_position >= LOCATOR.size:
        stream.seek(end_position - LOCATOR.size)
        locator = read_exact(stream, LOCATOR.size)
        if locator.startswith(b"PK\x06\x07"):
            _, zip64_disk, zip64_offset, disk_count = LOCATOR.unpack(locator)
            if zip64_disk or disk_count != 1 or zip64_offset + ZIP64_END.size > end_position:
                raise ConfigError("ZIP64 目录位置或分卷信息无效。")
            stream.seek(zip64_offset)
            record = ZIP64_END.unpack(read_exact(stream, ZIP64_END.size))
            signature, length, _, _, disk, directory_disk, disk_entries, entries, \
                directory_size, offset = record
            if (signature != b"PK\x06\x06" or length < 44 or disk or directory_disk
                    or disk_entries != entries
                    or zip64_offset + 12 + length != end_position - LOCATOR.size):
                raise ConfigError("ZIP64 目录记录无效。")
            directory_end = zip64_offset
    if offset + directory_size > directory_end:
        raise ConfigError("ZIP 中央目录超出原归档边界。")
    if entries:
        stream.seek(offset)
        if read_exact(stream, 4) != b"PK\x01\x02":
            raise ConfigError("ZIP 中央目录不可读取，请使用标准 ZIP 或 AES ZIP 归档。")
    return ZipDirectory(offset, directory_size, entries, tail[position + END.size:])


def write_directory(
    reader: BinaryIO, writer: BinaryIO, directory: ZipDirectory,
    archive_offset: int, cancellation: Cancellation,
) -> None:
    """复制中央目录并以 ZIP64 末端记录指向前部的原始文件数据。"""
    body_size = directory.size + ZIP64_END.size + LOCATOR.size + END.size + len(directory.comment)
    writer.write(box_header(b"free", body_size))
    offset = writer.tell() - archive_offset
    copy_range(reader, writer, directory.offset, directory.size, cancellation)
    zip64_offset = writer.tell() - archive_offset
    writer.write(ZIP64_END.pack(
        b"PK\x06\x06", 44, 45, 45, 0, 0,
        directory.entries, directory.entries, directory.size, offset,
    ))
    writer.write(LOCATOR.pack(b"PK\x06\x07", 0, zip64_offset, 1))
    writer.write(END.pack(b"PK\x05\x06", 0, 0, 0xFFFF, 0xFFFF,
                          0xFFFFFFFF, 0xFFFFFFFF, len(directory.comment)))
    writer.write(directory.comment)
