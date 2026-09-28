"""MP4 数据块读取与媒体偏移重定位，按块复制音视频数据。"""

from __future__ import annotations

import struct
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from core.cancellation import Cancellation
from core.models import ConfigError

CONTAINERS = {
    b"moov", b"trak", b"mdia", b"minf", b"stbl", b"dinf", b"moof", b"traf", b"mfra",
}


@dataclass(frozen=True)
class Box:
    """一个有边界的数据块，容器仅保存子块索引。"""

    start: int
    size: int
    header_size: int
    kind: bytes
    children: tuple[Box, ...] = ()
    count: int = 0
    version: int = 0

    @property
    def body(self) -> int:
        return self.start + self.header_size

    @property
    def end(self) -> int:
        return self.start + self.size

    @property
    def rewritten_size(self) -> int:
        body_size = self.size - self.header_size
        if self.kind == b"stco":
            body_size += self.count * 4
        elif self.kind == b"sidx" and self.version == 0:
            body_size += 8
        elif self.kind == b"tfra" and self.version == 0:
            body_size += self.count * 8
        elif self.kind in CONTAINERS:
            body_size = sum(child.rewritten_size for child in self.children)
        return body_size + (16 if self.header_size == 16 or body_size + 8 > 0xFFFFFFFF else 8)


def read_exact(stream: BinaryIO, size: int) -> bytes:
    """读取结构字段，截断文件给出明确错误。"""
    data = stream.read(size)
    if len(data) != size:
        raise ConfigError("MP4 或归档数据不完整，文件可能被截断。")
    return data


def box_header(kind: bytes, body_size: int, *, extended: bool = False) -> bytes:
    """生成支持大于 4 GiB 内容的 MP4 数据块头。"""
    if body_size + 8 <= 0xFFFFFFFF and not extended:
        return struct.pack(">I4s", body_size + 8, kind)
    return struct.pack(">I4sQ", 1, kind, body_size + 16)


def iter_boxes(
    stream: BinaryIO, start: int, end: int, cancellation: Cancellation,
) -> Iterator[Box]:
    """按块长度跳过载荷，所有位置均受所属容器边界约束。"""
    while start < end:
        cancellation.check()
        if end - start < 8:
            raise ConfigError("MP4 数据块头不完整。")
        stream.seek(start)
        size, kind = struct.unpack(">I4s", read_exact(stream, 8))
        header_size = 8
        if size == 1:
            if end - start < 16:
                raise ConfigError("MP4 扩展长度字段不完整。")
            size = struct.unpack(">Q", read_exact(stream, 8))[0]
            header_size = 16
        elif size == 0:
            size = end - start
        if size < header_size or size > end - start:
            raise ConfigError("MP4 数据块长度超出文件或容器边界。")
        yield Box(start, size, header_size, kind)
        start += size


def _index_box(stream: BinaryIO, box: Box, cancellation: Cancellation, depth: int = 0) -> Box:
    if depth > 16:
        raise ConfigError("MP4 媒体容器嵌套层数异常。")
    children: tuple[Box, ...] = ()
    count = version = 0
    if box.kind in CONTAINERS:
        children = tuple(
            _index_box(stream, child, cancellation, depth + 1)
            for child in iter_boxes(stream, box.body, box.end, cancellation)
        )
    elif box.kind in (b"stco", b"co64", b"sidx", b"tfra", b"tfhd"):
        stream.seek(box.body)
        minimum = {b"stco": 8, b"co64": 8, b"sidx": 24, b"tfra": 16, b"tfhd": 8}
        if box.size - box.header_size < minimum[box.kind]:
            raise ConfigError("MP4 媒体偏移表不完整。")
        fields = read_exact(stream, minimum[box.kind])
        version = fields[0]
        if box.kind in (b"stco", b"co64"):
            count = int.from_bytes(fields[4:8], "big")
            width = 4 if box.kind == b"stco" else 8
            if box.size - box.header_size != 8 + count * width or version != 0:
                raise ConfigError("MP4 媒体偏移表长度或版本无效。")
        elif box.kind in (b"sidx", b"tfra"):
            if version not in (0, 1):
                raise ConfigError("MP4 分片索引版本无效。")
            if box.kind == b"tfra":
                count = int.from_bytes(fields[12:16], "big")
                lengths = int.from_bytes(fields[8:12], "big")
                width = (16 if version else 8) + sum(
                    ((lengths >> shift) & 3) + 1 for shift in (4, 2, 0)
                )
                if box.size - box.header_size != 16 + count * width:
                    raise ConfigError("MP4 分片随机访问索引长度无效。")
            elif box.size - box.header_size < (32 if version else 24):
                raise ConfigError("MP4 分片索引不完整。")
        elif int.from_bytes(fields[:4], "big") & 1 and box.size - box.header_size < 16:
            raise ConfigError("MP4 分片基础偏移字段不完整。")
    elif box.kind == b"cmov":
        raise ConfigError("载体使用压缩的 QuickTime 索引，请先另存为标准 MP4。")
    elif box.kind == b"saio":
        raise ConfigError("载体含加密媒体的辅助偏移表，请使用可独立播放的普通 MP4。")
    elif box.kind == b"dref":
        if box.end - box.body < 8:
            raise ConfigError("MP4 媒体引用表不完整。")
        for entry in iter_boxes(stream, box.body + 8, box.end, cancellation):
            if entry.end - entry.body < 4:
                raise ConfigError("MP4 媒体引用不完整。")
            stream.seek(entry.body)
            flags = int.from_bytes(read_exact(stream, 4), "big")
            if not flags & 1:
                raise ConfigError("MP4 引用了外部媒体文件，请选择音视频数据完整的独立 MP4。")
    elif box.kind == b"mfro" and box.end - box.body != 8:
        raise ConfigError("MP4 分片随机访问尾部长度无效。")
    return Box(box.start, box.size, box.header_size, box.kind, children, count, version)


