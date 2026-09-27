"""复用 7-Zip 工具的 ZIP 格式后端。"""

from __future__ import annotations

import re
from pathlib import Path

from core.models import FORMAT_ZIP

from .base import DISGUISED_VOLUME_EXTENSION_CHARS
from .sevenzip import SEVENZIP_LEVEL_MAP, SevenZipBackend

ZIP_SIGNATURE = b"PK\x03\x04"


class ZipBackend(SevenZipBackend):
    """7-Zip 命令行的 .zip 后端；分卷命名与解包规则同 7z（foo.zip.001）。

    创建 ZIP 需要支持 -tzip 的 7z 家族工具（7z / 7za / 7zz），
    精简版 7zr 只认 .7z 格式。ZIP 不支持加密压缩包头（没有等价
    -mhe 的开关），文件名始终明文；密码只保护内容，且用
    -mem=AES256 代替默认的传统 ZipCrypto（后者强度过弱）。
    """

    format_name = FORMAT_ZIP
    archive_extension = ".zip"
    signature = ZIP_SIGNATURE
    volume_name_pattern = re.compile(r"^(.*)\.zip\.(\d+)$", re.IGNORECASE)

    def build_add_command(
        self,
        tool: Path,
        source: Path,
        destination: Path,
        *,
        compression_level: int,
        background: bool = False,
        password: str = "",
        recovery_percent: int | None = None,
        volume_size: str | None = None,
        extra_inputs: tuple[str, ...] = (),
    ) -> list[str]:
        command = [
            str(tool),
            "a",
            "-tzip",
            f"-mx{SEVENZIP_LEVEL_MAP[compression_level]}",
            "-y",
        ]
        if password:
            command.extend([f"-p{password}", "-mem=AES256"])
        if volume_size:
            command.append(f"-v{volume_size}")
        command.extend([str(destination), "--", source.name, *extra_inputs])
        return command

    def standard_volume_name(self, base: str, number: int) -> str:
        return f"{base}.zip.{number:03d}"

    def parse_disguised_volume(self, name: str) -> tuple[str, int, str] | None:
        match = re.fullmatch(
            rf"^(.*)\.({DISGUISED_VOLUME_EXTENSION_CHARS})\.(\d+)$",
            name,
            re.IGNORECASE,
        )
        if match is None or match.group(2).casefold() == "zip":
            return None
        return match.group(1), int(match.group(3)), match.group(2)
