"""WinRAR / rarlab rar 的命令、签名、分卷规则与退出码。"""

from __future__ import annotations

import re
from pathlib import Path

from core.models import FORMAT_RAR
from platforms import get_archive_platform

from .base import DISGUISED_VOLUME_EXTENSION_CHARS, has_signature

# RAR4 与 RAR5 共用的 6 字节签名前缀。
RAR_SIGNATURE = b"Rar!\x1a\x07"

# WinRAR / rarlab rar 的退出码含义（官方文档 EXIT CODE 章节）。
RAR_EXIT_CODES: dict[int, str] = {
    1: "警告（非致命错误，例如文件被跳过）",
    2: "致命错误",
    3: "CRC 校验错误（数据损坏）",
    4: "试图修改被锁定的压缩包",
    5: "写入错误（磁盘满或权限不足）",
    6: "文件打开错误",
    7: "命令行参数错误",
    8: "内存不足",
    9: "文件创建错误",
    10: "没有匹配的文件",
    11: "密码错误",
    255: "用户中断",
}


class RarBackend:
    """WinRAR / rarlab rar 命令行的 RAR5 后端。"""

    format_name = FORMAT_RAR
    archive_extension = ".rar"
    signature = RAR_SIGNATURE
    exit_codes = RAR_EXIT_CODES
    volume_name_pattern = re.compile(r"^(.*)\.part(\d+)\.rar$", re.IGNORECASE)

    def looks_like(self, path: Path) -> bool:
        return has_signature(path, self.signature)

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
            "-cfg-",  # 不读取用户的 WinRAR 全局配置，确保行为可预测。
            "-ma5",  # 使用 RAR5 格式，恢复记录功能依赖 RAR 格式。
            f"-m{compression_level}",  # 0-5：仅存储到最高压缩。
            "-ep1",  # 不保存输入项父目录的绝对路径。
            "-y",  # 自动回答 WinRAR 自己的确认问题。
        ]
        if source.is_dir():
            command.append("-r")
        if background:
            # -ibck 让 WinRAR 在后台运行，不弹出压缩进度窗口。
            command.extend(get_archive_platform().background_switch())
        if password:
            # -hp 同时加密文件内容与压缩包内文件名。
            command.append(f"-hp{password}")
        if recovery_percent is not None:
            command.append(f"-rr{recovery_percent}p")
        if volume_size:
            # -v 把压缩包切分成固定大小的分卷（如 -v500m），适配网盘单文件大小限制。
            command.append(f"-v{volume_size}")
        command.extend([str(destination), "--", source.name, *extra_inputs])
        return command

    def build_test_command(
        self,
        tool: Path,
        archive: Path,
        password: str = "",
        *,
        background: bool = False,
    ) -> list[str]:
        command = [str(tool), "t", "-cfg-", "-y"]
        if background:
            command.extend(get_archive_platform().background_switch())
        if password:
            command.append(f"-p{password}")
        command.append(str(archive))
        return command

    def build_extract_command(
        self, tool: Path, archive: Path, password: str = ""
    ) -> list[str]:
        command = [
            str(tool),
            "x",
            "-cfg-",
            "-y",
            *get_archive_platform().background_switch(),
        ]
        if password:
            command.append(f"-p{password}")
        command.extend(["--", str(archive)])
        return command

    def volume_final_names(self, destination: Path, count: int) -> list[Path]:
        return [
            destination.with_suffix(f".part{number}.rar")
            for number in range(1, count + 1)
        ]

    def volume_set_base(self, destination: Path) -> Path:
        # foo.rar → foo；正式卷名形如 foo.part1.rar。
        return destination.with_suffix("")

    def find_volumes(self, base: Path) -> list[tuple[int, Path]]:
        found: list[tuple[int, Path]] = []
        escaped = re.escape(base.name)
        for path in base.parent.iterdir():
            match = re.fullmatch(
                rf"{escaped}\.part(\d+)\.rar", path.name, re.IGNORECASE
            )
            if match:
                found.append((int(match.group(1)), path))
        found.sort()
        return found

    def standard_volume_name(self, base: str, number: int) -> str:
        return f"{base}.part{number}.rar"

    def bare_volume_target(self, base: Path) -> Path | None:
        # 实测（rar 7.x 与 WinRAR）：内容不超过一卷时 rar 直接以基准名
        # 落盘、不带 .partN.rar 后缀，补上第一卷卷名后按常规分卷处理。
        return base.with_name(f"{base.name}.part1.rar")

    def parse_disguised_volume(self, name: str) -> tuple[str, int, str] | None:
        match = re.fullmatch(
            rf"^(.*)\.part(\d+)\.({DISGUISED_VOLUME_EXTENSION_CHARS})$",
            name,
            re.IGNORECASE,
        )
        if match is None or match.group(3).casefold() == "rar":
            return None
        return match.group(1), int(match.group(2)), match.group(3)

    def disguised_volume_name(self, base: str, number: int, extension: str) -> str:
        return f"{base}.part{number}.{extension}"

    def disguise_name(self, path: Path, extension: str) -> Path:
        return path.with_suffix(extension)
