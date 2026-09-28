"""压缩计划构建：解析工具与来源、展开层名并校验任务的输出位置。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from core.backends import get_backend
from core.config import validate_archive_name
from core.filesystem import normalize_user_path
from core.models import (
    COMPRESS_MODE_SEPARATE,
    FORMAT_7Z,
    FORMAT_RAR,
    FORMAT_ZIP,
    AppConfig,
    ConfigError,
)
from core.video import validate_video
from platforms import get_archive_platform

from .models import CompressionPlan, LayerPlan, TaskPlan
from .outputs import check_output_paths, existing_outputs
from .preflight import disk_warnings


def _resolve_tools(config: AppConfig, config_directory: Path) -> dict[str, Path]:
    """只解析本次使用的工具；7z 与 ZIP 共用同一可执行文件。"""
    used_formats = {layer.format for layer in config.layers}
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
    config: AppConfig,
    sources: tuple[Path, ...],
    output_directory: Path,
    tools: dict[str, Path],
    video: Path | None = None,
) -> TaskPlan:
    """确定一套嵌套压缩包的层参数与输出命名。"""
    layers: list[LayerPlan] = []
    for index, layer in enumerate(config.layers):
        name = layer.archive_name
        try:
            if config.compress_mode == COMPRESS_MODE_SEPARATE and layer.name_template:
                name = (
                    layer.name_template.format(stem=sources[0].stem)
                    + get_backend(layer.format).archive_extension
                )
            name = validate_archive_name(name, layer.format)
        except (KeyError, IndexError, AttributeError, ValueError) as error:
            raise ConfigError(
                f"layers[{index}] 的层名无效（来源：{sources[0].name}）：{error}"
            ) from error
        layers.append(
            LayerPlan(
                config=replace(layer, archive_name=name),
                tool=tools[layer.format],
                destination=(output_directory / name).resolve(),
                video=video if index == len(config.layers) - 1 else None,
                disguise_extension=(
                    config.disguise_extension
                    if config.disguise_outer_extension and index == len(config.layers) - 1
                    else None
                ),
            )
        )
    return TaskPlan(sources=sources, output_directory=output_directory, layers=tuple(layers))


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
    if config.delete_inner_after_verify and not config.verify_after_compress:
        raise ConfigError(
            "delete_inner_after_verify 必须与 verify_after_compress 一起启用；"
            "未自检就删除上一层会导致中间数据无法恢复"
        )
    config_path = config_path.resolve() if config_path is not None else None
    config_directory = config_path.parent if config_path is not None else Path.cwd()
    tools = _resolve_tools(config, config_directory)
    sources = _resolve_sources(config, config_directory)
    output_directory = normalize_user_path(config.output_directory, config_directory)
    videos: dict[Path, Path] = {}
    if config.video_fusion:
        if config.layers[-1].volume_size:
            raise ConfigError("视频融合的最外层应为单文件归档，请将分卷设置放在内部压缩层。")
        overrides = {
            normalize_user_path(source, config_directory): video
            for source, video in config.source_video_paths.items()
        }
        checked: set[Path] = set()
        for source in sources:
            raw_video = config.video_path
            if config.compress_mode == COMPRESS_MODE_SEPARATE:
                raw_video = overrides.get(source, "") or raw_video
            if not raw_video:
                raise ConfigError(f"请为视频融合选择默认视频或来源专用视频：{source}")
            video = normalize_user_path(raw_video, config_directory)
            if video not in checked:
                validate_video(video)
                checked.add(video)
            videos[source] = video

    tasks: list[TaskPlan] = []
    if config.compress_mode == COMPRESS_MODE_SEPARATE:
        seen_stems: set[str] = set()
        for source in sources:
            stem = source.stem.casefold()
            if stem in seen_stems:
                raise ConfigError(f"多个来源去除后缀后同名：{source.name}，请区分来源名称")
            seen_stems.add(stem)
            task_output = (output_directory / source.stem).resolve()
            tasks.append(_plan_task(config, (source,), task_output, tools, videos.get(source)))
    else:
        tasks.append(_plan_task(config, sources, output_directory, tools, videos.get(sources[0])))

    protected_inputs = (*sources, *videos.values())
    _validate_outputs(tasks, protected_inputs)
    for task in tasks:
        ancestor = task.output_directory
        while not ancestor.exists():
            ancestor = ancestor.parent
        if not ancestor.is_dir():
            raise ConfigError(f"输出目录或其父路径不是文件夹：{ancestor}")
        for layer in task.layers:
            check_output_paths(existing_outputs(layer), config.overwrite_existing, protected_inputs)

    return CompressionPlan(
        config=config,
        config_path=config_path,
        output_directory=output_directory,
        tasks=tuple(tasks),
        winrar=tools.get(FORMAT_RAR),
        sevenzip=tools.get(FORMAT_7Z),
        warnings=disk_warnings(
            config, list(sources), output_directory,
            video_bytes=sum(task.layers[-1].video.stat().st_size for task in tasks
                            if task.layers[-1].video is not None),
        ),
    )
