"""--unpack 解包模式的入口流程。

负责解包前的准备（定位压缩程序、合并候选密码、确定输出目录）与
解包后的结果展示；逐层解包本身由 core.unpack 完成。

候选密码合并顺序：--password → --password-file → --config 指定的
配置文件（或默认配置文件）里各层已保存的密码。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from cli.configuration import read_password_file
from cli.display import print_json
from cli.prompts import read_password
from core.config import load_config
from core.filesystem import normalize_user_path
from core.models import DEFAULT_CONFIG_PATH, FORMAT_7Z, ConfigError
from core.result_summary import MANIFEST_SCHEMA_VERSION
from core.unpack import unpack_archive
from platforms import resolve_optional_tool


def ask_unpack_password(layer_index: int, *, output_stream: TextIO | None = None) -> str:
    """解包时逐层询问密码；直接回车或输入流结束表示放弃。"""
    try:
        return read_password(
            f"第 {layer_index} 层密码（直接回车放弃）：",
            output_stream=output_stream,
        )
    except EOFError:
        return ""


def load_config_sidecar(config_path: Path, *, required: bool) -> tuple[str, str, list[str]]:
    """读取配置中的工具路径与各层已保存密码（作为解包候选）。"""
    winrar_setting = "auto"
    sevenzip_setting = "auto"
    passwords: list[str] = []
    if config_path.exists():
        try:
            config = load_config(config_path, allow_incomplete=True)
            winrar_setting = config.winrar_path
            sevenzip_setting = config.sevenzip_path
            passwords = [layer.password for layer in config.layers if layer.password]
        except (ConfigError, OSError) as error:
            if required:
                raise
            print(f"注意：未使用默认配置：{error}", file=sys.stderr)
    elif required:
        raise ConfigError(f"指定的配置文件不存在：{config_path}")
    return winrar_setting, sevenzip_setting, passwords


def _stderr_line(line: str) -> None:
    print(line, file=sys.stderr)


def _stdout_line(line: str) -> None:
    print(line)


def run_unpack(arguments: argparse.Namespace) -> int:
    """--unpack 的主流程：定位压缩包与输出目录后逐层解包。"""
    json_mode = arguments.json
    archive = normalize_user_path(str(arguments.unpack))
    if not archive.exists():
        message = f"找不到压缩包：{archive}"
        if json_mode:
            print_json(
                {
                    "tool": "nestpack",
                    "schema_version": MANIFEST_SCHEMA_VERSION,
                    "status": "error",
                    "error_kind": "input_not_found",
                    "error": message,
                }
            )
        else:
            print(message)
        return 1

    config_path = (
        normalize_user_path(str(arguments.config))
        if arguments.config is not None
        else DEFAULT_CONFIG_PATH
    )
    winrar_setting, sevenzip_setting, config_passwords = load_config_sidecar(
        config_path, required=arguments.config is not None
    )
    candidates = list(arguments.password)
    if arguments.password_file is not None:
        candidates.extend(read_password_file(normalize_user_path(str(arguments.password_file))))
    candidates.extend(config_passwords)

    # 两种工具都尽力解析（auto 未找到不阻断），真正解到对应格式的层
    # 而工具缺失时由 core.unpack 报清晰错误。
    config_directory = config_path.parent
    rar_tool = resolve_optional_tool(
        arguments.winrar_path or winrar_setting,
        Path.cwd() if arguments.winrar_path else config_directory,
    )
    sevenzip_tool = resolve_optional_tool(
        arguments.sevenzip_path or sevenzip_setting,
        Path.cwd() if arguments.sevenzip_path else config_directory,
        kind=FORMAT_7Z,
    )
    if arguments.output is not None:
        output_dir = normalize_user_path(str(arguments.output))
    else:
        output_dir = archive.parent / f"{archive.stem}_unpacked"

    def tool_line(label: str, tool: Path | None) -> str:
        if tool is not None:
            return f"{label}：{tool}"
        return f"{label}：未检测到（遇到对应格式层时才会用到）"

    if json_mode:
        print(tool_line("WinRAR", rar_tool), file=sys.stderr)
        print(tool_line("7-Zip（解 7z / zip 层）", sevenzip_tool), file=sys.stderr)
        print(f"解包输出目录：{output_dir}", file=sys.stderr)
        output_cb = _stderr_line
    else:
        print(tool_line("WinRAR", rar_tool))
        print(tool_line("7-Zip（解 7z / zip 层）", sevenzip_tool))
        print(f"解包输出目录：{output_dir}")
        output_cb = _stdout_line

    entries = unpack_archive(
        archive,
        output_dir,
        rar_tool=rar_tool,
        sevenzip_tool=sevenzip_tool,
        candidates=candidates,
        password_prompt=None
        if arguments.non_interactive
        else lambda layer_index: ask_unpack_password(
            layer_index, output_stream=sys.stderr if json_mode else None
        ),
        layer_limit=arguments.layers,
        output_cb=output_cb,
    )
    if json_mode:
        print_json(
            {
                "tool": "nestpack",
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "status": "ok",
                "mode": "unpack",
                "output_dir": str(output_dir),
                "entries": [str(entry) for entry in entries],
            }
        )
        return 0
    print(f"\n解包完成，共恢复 {len(entries)} 个条目：")
    for entry in entries:
        print(f"  {entry}")
    return 0
