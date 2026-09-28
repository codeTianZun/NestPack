"""压缩计划构建：解析工具与来源、展开层名并校验任务的输出位置。"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from core.config import parse_config, validate_archive_name
from core.filesystem import normalize_user_path
from core.models import (
    COMPRESS_MODE_SEPARATE,
    FORMAT_7Z,
    FORMAT_RAR,
    FORMAT_ZIP,
    AppConfig,
    ConfigError,
    LayerConfig,
)
from core.naming import resolve_archive_name
from core.sfx import SfxPlan, resolve_sfx
from core.source_layers import source_layer_groups
from core.video import validate_video
from platforms import get_archive_platform
from platforms.win32.filename_rules import validate_filename as windows_filename

from .models import CompressionPlan, LayerPlan, TaskPlan
from .outputs import check_output_paths, existing_outputs
from .preflight import disk_warnings


def _resolve_tools(
    config: AppConfig, config_directory: Path, used_formats: set[str],
) -> dict[str, Path]:
    """只解析本次使用的工具；7z 与 ZIP 共用同一可执行文件。"""
    platform = get_archive_platform()
    tools: dict[str, Path] = {}
    for kind, configured in ((FORMAT_RAR, config.winrar_path), (FORMAT_7Z, config.sevenzip_path)):
        formats = {FORMAT_RAR} if kind == FORMAT_RAR else {FORMAT_7Z, FORMAT_ZIP}
        if not used_formats.intersection(formats):
            continue
        required_format = FORMAT_ZIP if kind == FORMAT_7Z and FORMAT_ZIP in used_formats else kind
        try:
            tool = platform.resolve_tool(configured, config_directory, kind=required_format)
        except ConfigError as error:
            raise ConfigError(
                f"{error}；可使用 GUI 的依赖安装按钮，或 CLI 的 --install-tools {kind} 模式"
            ) from error
        for archive_format in formats:
            tools[archive_format] = tool
    return tools


def _resolve_sources(config: AppConfig, config_directory: Path) -> tuple[Path, ...]:
    """解析来源并校验存在性和名称唯一性。"""
    raw_sources = config.effective_source_paths()
    if not raw_sources:
        raise ConfigError("source_path 不能为空，请至少指定一个原始文件或文件夹")
    sources: list[Path] = []
    seen_names: set[str] = set()
    for raw_source in raw_sources:
        source = normalize_user_path(raw_source, config_directory)
        if not source.exists():
            raise ConfigError(f"source_path 不存在：{source}")
        folded = source.name.casefold()
        if folded in seen_names:
            raise ConfigError(f"多个来源同名：{source.name}，请区分来源名称")
        seen_names.add(folded)
        sources.append(source)
    return tuple(sources)


def _plan_task(
    configs: list[LayerConfig],
    sources: tuple[Path, ...],
    output_directory: Path,
    tools: dict[str, Path],
    videos: dict[int, Path],
    sfx_plans: dict[int, SfxPlan] | None = None,
) -> TaskPlan:
    """确定一套嵌套压缩包的层参数与输出命名。"""
    layers: list[LayerPlan] = []
    for index, layer in enumerate(configs):
        try:
            name = resolve_archive_name(layer, index + 1, sources[0])
            name = validate_archive_name(
                name, layer.format,
                sfx_extension=layer.sfx.extension if layer.sfx.enabled else None,
            )
            if layer.sfx.enabled and layer.sfx.target == "windows":
                windows_filename(name)
                for previous in layers[-1:]:
                    for path in previous.output_paths():
                        windows_filename(path.name)
        except ValueError as error:
            raise ConfigError(
                f"layers[{index}] 的层名无效（来源：{sources[0].name}）：{error}"
            ) from error
        layers.append(
            LayerPlan(
                config=replace(layer, archive_name=name),
                tool=tools[layer.format],
                destination=(output_directory / name).resolve(),
                video=videos.get(index),
                sfx=(sfx_plans or {}).get(index),
                disguise_extension=(
                    layer.disguise.extension
                    if layer.disguise.mode == "extension"
                    else None
                ),
            )
        )
    return TaskPlan(sources=sources, output_directory=output_directory, layers=tuple(layers))


def _validate_windows_sources(sources: tuple[Path, ...], hide_root: bool) -> None:
    """在制作 Windows 首层前检查实际要释放的来源名称和同目录大小写冲突。"""
    def check_names(parent: Path, names: list[str]) -> None:
        seen: set[str] = set()
        for name in names:
            try:
                if windows_filename(name) != name:
                    raise ValueError("名称首尾含空白")
                if name.casefold() in seen:
                    raise ValueError("同目录文件名只存在大小写差异")
            except ValueError as error:
                raise ConfigError(
                    f"Windows 自解压无法按原名释放 {parent / name}：{error}"
                ) from error
            seen.add(name.casefold())

    for source in sources:
        if not hide_root:
            check_names(source.parent, [source.name])
        if source.is_dir():
            def on_error(error: OSError) -> None:
                raise error
            for root, directories, files in os.walk(source, onerror=on_error, followlinks=False):
                check_names(Path(root), directories + files)


def _validate_outputs(tasks: list[TaskPlan], sources: tuple[Path, ...]) -> None:
    """按计划中的实际路径校验来源与各任务、各层之间的冲突。"""
    used_paths = {str(source).casefold() for source in sources}
    for task in tasks:
        if str(task.output_directory).casefold() in used_paths:
            raise ConfigError("输出目录与来源或压缩层冲突：请调整 output_directory")
        for index, layer in enumerate(task.layers):
            paths = (layer.destination, *layer.output_paths())
            for path in paths:
                if str(path).casefold() in used_paths:
                    raise ConfigError(
                        f"layers[{index}].archive_name 会覆盖原始输入或其他压缩层（{path}）"
                    )
            used_paths.update(str(path).casefold() for path in paths)


def build_compression_plan(
    config: AppConfig, config_path: Path | None = None
) -> CompressionPlan:
    """解析运行环境，按打包方式生成并校验全部任务。"""
    config = parse_config(config.to_json_dict())
    if config.delete_inner_after_verify and not config.verify_after_compress:
        raise ConfigError(
            "delete_inner_after_verify 必须与 verify_after_compress 一起启用；"
            "未自检就删除上一层会导致中间数据无法恢复"
        )
    config_path = config_path.resolve() if config_path is not None else None
    config_directory = config_path.parent if config_path is not None else Path.cwd()
    sources = _resolve_sources(config, config_directory)
    groups = source_layer_groups(config, config_directory)
    tools = _resolve_tools(config, config_directory, {
        layer.format for _, layers in groups for layer in layers
    })
    output_directory = normalize_user_path(config.output_directory, config_directory)
    separate = config.compress_mode == COMPRESS_MODE_SEPARATE
    seen_stems: set[str] = set()
    checked: set[Path] = set()
    resources: set[Path] = set()
    sfx_warnings: list[str] = []
    tasks: list[TaskPlan] = []
    for task_sources, configs in groups:
        source = task_sources[0]
        task_output = output_directory
        if separate:
            stem = source.stem.casefold()
            if stem in seen_stems:
                raise ConfigError(f"多个来源去除后缀后同名：{source.name}，请区分来源名称")
            seen_stems.add(stem)
            task_output = (output_directory / source.stem).resolve()
        sfx_plans: dict[int, SfxPlan] = {}
        videos: dict[int, Path] = {}
        for index, layer in enumerate(configs):
            if layer.sfx.enabled:
                sfx = resolve_sfx(layer.sfx, tools[FORMAT_RAR], config_directory)
                sfx_plans[index] = sfx
                resources.update(sfx.resources)
                if index == 0 and layer.sfx.target == "windows":
                    _validate_windows_sources(task_sources, config.hide_source_name)
                if layer.sfx.setup and (config.hide_source_name or config.randomize_layer_names):
                    sfx_warnings.append(
                        f"{source.name} 第 {index + 1} 层启动命令按原文写入；"
                        "随机改名后请确认命令中的文件路径。"
                    )
            disguise = layer.disguise
            if disguise.mode == "video":
                overrides = {normalize_user_path(path, config_directory): video
                             for path, video in disguise.source_video_paths.items()}
                raw_video = (overrides.get(source) if separate else "") or disguise.video_path
                if not raw_video:
                    raise ConfigError(f"{source.name} 第 {index + 1} 层请选择载体视频")
                video = normalize_user_path(raw_video, config_directory)
                if video not in checked:
                    validate_video(video)
                    checked.add(video)
                videos[index] = video
        if sfx_plans and config.add_padding:
            sfx_warnings.append("原生自解压会一并释放随机填充文件；NestPack 解包会清理填充文件。")
        tasks.append(_plan_task(configs, task_sources, task_output, tools, videos, sfx_plans))

    protected_inputs = (*sources, *checked, *resources)
    _validate_outputs(tasks, protected_inputs)
    for task in tasks:
        ancestor = task.output_directory
        while not ancestor.exists():
            ancestor = ancestor.parent
        if not ancestor.is_dir():
            raise ConfigError(f"输出目录或其父路径不是文件夹：{ancestor}")
        for planned in task.layers:
            check_output_paths(
                existing_outputs(planned), config.overwrite_existing, protected_inputs,
            )

    return CompressionPlan(
        config=config,
        config_path=config_path,
        output_directory=output_directory,
        tasks=tuple(tasks),
        winrar=tools.get(FORMAT_RAR),
        sevenzip=tools.get(FORMAT_7Z),
        warnings=(*dict.fromkeys(sfx_warnings), *disk_warnings(
            config, list(sources), output_directory,
            layer_count=max(len(task.layers) for task in tasks),
            video_bytes=sum(layer.video.stat().st_size for task in tasks for layer in task.layers
                            if layer.video is not None),
        )),
    )
