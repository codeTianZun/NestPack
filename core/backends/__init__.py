"""格式后端入口：按格式选择命令与分卷规则，按内容识别归档。"""

from __future__ import annotations

from pathlib import Path

from core.models import FORMAT_7Z, FORMAT_RAR, FORMAT_ZIP, ConfigError
from core.rar_content import rar_signature_offset

from .base import ArchiveBackend, describe_exit_code
from .rar import RarBackend
from .sevenzip import SevenZipBackend
from .zip import ZipBackend

__all__ = [
    "ArchiveBackend",
    "SUPPORTED_FORMATS",
    "describe_exit_code",
    "detect_archive_format",
    "get_backend",
    "iter_backends",
]

SUPPORTED_FORMATS = (FORMAT_RAR, FORMAT_7Z, FORMAT_ZIP)
_BACKENDS: dict[str, ArchiveBackend] = {
    FORMAT_RAR: RarBackend(),
    FORMAT_7Z: SevenZipBackend(),
    FORMAT_ZIP: ZipBackend(),
}


def get_backend(archive_format: str) -> ArchiveBackend:
    """按格式名取后端；不支持的格式抛 ConfigError。"""
    backend = _BACKENDS.get(archive_format)
    if backend is None:
        raise ConfigError(
            f"不支持的压缩格式 {archive_format!r}"
            f"（可选：{'、'.join(SUPPORTED_FORMATS)}）"
        )
    return backend


def iter_backends() -> tuple[ArchiveBackend, ...]:
    """返回全部后端，解包侧逐格式尝试识别时使用。"""
    return tuple(_BACKENDS.values())


def detect_archive_format(path: Path) -> str | None:
    """按文件头识别受支持的格式；无法识别返回 None。

    一次读取各后端用于识别的签名前缀（RAR / 7z 各 6 字节、
    ZIP 4 字节），在内存中比对，避免逐格式重复打开同一文件。
    """
    max_len = max(len(backend.signature) for backend in _BACKENDS.values())
    try:
        with path.open("rb") as stream:
            header = stream.read(max_len)
    except OSError:
        return None
    for archive_format, backend in _BACKENDS.items():
        if header.startswith(backend.signature):
            return archive_format
    if header.startswith((b"MZ", b"\x7fELF")) and rar_signature_offset(path) is not None:
        return FORMAT_RAR
    return None
