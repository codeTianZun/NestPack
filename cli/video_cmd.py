"""独立视频融合与原归档提取的命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cli.display import print_json
from core.filesystem import normalize_user_path
from core.models import ConfigError
from core.result_summary import MANIFEST_SCHEMA_VERSION
from core.video import extract_video_archive, fuse_archive, inspect_video_archive


def run_video(arguments: argparse.Namespace) -> int:
    """复用核心原子发布流程，输出单文件完成结果。"""
    output = normalize_user_path(str(arguments.output)) if arguments.output else Path.cwd()
    source = normalize_user_path(str(arguments.fuse_archive or arguments.extract_video_archive))
    overwrite = bool(arguments.overwrite_existing)

    def report(message: str) -> None:
        print(message, file=sys.stderr if arguments.json else sys.stdout)

    if arguments.fuse_archive is not None:
        result = fuse_archive(
            normalize_user_path(arguments.video_path), source, output / f"{source.stem}.mp4",
            overwrite_existing=overwrite, output_cb=report,
        )
        mode = "video_fusion"
    else:
        record = inspect_video_archive(source)
        if record is None:
            raise ConfigError("所选文件不是 NestPack 生成的视频融合文件。")
        result = extract_video_archive(
            source, output / f"{source.stem}.{record.format}",
            overwrite_existing=overwrite, output_cb=report,
        )
        mode = "video_extract"
    if arguments.json:
        print_json({
            "tool": "nestpack", "schema_version": MANIFEST_SCHEMA_VERSION,
            "status": "ok", "mode": mode, "files": [str(result)],
        })
    else:
        print(f"已完成：{result}")
    return 0
