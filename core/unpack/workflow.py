"""逐层解包编排与最终载荷落盘；失败时保留工作目录供恢复。"""

from __future__ import annotations

import shutil
import threading
from collections.abc import Callable, Sequence
from pathlib import Path

from core.backends import detect_archive_format, get_backend
from core.cancellation import Cancellation
from core.models import FORMAT_7Z, FORMAT_ZIP
from platforms import get_archive_platform

from .content import PADDING_NAME_PATTERN, classify_extracted
from .extraction import extract_layer
from .volumes import find_disguised_volume_set, stage_volume_set
from .workspace import unpack_workspace


def unpack_archive(
    archive: Path,
    output_dir: Path,
    *,
    rar_tool: Path | None = None,
    sevenzip_tool: Path | None = None,
    candidates: Sequence[str] = (),
    password_prompt: Callable[[int], str] | None = None,
    layer_limit: int | None = None,
    cancel_event: threading.Event | None = None,
    output_cb: Callable[[str], None] | None = None,
) -> list[Path]:
    """逐层解开嵌套压缩包，把原始文件释放到 output_dir，返回载荷条目。

    每层按文件头识别格式（RAR / 7z / ZIP）并选用对应的工具；rar_tool /
    sevenzip_tool 都是尽力提供（可以为 None），只在解到对应格式的层
    而工具缺失时才报错（zip 与 7z 共用 sevenzip_tool）。candidates 是
    优先尝试的密码（顺序任意）；
    全部失败且提供了 password_prompt 时逐层交互询问。layer_limit
    强制指定层数，用于载荷本身恰好是单个压缩包文件时避免多解一层；
    None 表示自动识别。最外层是伪装扩展名的分卷套（foo.part1.bin…
    / foo.bin.001…）时自动以标准卷名接入工作目录再解，无需手动改名。
    失败或取消时保留输出目录下的临时工作目录，便于手动续解。
    """

    def tool_for(archive_format: str) -> Path:
        if archive_format in (FORMAT_7Z, FORMAT_ZIP):
            if sevenzip_tool is None:
                raise RuntimeError(
                    f"遇到 {archive_format} 压缩层，但没有可用的 7-Zip 命令行"
                    "工具；请安装 7-Zip"
                    "（或使用 CLI 的 --install-tools 7z 模式）后重试"
                )
            if archive_format == FORMAT_ZIP:
                return get_archive_platform().resolve_tool(
                    str(sevenzip_tool), Path.cwd(), kind=FORMAT_ZIP
                )
            return sevenzip_tool
        if rar_tool is None:
            raise RuntimeError(
                "遇到 RAR 压缩层，但没有可用的 WinRAR/rar 命令行工具；"
                "请安装 WinRAR（或使用 CLI 的 --install-tools rar 模式）后重试"
            )
        return rar_tool

    cancellation = Cancellation(cancel_event)
    cancellation.check()
    archive = archive.resolve()
    outer_format = detect_archive_format(archive)
    if outer_format is None:
        raise RuntimeError(
            "不是受支持的压缩包（内容无 RAR/7z/ZIP 文件头，"
            f"伪装扩展名已按内容识别）：{archive}"
        )
    outer_backend = get_backend(outer_format)
    volume_match = outer_backend.volume_name_pattern.fullmatch(archive.name)
    if volume_match and int(volume_match.group(2)) != 1:
        first_volume = outer_backend.standard_volume_name(volume_match.group(1), 1)
        raise RuntimeError(f"分卷压缩包请从第一卷开始解包（如 {first_volume}）")

    with unpack_workspace(output_dir, cancellation, output_cb) as work:
        # 伪装分卷套：改回标准卷名后再解（见 find_disguised_volume_set）。
        disguised_set = find_disguised_volume_set(archive)
        if disguised_set is not None:
            volumes, base, disguised_backend = disguised_set
            parsed = disguised_backend.parse_disguised_volume(archive.name)
            assert parsed is not None
            if parsed[1] != 1:
                first_volume = disguised_backend.disguised_volume_name(
                    base, 1, parsed[2]
                )
                raise RuntimeError(
                    f"分卷压缩包请从第一卷开始解包（如 {first_volume}）"
                )
            if output_cb is not None:
                output_cb(
                    f"识别到伪装分卷（共 {len(volumes)} 卷），"
                    "已自动按标准卷名接入。"
                )
            current = stage_volume_set(
                volumes, base, disguised_backend, work / "volumes", cancellation
            )
            current_format = disguised_backend.format_name
        else:
            current = archive
            current_format = outer_format

        layer_index = 1
        known_passwords: list[str] = []
        while True:
            cancellation.check()
            backend = get_backend(current_format)
            layer_dir = work / f"layer_{layer_index}"
            layer_dir.mkdir()
            if output_cb is not None:
                output_cb(f"正在解第 {layer_index} 层：{current.name}")
            extract_layer(
                tool_for(current_format),
                backend,
                current,
                layer_dir,
                candidates,
                known_passwords,
                password_prompt,
                layer_index,
                cancellation,
                output_cb,
            )
            if layer_limit is not None and layer_index >= layer_limit:
                payload_dir = layer_dir
                break
            content = classify_extracted(layer_dir)
            if content.is_intermediate:
                current = content.volumes[0]
                current_format = content.archive_format
                layer_index += 1
                continue
            payload_dir = layer_dir
            break

        cancellation.check()
        # 载荷就位：删掉随机填充文件，检查同名冲突后移动到输出目录。
        for entry in payload_dir.iterdir():
            if PADDING_NAME_PATTERN.fullmatch(entry.name):
                entry.unlink(missing_ok=True)
        entries = sorted(payload_dir.iterdir())
        conflicts = [
            entry.name for entry in entries if (output_dir / entry.name).exists()
        ]
        if conflicts:
            raise RuntimeError(
                f"解包目标目录已有同名文件：{'、'.join(conflicts)}"
            )
        moved = []
        for entry in entries:
            target = output_dir / entry.name
            shutil.move(str(entry), str(target))
            moved.append(target)
    return moved
