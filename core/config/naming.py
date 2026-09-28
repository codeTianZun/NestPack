"""为待执行的任务配置生成随机层名。"""

from __future__ import annotations

import random
import string
from dataclasses import replace
from pathlib import Path

from core.models import COMPRESS_MODE_SEPARATE, AppConfig, LayerConfig
from core.naming import archive_extension
from core.source_layers import source_layer_groups

RANDOM_NAME_CHARS = string.ascii_lowercase + string.digits


def randomized_layer_names(config: AppConfig, config_dir: Path | None = None) -> AppConfig:
    """为各层生成 8 位随机主名并附上格式后缀，返回更新后的配置。"""
    used_names = {
        Path(path).name.casefold() for path in config.effective_source_paths()
    }

    def random_name(layer: LayerConfig) -> str:
        while True:
            name = "".join(random.choices(RANDOM_NAME_CHARS, k=8))
            if name.casefold() not in used_names:
                break
        used_names.add(name)
        return name + archive_extension(layer)

    def randomize(layers: list[LayerConfig]) -> list[LayerConfig]:
        return [replace(layer, archive_name=random_name(layer), auto_name=False)
                for layer in layers]

    if config.compress_mode == COMPRESS_MODE_SEPARATE:
        return replace(config, source_layers={
            str(sources[0]): randomize(layers)
            for sources, layers in source_layer_groups(config, config_dir or Path.cwd())
        })
    return replace(config, layers=randomize(config.layers))
