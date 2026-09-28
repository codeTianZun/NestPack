"""启动前检查：磁盘占用估算与偏紧提醒。

只做提醒不拦截：估算按不可压缩计，实际占用通常更小。
"""

from __future__ import annotations

import shutil
from pathlib import Path

from core.models import COMPRESS_MODE_COMBINED, AppConfig


def path_size(path: Path) -> int:
    """返回文件或文件夹的总大小（符号链接本身不计）。"""
    if path.is_file():
        return path.stat().st_size
    total = 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def disk_warnings(
    config: AppConfig, sources: list[Path], output_directory: Path, *, video_bytes: int = 0,
) -> tuple[str, ...]:
    """启动前估算磁盘占用并与剩余空间比较，偏紧时给出提示。

    来源大小合计不足 64MiB 时跳过剩余空间比较。
    """
    try:
        # 缓存每个来源的大小，避免后续计算 copy_total 时对同一目录
        # 再次全量 rglob（大目录的重复遍历开销显著）。
        sizes = {source: path_size(source) for source in sources}
        source_total = sum(sizes.values())
        if source_total + video_bytes < 64 * 1024 * 1024:
            return ()
        ancestor = output_directory
        while not ancestor.exists():
            ancestor = ancestor.parent
        free = shutil.disk_usage(ancestor).free
    except OSError:
        return ()

    # 压缩峰值：上一层产物 + 正在写入的临时文件，约两份数据，
    # 外加恢复记录等零头；按不可压缩估算，宁多勿少。
    retained = 2.2 if config.delete_inner_after_verify else len(config.layers) + 1
    need = int((source_total + video_bytes) * retained)
    if any(layer.disguise.mode == "video" for layer in config.layers):
        need += source_total + video_bytes

    # 需要整份复制的部分：合并多来源的暂存目录、脱敏别名的文件夹复制。
    copy_total = 0
    for source in sources:
        if not source.is_dir():
            continue
        if config.hide_source_name or (
            config.compress_mode == COMPRESS_MODE_COMBINED and len(sources) > 1
        ):
            copy_total += sizes[source]
    need += copy_total

    if free >= need:
        return ()
    gib = 1024**3
    return (
        f"磁盘空间可能不足：预计需要约 {need / gib:.1f}GiB"
        f"（含脱敏/暂存复制 {copy_total / gib:.1f}GiB），"
        f"输出盘剩余 {free / gib:.1f}GiB。估算按不可压缩计算，实际通常更小，"
        "空间不足时任务会中途失败。",
    )
