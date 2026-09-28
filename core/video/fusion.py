"""视频融合与原归档提取：可取消复制、完整性记录与原子发布。"""

from __future__ import annotations

import hashlib
import os
import struct
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from core.backends import detect_archive_format, get_backend
from core.cancellation import Cancellation
from core.filesystem import temporary_directory
from core.models import ConfigError

from .mp4 import box_header, copy_range, iter_boxes, read_exact, read_movie, write_movie
from .zip_directory import read_directory, write_directory

FUSION_UUID = bytes.fromhex("7206b5a845094c0bba51d746b3ac35c1")
RECORD = struct.Struct(">BB6xQQ32s")
FORMATS = ("rar", "7z", "zip")
RECORD_SIZE = 8 + len(FUSION_UUID) + RECORD.size


@dataclass(frozen=True)
class VideoArchive:
    """融合文件中原始归档的格式、字节范围与 SHA256。"""

    format: str
    offset: int
    size: int
    sha256: bytes


def inspect_video_archive(
    path: Path, cancellation: Cancellation | None = None,
) -> VideoArchive | None:
    """识别 NestPack 融合记录，按 MP4 块边界定位归档。"""
    cancellation = cancellation or Cancellation()
    with path.open("rb") as stream:
        head = stream.read(8)
        if len(head) != 8 or head[4:] != b"ftyp":
            return None
        size = path.stat().st_size
        found: VideoArchive | None = None
        payloads: list[tuple[int, int]] = []
        for box in iter_boxes(stream, 0, size, cancellation):
            if box.kind == b"free":
                payloads.append((box.body, box.end - box.body))
            if box.kind != b"uuid" or box.end - box.body < len(FUSION_UUID):
                continue
            stream.seek(box.body)
            if read_exact(stream, len(FUSION_UUID)) != FUSION_UUID:
                continue
            if found is not None or box.end - box.body != len(FUSION_UUID) + RECORD.size:
                raise ConfigError("视频融合记录重复或长度无效。")
            version, kind, offset, length, digest = RECORD.unpack(read_exact(stream, RECORD.size))
            if version != 1 or kind >= len(FORMATS) or not length:
                raise ConfigError("视频融合记录的版本、格式或长度无效。")
            found = VideoArchive(FORMATS[kind], offset, length, digest)
        if found is not None:
            if (found.offset, found.size) not in payloads:
                raise ConfigError("视频融合记录与归档数据块不匹配。")
            stream.seek(found.offset)
            if not read_exact(stream, min(found.size, 8)).startswith(
                get_backend(found.format).signature
            ):
                raise ConfigError("视频中的归档签名与融合记录不匹配。")
        return found


def validate_video(path: Path, cancellation: Cancellation | None = None) -> None:
    """校验载体结构，规划和独立融合共用同一入口。"""
    read_movie(path, cancellation)
    if inspect_video_archive(path, cancellation) is not None:
        raise ConfigError("所选视频已经包含融合归档，请选择原始载体视频。")


def _archive_format(path: Path) -> str:
    archive_format = detect_archive_format(path)
    if archive_format is None:
        raise ConfigError(f"请选择完整的 RAR、7z 或 ZIP 单文件归档：{path}")
    backend = get_backend(archive_format)
    if (backend.volume_name_pattern.fullmatch(path.name)
            or backend.parse_disguised_volume(path.name)):
        raise ConfigError("视频融合使用完整的单文件归档，请先将分卷套打包为一个外层归档。")
    if archive_format == "7z":
        with path.open("rb") as stream:
            header = read_exact(stream, 32)
        offset, length = struct.unpack("<QQ", header[12:28])
        if offset + length + 32 > path.stat().st_size:
            raise ConfigError("7z 归档不完整，请选择完整的单文件归档。")
    return archive_format