def read_movie(path: Path, cancellation: Cancellation | None = None) -> tuple[Box, ...]:
    """读取独立 MP4 的媒体结构，保留音视频编码和数据。"""
    cancellation = cancellation or Cancellation()
    if not path.is_file():
        raise ConfigError(f"载体视频不存在：{path}")
    with path.open("rb") as stream:
        boxes = tuple(iter_boxes(stream, 0, path.stat().st_size, cancellation))
        if not boxes or boxes[0].kind != b"ftyp" or boxes[0].size < 16:
            raise ConfigError(f"载体必须是包含 ftyp 标识的 MP4 文件：{path}")
        if not any(box.kind == b"moov" for box in boxes) or not any(
            box.kind == b"mdat" for box in boxes
        ):
            raise ConfigError("MP4 必须同时包含媒体索引与音视频数据。")
        return tuple(_index_box(stream, box, cancellation) for box in boxes)


def copy_range(
    reader: BinaryIO, writer: BinaryIO, start: int, size: int,
    cancellation: Cancellation, on_chunk: Callable[[bytes], object] | None = None,
) -> None:
    """复制指定范围，内存占用不随载体或压缩包体积增长。"""
    reader.seek(start)
    while size:
        cancellation.check()
        data = read_exact(reader, min(size, 1024 * 1024))
        writer.write(data)
        if on_chunk is not None:
            on_chunk(data)
        size -= len(data)


def write_movie(
    reader: BinaryIO, writer: BinaryIO, boxes: tuple[Box, ...],
    cancellation: Cancellation, *, insert_size: int = 0,
    insert: Callable[[], None] | None = None,
) -> None:
    """在格式标识后插入数据，并重写绝对媒体偏移及分片索引。"""
    destinations: dict[int, int] = {}
    position = 0
    for index, box in enumerate(boxes):
        destinations[box.start] = position
        position += box.rewritten_size
        if index == 0:
            position += insert_size

    def relocate(offset: int) -> int:
        for box in boxes:
            if box.start <= offset < box.end:
                return destinations[box.start] + offset - box.start
        if offset == boxes[-1].end:
            return position
        raise ConfigError("MP4 媒体偏移超出原视频边界。")

    def write_box(box: Box) -> None:
        cancellation.check()
        kind = b"co64" if box.kind == b"stco" else box.kind
        size = box.rewritten_size
        header_size = 16 if box.header_size == 16 or size > 0xFFFFFFFF else 8
        beginning = writer.tell()
        writer.write(box_header(kind, size - header_size, extended=header_size == 16))
        if box.kind in CONTAINERS:
            for child in box.children:
                write_box(child)
        elif box.kind in (b"stco", b"co64"):
            reader.seek(box.body)
            writer.write(read_exact(reader, 8))
            width = 4 if box.kind == b"stco" else 8
            for _ in range(box.count):
                cancellation.check()
                offset = int.from_bytes(read_exact(reader, width), "big")
                writer.write(struct.pack(">Q", relocate(offset)))
        elif box.kind == b"tfhd":
            reader.seek(box.body)
            fields = read_exact(reader, 8)
            writer.write(fields)
            consumed = 8
            if int.from_bytes(fields[:4], "big") & 1:
                offset = int.from_bytes(read_exact(reader, 8), "big")
                writer.write(struct.pack(">Q", relocate(offset)))
                consumed += 8
            copy_range(reader, writer, box.body + consumed, box.end - box.body - consumed,
                       cancellation)
        elif box.kind == b"sidx":
            reader.seek(box.body)
            fields = read_exact(reader, 12)
            writer.write(b"\x01" + fields[1:])
            width = 8 if box.version else 4
            timestamp = int.from_bytes(read_exact(reader, width), "big")
            offset = int.from_bytes(read_exact(reader, width), "big")
            first_offset = relocate(box.end + offset) - beginning - size
            if first_offset < 0:
                raise ConfigError("MP4 分片索引指向其自身之前。")
            writer.write(struct.pack(">QQ", timestamp, first_offset))
            consumed = 12 + width * 2
            copy_range(reader, writer, box.body + consumed, box.end - box.body - consumed,
                       cancellation)
        elif box.kind == b"tfra":
            reader.seek(box.body)
            fields = read_exact(reader, 16)
            writer.write(b"\x01" + fields[1:])
            lengths = int.from_bytes(fields[8:12], "big")
            suffix_size = sum(((lengths >> shift) & 3) + 1 for shift in (4, 2, 0))
            width = 8 if box.version else 4
            for _ in range(box.count):
                cancellation.check()
                timestamp = int.from_bytes(read_exact(reader, width), "big")
                offset = int.from_bytes(read_exact(reader, width), "big")
                writer.write(struct.pack(">QQ", timestamp, relocate(offset)))
                writer.write(read_exact(reader, suffix_size))
        elif box.kind == b"mfro":
            reader.seek(box.body)
            writer.write(read_exact(reader, 4))
            parent = next(
                top for top in boxes
                if top.kind == b"mfra" and top.start < box.start < top.end
            )
            if parent.rewritten_size > 0xFFFFFFFF:
                raise ConfigError("MP4 分片随机访问索引超出可表示大小。")
            writer.write(struct.pack(">I", parent.rewritten_size))
        else:
            copy_range(reader, writer, box.body, box.end - box.body, cancellation)

    for index, box in enumerate(boxes):
        write_box(box)
        if index == 0 and insert is not None:
            insert()
