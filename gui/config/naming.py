"""无需归档工具即可生成的最终输出路径预览。"""

from pathlib import Path

from core.config import validate_archive_name
from core.filesystem import normalize_user_path
from core.models import COMPRESS_MODE_SEPARATE, LayerConfig
from core.naming import archive_extension, layer_output_paths, resolve_archive_name


def output_preview(
    layers: list[LayerConfig], sources: list[str], mode: str,
    output: str, config_dir: Path, *, random_names: bool,
) -> tuple[list[tuple[str, str]], str]:
    """逐任务显示最外层实际路径；随机名称以待生成占位表示。"""
    if not sources:
        return [], "添加来源后显示最终输出路径"
    if not layers:
        return [], "添加压缩层后显示最终输出路径"
    if not output:
        return [], "选择输出目录后显示最终输出路径"
    outer = layers[-1]
    separate = mode == COMPRESS_MODE_SEPARATE
    directory = normalize_user_path(output, config_dir)
    paths = [normalize_user_path(source, config_dir) for source in sources]
    rows: list[tuple[str, str]] = []
    for source in paths if separate else paths[:1]:
        title = source.name if separate else f"合并打包（{len(paths)} 个来源）"
        try:
            name = (
                "{随机名称}" + archive_extension(outer) if random_names else
                resolve_archive_name(outer, len(layers), source)
            )
            name = validate_archive_name(
                name, outer.format,
                sfx_extension=outer.sfx.extension if outer.sfx.enabled else None,
            )
            destination = directory / source.stem / name if separate else directory / name
            rows.append((title, str(layer_output_paths(outer, destination)[0])))
        except ValueError as error:
            rows.append((title, f"文件名待完善：{error}"))
    hints = ["每个来源输出一套" if separate else "全部来源合并输出一套"]
    if outer.volume_size:
        hints.append("分卷预览显示第一卷")
    if random_names:
        hints.append("执行时将重新生成名称并覆盖已填写的名称")
    return rows, "；".join(hints)