def write_fused_video(
    video: Path, archive: Path, target: Path, cancellation: Cancellation,
    output_cb: Callable[[str], None] | None = None,
) -> None:
    """写入调用方持有的临时文件，归档字节原样保留。"""
    archive_format = _archive_format(archive)
    boxes = read_movie(video, cancellation)
    if inspect_video_archive(video, cancellation) is not None:
        raise ConfigError("所选视频已经包含融合归档，请选择原始载体视频。")
    archive_size = archive.stat().st_size
    header = box_header(b"free", archive_size)
    insertion_size = RECORD_SIZE + len(header) + archive_size
    if boxes[0].rewritten_size + RECORD_SIZE + len(header) >= 1 << 20:
        raise ConfigError("MP4 格式标识过大，超出解压工具的归档头识别范围。")
    if output_cb is not None:
        output_cb(f"正在融合视频：{video.name}（保留原音视频与归档内容）")
    digest = hashlib.sha256()
    record_position = 0
    archive_offset = 0
    with video.open("rb") as reader, archive.open("rb") as payload, target.open("w+b") as writer:
        directory = read_directory(payload, archive_size) if archive_format == "zip" else None
        def insert_archive() -> None:
            nonlocal record_position, archive_offset
            writer.write(box_header(b"uuid", len(FUSION_UUID) + RECORD.size))
            writer.write(FUSION_UUID)
            record_position = writer.tell()
            writer.write(bytes(RECORD.size))
            writer.write(header)
            archive_offset = writer.tell()
            copy_range(payload, writer, 0, archive_size, cancellation, digest.update)

        write_movie(reader, writer, boxes, cancellation,
                    insert_size=insertion_size, insert=insert_archive)
        if directory is not None:
            write_directory(payload, writer, directory, archive_offset, cancellation)
        cancellation.check()
        writer.seek(record_position)
        writer.write(RECORD.pack(1, FORMATS.index(archive_format), archive_offset,
                                 archive_size, digest.digest()))
    if output_cb is not None:
        output_cb("视频融合完成。")


def _check_destination(destination: Path, inputs: tuple[Path, ...], overwrite: bool) -> None:
    for source in inputs:
        if destination == source or (
            destination.exists() and source.exists() and destination.samefile(source)
        ):
            raise ConfigError(f"输出不能覆盖输入文件：{destination}")
    if destination.exists() and (not overwrite or not destination.is_file()):
        raise ConfigError(f"输出文件已存在或目标不是文件：{destination}")


def fuse_archive(
    video: Path, archive: Path, destination: Path, *, overwrite_existing: bool = False,
    cancellation: Cancellation | None = None, output_cb: Callable[[str], None] | None = None,
) -> Path:
    """独立融合已有归档，成功后原子发布 MP4。"""
    cancellation = cancellation or Cancellation()
    video, archive, destination = video.resolve(), archive.resolve(), destination.resolve()
    if destination.suffix.lower() != ".mp4":
        raise ConfigError("视频融合输出文件应使用 .mp4 扩展名。")
    _archive_format(archive)
    validate_video(video, cancellation)
    _check_destination(destination, (video, archive), overwrite_existing)
    cancellation.check()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with temporary_directory(destination.parent) as work:
        temporary = work / "fused.mp4"
        write_fused_video(video, archive, temporary, cancellation, output_cb)
        cancellation.check()
        _check_destination(destination, (video, archive), overwrite_existing)
        os.replace(temporary, destination)
    return destination


def extract_video_archive(
    video: Path, destination: Path, *, overwrite_existing: bool = False,
    cancellation: Cancellation | None = None, output_cb: Callable[[str], None] | None = None,
) -> Path:
    """按记录提取原始归档并校验 SHA256，成功后原子发布。"""
    cancellation = cancellation or Cancellation()
    video, destination = video.resolve(), destination.resolve()
    record = inspect_video_archive(video, cancellation)
    if record is None:
        raise ConfigError("所选文件不是 NestPack 生成的视频融合文件。")
    _check_destination(destination, (video,), overwrite_existing)
    cancellation.check()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with temporary_directory(destination.parent) as work:
        temporary = work / "archive"
        digest = hashlib.sha256()
        if output_cb is not None:
            output_cb("正在提取视频中的原始归档并校验完整性…")
        with video.open("rb") as reader, temporary.open("wb") as writer:
            copy_range(reader, writer, record.offset, record.size, cancellation, digest.update)
        if digest.digest() != record.sha256:
            raise ConfigError("视频中的归档完整性校验失败，文件可能已被修改或损坏。")
        cancellation.check()
        _check_destination(destination, (video,), overwrite_existing)
        os.replace(temporary, destination)
    return destination
