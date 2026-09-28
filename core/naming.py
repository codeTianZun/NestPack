"""层名称与产物路径：配置编辑、预览和压缩计划共用的命名规则。"""

from pathlib import Path

from core.backends import get_backend
from core.models import LayerConfig


def archive_extension(layer: LayerConfig) -> str:
    """返回本层归档或自解压的后缀。"""
    return layer.sfx.extension if layer.sfx.enabled else get_backend(layer.format).archive_extension


def default_archive_name(stem: str, number: int, extension: str) -> str:
    """按来源主名和当前层号生成默认名称。"""
    return f"{stem}_{number}{extension}"


def replace_archive_extension(name: str, extension: str) -> str:
    """切换格式时替换已有归档后缀，保留自定义主名。"""
    if Path(name).suffix.lower() in (".rar", ".7z", ".zip", ".exe", ".sfx"):
        return str(Path(name).with_suffix(extension))
    return name


def resolve_archive_name(layer: LayerConfig, number: int, source: Path) -> str:
    """按当前来源与层号展开自动名称，手动名称保持原值。"""
    if layer.auto_name:
        return default_archive_name(source.stem, number, archive_extension(layer))
    return layer.archive_name


def layer_output_paths(
    layer: LayerConfig, destination: Path, volume_count: int = 1,
) -> tuple[Path, ...]:
    """按格式、分卷和伪装生成产物路径；预览使用第一卷。"""
    if layer.disguise.mode == "video":
        return (destination.with_suffix(".mp4"),)
    backend = get_backend(layer.format)
    paths = (
        backend.volume_final_names(destination, volume_count)
        if layer.volume_size else [destination]
    )
    if layer.disguise.mode == "extension":
        extension = layer.disguise.extension
        if layer.sfx.enabled and extension.casefold() in (".exe", ".sfx"):
            paths[0] = backend.disguise_name(paths[0], extension)
        else:
            paths = [backend.disguise_name(path, extension) for path in paths]
    return tuple(paths)
