"""压缩计划与结果：任务、层参数和产物之间的明确对应关系。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.models import AppConfig, LayerConfig
from core.naming import layer_output_paths
from core.sfx import SfxPlan


@dataclass(frozen=True)
class LayerPlan:
    """一层已展开的参数、工具、归档目标及伪装设置。"""

    config: LayerConfig
    tool: Path
    destination: Path
    disguise_extension: str | None = None
    video: Path | None = None
    sfx: SfxPlan | None = None

    def output_paths(self, volume_count: int = 1) -> tuple[Path, ...]:
        """按实际卷数生成产物路径；预览时用第一卷表达尚未确定大小的分卷套。"""
        return layer_output_paths(self.config, self.destination, volume_count)


@dataclass(frozen=True)
class TaskPlan:
    """生成一套嵌套压缩包的任务；来源与层顺序在计划阶段确定。"""

    sources: tuple[Path, ...]
    output_directory: Path
    layers: tuple[LayerPlan, ...]


@dataclass(frozen=True)
class CompressionPlan:
    """供校验、预览和执行共同使用的压缩计划。"""

    config: AppConfig
    config_path: Path | None
    output_directory: Path
    tasks: tuple[TaskPlan, ...]
    winrar: Path | None
    sevenzip: Path | None
    warnings: tuple[str, ...] = ()

    @property
    def sources(self) -> tuple[Path, ...]:
        """按任务顺序返回本次压缩的原始来源。"""
        return tuple(source for task in self.tasks for source in task.sources)

    @property
    def total_layers(self) -> int:
        """本次压缩需要完成的总层数。"""
        return sum(len(task.layers) for task in self.tasks)

    @property
    def protected_inputs(self) -> tuple[Path, ...]:
        """所有原始来源、载体视频和自解压素材，发布时均须保持完整。"""
        videos = (
            layer.video for task in self.tasks for layer in task.layers
            if layer.video is not None
        )
        resources = (
            resource for task in self.tasks for layer in task.layers
            if layer.sfx is not None for resource in layer.sfx.resources
        )
        return (*self.sources, *videos, *resources)


@dataclass(frozen=True)
class LayerResult:
    """一层的计划与实际产物；被后续层包裹并清理的文件仍保留路径记录。"""

    plan: LayerPlan
    files: tuple[Path, ...]


@dataclass(frozen=True)
class TaskResult:
    """一套嵌套压缩包的结果，关联原始来源与各层产物。"""

    plan: TaskPlan
    layers: tuple[LayerResult, ...]

    @property
    def final_files(self) -> tuple[Path, ...]:
        """最外层完成伪装等处理后的交付文件。"""
        return self.layers[-1].files


@dataclass(frozen=True)
class CompressionResult:
    """全部任务的执行结果，任务顺序与计划一致。"""

    plan: CompressionPlan
    tasks: tuple[TaskResult, ...]

    @property
    def final_files(self) -> tuple[Path, ...]:
        """按任务顺序返回全部最外层交付文件。"""
        return tuple(path for task in self.tasks for path in task.final_files)
