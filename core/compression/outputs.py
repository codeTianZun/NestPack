"""层产物发布：目标检查、正式文件替换与分卷失败恢复。"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from core.backends import get_backend
from core.cancellation import Cancellation
from core.filesystem import cleanup_path, link_or_copy_file
from core.models import FORMAT_RAR

from .models import LayerPlan


def existing_outputs(planned: LayerPlan) -> tuple[Path, ...]:
    """枚举该层已有的正式产物，包含旧分卷套的全部卷。"""
    backend = get_backend(planned.config.format)
    if planned.video is not None:
        return tuple(path for path in planned.output_paths() if path.exists())
    base = planned.destination
    if planned.disguise_extension is not None:
        base = backend.disguise_name(base, planned.disguise_extension)
    if not planned.config.volume_size:
        return (base,) if base.exists() else ()
    found: list[Path] = []
    first = planned.output_paths()[0]
    if not first.parent.exists():
        return ()
    if planned.sfx is not None and (
        planned.disguise_extension is None
        or planned.disguise_extension.casefold() in (".exe", ".sfx")
    ):
        tail = re.compile(
            rf"{re.escape(planned.destination.stem)}\.part(\d+)\.rar", re.IGNORECASE,
        )
        for path in first.parent.iterdir():
            match = tail.fullmatch(path.name)
            if path.name == first.name or (match is not None and int(match.group(1)) > 1):
                found.append(path)
        return tuple(sorted(found))
    standard = backend.volume_name_pattern.fullmatch(first.name)
    disguised = backend.parse_disguised_volume(first.name)
    if disguised is not None:
        standard = None
    for path in first.parent.iterdir():
        if standard is not None:
            if (planned.config.format == FORMAT_RAR
                    and path.suffix.casefold() != first.suffix.casefold()):
                continue
            match = backend.volume_name_pattern.fullmatch(path.name)
            if match is not None and match.group(1).casefold() == standard.group(1).casefold():
                found.append(path)
        elif disguised is not None:
            parsed = backend.parse_disguised_volume(path.name)
            if parsed is not None and (
                parsed[0].casefold(), parsed[2].casefold()
            ) == (disguised[0].casefold(), disguised[2].casefold()):
                found.append(path)
    return tuple(sorted(found))


def check_output_paths(
    destinations: tuple[Path, ...],
    overwrite_existing: bool,
    protected_inputs: tuple[Path, ...],
) -> None:
    """按覆盖策略检查整层目标，在替换任何文件前报告冲突。"""
    for destination in destinations:
        if destination in protected_inputs or (
            destination.exists() and any(
                source.exists() and destination.samefile(source) for source in protected_inputs
            )
        ):
            raise RuntimeError(f"输出压缩包不能覆盖输入文件：{destination}")
        if not destination.exists():
            continue
        if not overwrite_existing:
            raise RuntimeError(
                f"输出文件已存在：{destination}\n"
                "如需自动覆盖，请将 overwrite_existing 设置为 true。"
            )
        if not destination.is_file():
            raise RuntimeError(f"输出路径已存在但不是文件：{destination}")


def publish_files(
    products: tuple[Path, ...],
    planned: LayerPlan,
    *,
    overwrite_existing: bool,
    cancellation: Cancellation,
    protected_inputs: tuple[Path, ...],
) -> tuple[Path, ...]:
    """发布已完成自检和隐私处理的整层文件，分卷替换失败时恢复旧文件。"""
    cancellation.check()
    destinations = planned.output_paths(len(products))
    previous = existing_outputs(planned)
    check_output_paths(previous, overwrite_existing, protected_inputs)
    check_output_paths(destinations, overwrite_existing, protected_inputs)
    pairs = tuple(zip(products, destinations, strict=True))
    obsolete = set(previous).difference(destinations)
    if len(pairs) == 1 and not obsolete:
        source, destination = pairs[0]
        os.replace(source, destination)
        return destinations

    backup_directory = Path(
        tempfile.mkdtemp(prefix=".nestpack-backup-", dir=destinations[0].parent)
    )
    backups: dict[Path, Path] = {}
    attempted: list[Path] = []
    keep_backups = False
    try:
        for index, destination in enumerate(sorted(set(previous).union(destinations))):
            if destination.exists():
                backup = backup_directory / str(index)
                link_or_copy_file(destination, backup, cancellation)
                backups[destination] = backup
        cancellation.check()
        try:
            # 发布整套分卷期间完成替换或恢复；取消检查位于发布前。
            for source, destination in pairs:
                attempted.append(destination)
                os.replace(source, destination)
            for destination in sorted(obsolete):
                attempted.append(destination)
                destination.unlink()
        except BaseException as error:
            unrestored: list[Path] = []
            for destination in reversed(attempted):
                try:
                    if destination in backups:
                        os.replace(backups[destination], destination)
                    else:
                        destination.unlink(missing_ok=True)
                except OSError:
                    unrestored.append(destination)
            if unrestored:
                keep_backups = True
                raise RuntimeError(
                    f"产物发布失败（{error}），部分文件无法恢复："
                    f"{'、'.join(str(path) for path in unrestored)}；"
                    f"旧文件备份保留在：{backup_directory}"
                ) from error
            raise
        return destinations
    finally:
        if not keep_backups:
            cleanup_path(backup_directory)
