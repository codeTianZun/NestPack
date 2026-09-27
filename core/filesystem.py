"""共享文件操作：路径解析、原子文本写入与临时产物清理。"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from core.cancellation import Cancellation


def normalize_user_path(value: str, base_directory: Path | None = None) -> Path:
    """展开环境变量和用户目录，并按需相对配置目录解析路径。"""
    cleaned_value = value.strip().strip('"')
    expanded_value = os.path.expandvars(os.path.expanduser(cleaned_value))
    path = Path(expanded_value)
    if not path.is_absolute() and base_directory is not None:
        path = base_directory / path
    return path.resolve()


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """先写临时文件再替换，避免程序中断时留下半份内容。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary_path.write_text(content, encoding=encoding)
        temporary_path.replace(path)
    except BaseException:
        # 写入或替换失败时清理残留临时文件；清理错误不覆盖原始异常。
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def cleanup_path(path: Path) -> None:
    """清理生成的文件或目录，忽略清理错误以保留调用方的原始异常。"""
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    except OSError:
        pass


@contextmanager
def temporary_directory(parent: Path) -> Iterator[Path]:
    """创建本次调用独占的工作目录，并在离开作用域时清理。"""
    directory = Path(tempfile.mkdtemp(prefix=".", dir=parent))
    try:
        yield directory
    finally:
        cleanup_path(directory)


def copy_file(source: Path, target: Path, cancellation: Cancellation) -> None:
    """按块复制文件并保留元数据，复制过程响应停止请求。"""
    cancellation.check()
    with source.open("rb") as reader, target.open("wb") as writer:
        while chunk := reader.read(1024 * 1024):
            cancellation.check()
            writer.write(chunk)
    cancellation.check()
    shutil.copystat(source, target)


def link_or_copy_file(source: Path, target: Path, cancellation: Cancellation) -> None:
    """优先硬链接文件；文件系统不支持时按块复制。"""
    cancellation.check()
    try:
        os.link(source, target)
    except OSError:
        copy_file(source, target, cancellation)


def stage_source(source: Path, target: Path, cancellation: Cancellation) -> None:
    """暂存来源文件或目录，保留目录内的符号链接。"""
    cancellation.check()
    if source.is_dir():
        def copy_entry(src: str, dst: str) -> str:
            copy_file(Path(src), Path(dst), cancellation)
            return dst

        def visit_directory(_directory: str, _names: list[str]) -> tuple[str, ...]:
            cancellation.check()
            return ()

        shutil.copytree(
            source, target, symlinks=True, copy_function=copy_entry, ignore=visit_directory,
        )
    else:
        link_or_copy_file(source, target, cancellation)
