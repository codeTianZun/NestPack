"""归档后端协议、文件头匹配与退出码描述。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

DISGUISED_VOLUME_EXTENSION_CHARS = r"[0-9A-Za-z]{1,8}"


def has_signature(path: Path, signature: bytes) -> bool:
    """按文件头判断格式；无法读取时按不匹配处理。"""
    try:
        with path.open("rb") as stream:
            return stream.read(len(signature)) == signature
    except OSError:
        return False


class ArchiveBackend(Protocol):
    """单一归档格式的命令构建与命名约定。"""

    format_name: str
    archive_extension: str
    signature: bytes
    exit_codes: dict[int, str]
    # 正式分卷文件名的模式（解包侧识别整套分卷用）。
    volume_name_pattern: re.Pattern[str]

    def looks_like(self, path: Path) -> bool:
        """按文件头判断是否为本格式（与扩展名无关）。"""
        ...

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
        """构造"把 source（可带附加输入）压成 destination"的参数列表。"""
        ...

    def build_test_command(
        self,
        tool: Path,
        archive: Path,
        password: str = "",
        *,
        background: bool = False,
    ) -> list[str]:
        """构造自检（t）命令。"""
        ...

    def build_extract_command(
        self, tool: Path, archive: Path, password: str = ""
    ) -> list[str]:
        """构造解压（x）命令；rar 族始终带后台开关避免弹窗。"""
        ...

    def volume_final_names(self, destination: Path, count: int) -> list[Path]:
        """返回分卷层的正式文件名（如 foo.rar + 3 卷的三个卷名）。"""
        ...

    def volume_set_base(self, destination: Path) -> Path:
        """返回正式分卷套的基准名（find_volumes 的锚点）。"""
        ...

    def find_volumes(self, base: Path) -> list[tuple[int, Path]]:
        """枚举目录中属于 base 分卷套的文件，按卷号升序返回。"""
        ...

    def standard_volume_name(self, base: str, number: int) -> str:
        """返回第 number 卷的标准文件名。"""
        ...

    def bare_volume_target(self, base: Path) -> Path | None:
        """内容不足一卷时工具可能直接以基准名落盘，返回应补改的卷名。

        无该行为的格式返回 None。
        """
        ...

    def parse_disguised_volume(self, name: str) -> tuple[str, int, str] | None:
        """识别伪装分卷名，返回 (基准名, 卷号, 伪装扩展名)；非本格式返回 None。"""
        ...

    def disguised_volume_name(self, base: str, number: int, extension: str) -> str:
        """返回第 number 卷的伪装文件名（与 parse_disguised_volume 互逆）。"""
        ...

    def disguise_name(self, path: Path, extension: str) -> Path:
        """返回产物改名为伪装扩展名后的路径（保留卷号信息）。"""
        ...


def describe_exit_code(
    return_code: int,
    tool: Path,
    exit_codes: dict[int, str],
) -> str:
    """按后端码表把归档工具退出码翻译成中文；未知码原样给出数字。"""
    meaning = exit_codes.get(return_code)
    if meaning is None:
        return f"{tool.name} 返回错误代码 {return_code}"
    return f"{tool.name} 返回错误代码 {return_code}（{meaning}）"
