"""默认层与来源独立层的选择，供 GUI、CLI 和压缩计划共用。"""

from dataclasses import replace
from pathlib import Path

from core.filesystem import normalize_user_path
from core.models import COMPRESS_MODE_SEPARATE, AppConfig, LayerConfig


def default_source_layers(
    layers: list[LayerConfig], source: Path, config_dir: Path,
) -> list[LayerConfig]:
    """为来源展开默认层，名称自动生成，载体采用该来源的有效选择。"""
    result = []
    for layer in layers:
        videos = {
            normalize_user_path(path, config_dir): video
            for path, video in layer.disguise.source_video_paths.items()
        }
        result.append(replace(
            layer, archive_name="", auto_name=True,
            disguise=replace(layer.disguise, source_video_paths={},
                             video_path=videos.get(source) or layer.disguise.video_path),
        ))
    return result


def source_layer_groups(
    config: AppConfig, config_dir: Path,
) -> list[tuple[tuple[Path, ...], list[LayerConfig]]]:
    """按当前打包方式返回各任务实际使用的来源和压缩层。"""
    sources = tuple(normalize_user_path(path, config_dir)
                    for path in config.effective_source_paths())
    if config.compress_mode != COMPRESS_MODE_SEPARATE:
        return [(sources, config.layers)]
    overrides = {normalize_user_path(path, config_dir): layers
                 for path, layers in config.source_layers.items()}
    return [((source,), overrides[source] if source in overrides else
             default_source_layers(config.layers, source, config_dir)) for source in sources]
