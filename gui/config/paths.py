"""界面路径选择的起始目录；路径展开复用核心的配置目录规则。"""

from dataclasses import replace
from pathlib import Path

from core.filesystem import normalize_user_path
from core.models import AppConfig


def selection_directory(value: str, config_dir: Path) -> Path:
    """已有目录直接打开，文件或待创建路径从父目录开始选择。"""
    if not value.strip() or value.strip().lower() == "auto":
        return config_dir
    path = normalize_user_path(value, config_dir)
    return path if path.is_dir() else path.parent


def freeze_config_paths(config: AppConfig, config_dir: Path) -> AppConfig:
    """另存时固定本机路径，保持来源、输出、工具与素材的解析位置。"""
    def local_path(value: str) -> str:
        return str(normalize_user_path(value, config_dir)) if value.strip() else value

    def tool_path(value: str) -> str:
        return "auto" if value.strip().lower() == "auto" else local_path(value)

    sources = [local_path(value) for value in config.effective_source_paths()]
    return replace(
        config,
        source_path=sources[0] if sources else "",
        source_paths=sources,
        output_directory=local_path(config.output_directory),
        winrar_path=tool_path(config.winrar_path),
        sevenzip_path=tool_path(config.sevenzip_path),
        video_path=local_path(config.video_path),
        source_video_paths={
            local_path(source): local_path(video)
            for source, video in config.source_video_paths.items()
        },
        layers=[replace(layer, sfx=replace(
            layer.sfx,
            template_path=tool_path(layer.sfx.template_path),
            icon_path=local_path(layer.sfx.icon_path),
            logo_path=local_path(layer.sfx.logo_path),
        )) for layer in config.layers],
    )
