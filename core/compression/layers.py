"""执行一套嵌套层，按任务策略管理本次生成的层产物。"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path

from core.cancellation import Cancellation
from core.filesystem import cleanup_path
from core.models import AppConfig

from .archive import compress_layer
from .level import resolve_compression_level
from .models import LayerResult, TaskPlan, TaskResult
from .privacy import padding_file


def run_layer_stack(
    task: TaskPlan,
    config: AppConfig,
    source: Path,
    cancellation: Cancellation,
    output_cb: Callable[[str], None] | None,
    *,
    original_sources: tuple[Path, ...],
    on_layer_started: Callable[[str], None] | None = None,
    on_layer_completed: Callable[[str], None] | None = None,
) -> TaskResult:
    """逐层执行已就绪的来源，失败或取消时按配置清理该任务的已生成产物。"""
    current_source = source
    previous_products: tuple[Path, ...] = ()
    layer_results: list[LayerResult] = []
    layer_count = len(task.layers)
    try:
        for layer_number, planned in enumerate(task.layers, start=1):
            cancellation.check()
            if on_layer_started is not None:
                on_layer_started(
                    f"正在准备第 {layer_number}/{layer_count} 层："
                    f"{planned.config.archive_name}"
                )
            padding = (
                padding_file(current_source.parent, cancellation)
                if config.add_padding else nullcontext(None)
            )
            with padding as extra:
                extra_inputs = tuple(product.name for product in previous_products[1:])
                if extra is not None:
                    extra_inputs += (extra.name,)
                compression_level = resolve_compression_level(
                    planned.config, current_source, layer_number == 1, cancellation,
                )
                products = compress_layer(
                    planned, current_source,
                    show_gui=config.show_winrar_gui,
                    compression_level=compression_level,
                    overwrite_existing=config.overwrite_existing,
                    cancellation=cancellation,
                    original_sources=original_sources,
                    extra_inputs=extra_inputs,
                    verify=config.verify_after_compress,
                    randomize_time=config.randomize_timestamps and layer_number == layer_count,
                    output_cb=output_cb,
                )
                layer_results.append(LayerResult(plan=planned, files=products))
            current_source = products[0]
            previous_products = products
            if config.delete_inner_after_verify and len(layer_results) >= 2:
                for finished in layer_results[-2].files:
                    cleanup_path(finished)
            if on_layer_completed is not None:
                on_layer_completed(f"第 {layer_number}/{layer_count} 层打包完成")
        cancellation.check()
        return TaskResult(plan=task, layers=tuple(layer_results))
    except BaseException:
        if config.cleanup_on_failure:
            for produced in layer_results:
                for archive in produced.files:
                    cleanup_path(archive)
        raise
