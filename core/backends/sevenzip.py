"""7-Zip 的命令、签名、分卷规则与退出码。"""

from __future__ import annotations

import re
from pathlib import Path

from core.models import FORMAT_7Z

from .base import DISGUISED_VOLUME_EXTENSION_CHARS, has_signature

SEVENZIP_SIGNATURE = b"7z\xbc\xaf\x27\x1c"

# 7-Zip 的退出码含义（官方文档 EXIT CODE 章节）。
# 密码错误与数据损坏同为 2，报错文案不区分两者。
SEVENZIP_EXIT_CODES: dict[int, str] = {
    1: "警告（非致命错误）",
    2: "致命错误（密码错误或数据损坏）",
    7: "命令行参数错误",
    8: "内存不足",
    255: "用户中断",
}

# 配置的 0-5 压缩级别映射到 7z 的 -mx 刻度。
SEVENZIP_LEVEL_MAP = {0: 0, 1: 1, 2: 3, 3: 5, 4: 7, 5: 9}


class SevenZipBackend:
    """7-Zip 命令行（7z / 7zz / 7zr）的 .7z 后端。"""

    format_name = FORMAT_7Z
    archive_extension = ".7z"
    signature = SEVENZIP_SIGNATURE
    exit_codes = SEVENZIP_EXIT_CODES
    volume_name_pattern = re.compile(r"^(.*)\.7z\.(\d+)$", re.IGNORECASE)

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
            "-t7z",
            f"-mx{SEVENZIP_LEVEL_MAP[compression_level]}",
            "-y",
        ]
        if password:
            # -mhe=on 加密压缩包头（文件名等），等价 rar 的 -hp。
            command.extend([f"-p{password}", "-mhe=on"])
        if volume_size:
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
        command = [str(tool), "t", "-y"]
        if password:
            command.append(f"-p{password}")
        command.append(str(archive))
        return command

    def build_extract_command(
        self, tool: Path, archive: Path, password: str = ""
    ) -> list[str]:
        command = [str(tool), "x", "-y"]
        if password:
            command.append(f"-p{password}")
        command.extend(["--", str(archive)])
        return command

    def volume_final_names(self, destination: Path, count: int) -> list[Path]:
        return [
            destination.with_name(f"{destination.name}.{number:03d}")
            for number in range(1, count + 1)
        ]

    def volume_set_base(self, destination: Path) -> Path:
        # foo.7z 的正式卷名形如 foo.7z.001，基准名就是压缩包名本身。
        return destination

    def find_volumes(self, base: Path) -> list[tuple[int, Path]]:
        found: list[tuple[int, Path]] = []
        escaped = re.escape(base.name)
        for path in base.parent.iterdir():
            match = re.fullmatch(rf"{escaped}\.(\d+)$", path.name, re.IGNORECASE)
            if match:
                found.append((int(match.group(1)), path))
        found.sort()
        return found

    def standard_volume_name(self, base: str, number: int) -> str:
        return f"{base}.7z.{number:03d}"

    def bare_volume_target(self, base: Path) -> Path | None:
        # 7z 指定 -v 时总是以 .001 卷名落盘，无需补名。
        return None

    def parse_disguised_volume(self, name: str) -> tuple[str, int, str] | None:
        match = re.fullmatch(
            rf"^(.*)\.({DISGUISED_VOLUME_EXTENSION_CHARS})\.(\d+)$",
            name,
            re.IGNORECASE,
        )
        if match is None or match.group(2).casefold() == "7z":
            return None
        return match.group(1), int(match.group(3)), match.group(2)

    def disguised_volume_name(self, base: str, number: int, extension: str) -> str:
        return f"{base}.{extension}.{number:03d}"

    def disguise_name(self, path: Path, extension: str) -> Path:
        # 分卷 foo.7z.001 改名时保留末尾卷号，将中间的 .7z 换成伪装扩展名。
        match = self.volume_name_pattern.fullmatch(path.name)
        if match is not None:
            return path.with_name(f"{match.group(1)}{extension}.{match.group(2)}")
        return path.with_suffix(extension)
