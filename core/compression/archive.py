"""单层归档生命周期：临时输出、压缩、自检、隐私处理与正式发布。"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from core.backends import ArchiveBackend, describe_exit_code, get_backend
from core.cancellation import Cancellation
from core.filesystem import temporary_directory
from core.process import run_command
from core.video import write_fused_video

from .models import LayerPlan
from .outputs import check_output_paths, existing_outputs, publish_files
from .privacy import randomize_timestamps


def compress_layer(
    planned: LayerPlan,
    source: Path,
    *,
    show_gui: bool,
    compression_level: int,
    overwrite_existing: bool,
    cancellation: Cancellation,
    original_sources: tuple[Path, ...],
    extra_inputs: tuple[str, ...] = (),
    verify: bool = False,
    randomize_time: bool = False,
    output_cb: Callable[[str], None] | None = None,
) -> tuple[Path, ...]:
    """执行一层归档并返回实际交付路径，离开作用域时清理全部临时输出。"""
    cancellation.check()
    layer = planned.config
    backend = get_backend(layer.format)
    protected_inputs = (*original_sources, source, *(source.parent / name for name in extra_inputs))
    check_output_paths(existing_outputs(planned), overwrite_existing, protected_inputs)
    with temporary_directory(planned.destination.parent) as work:
        part = work / f"{planned.destination.name}.part"
        command = backend.build_add_command(
            planned.tool,
            source,
            part,
            compression_level=compression_level,
            background=not show_gui,
            password=layer.password,
            recovery_percent=layer.recovery_percent,
            volume_size=layer.volume_size,
            extra_inputs=extra_inputs,
        )
        return_code = run_command(
            command, cwd=source.parent, cancellation=cancellation,
            output_cb=output_cb, hide_console=output_cb is not None,
        )
        if return_code != 0:
            raise RuntimeError(
                f"{describe_exit_code(return_code, planned.tool, backend.exit_codes)}，"
                "压缩未成功。"
            )
        products = _collect_products(part, backend, bool(layer.volume_size), planned.tool)
        if verify:
            verify_archive(
                planned.tool, backend, products[0], layer.password,
                show_gui=show_gui, cancellation=cancellation, output_cb=output_cb,
            )
        if planned.video is not None:
            fused = work / "fused.mp4"
            write_fused_video(planned.video, products[0], fused, cancellation, output_cb)
            if verify:
                verify_archive(
                    planned.tool, backend, fused, layer.password,
                    show_gui=show_gui, cancellation=cancellation, output_cb=output_cb,
                )
            products = (fused,)
        if randomize_time:
            randomize_timestamps(products, cancellation)
        return publish_files(
            products, planned,
            overwrite_existing=overwrite_existing, cancellation=cancellation,
            protected_inputs=protected_inputs,
        )


def verify_archive(
    tool: Path,
    backend: ArchiveBackend,
    archive: Path,
    password: str,
    *,
    show_gui: bool,
    cancellation: Cancellation,
    output_cb: Callable[[str], None] | None,
) -> None:
    """运行工具的 t 自检，支持停止；分卷传入第一卷即可检查整套。"""
    command = backend.build_test_command(tool, archive, password, background=not show_gui)
    return_code = run_command(
        command, cancellation=cancellation, output_cb=output_cb,
        hide_console=output_cb is not None or not show_gui,
    )
    if return_code != 0:
        raise RuntimeError(
            "压缩包自检失败"
            f"（{describe_exit_code(return_code, tool, backend.exit_codes)}）：{archive}"
        )


def _collect_products(
    part: Path, backend: ArchiveBackend, split: bool, tool: Path,
) -> tuple[Path, ...]:
    """收集工具产生的文件，补齐 RAR 内容不足一卷时的卷名。"""
    if not split:
        if not part.is_file():
            raise RuntimeError(f"{tool.name} 未报告错误，但没有找到输出压缩包。")
        return (part,)
    volumes = backend.find_volumes(part)
    if not volumes and part.is_file():
        bare_target = backend.bare_volume_target(part)
        if bare_target is not None:
            os.replace(part, bare_target)
            volumes = backend.find_volumes(part)
    if not volumes:
        raise RuntimeError(f"{tool.name} 未报告错误，但没有找到输出的分卷。")
    return tuple(path for _number, path in volumes)
