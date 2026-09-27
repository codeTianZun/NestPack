"""为待执行的任务配置生成随机层名。"""

from __future__ import annotations

import random
import string
from dataclasses import replace
from pathlib import Path

from core.backends import get_backend
from core.models import AppConfig, LayerConfig

RANDOM_NAME_CHARS = string.ascii_lowercase + string.digits


def randomized_layer_names(config: AppConfig) -> AppConfig:
    """把各层文件名替换为 8 位随机名。

    randomize_layer_names 开启时由 CLI 与 GUI 在开始压缩前调用，
    随机名会随配置写回磁盘。
    """
    used_names = {
        Path(path).name.casefold() for path in config.effective_source_paths()
    }
    layers: list[LayerConfig] = []
    for layer in config.layers:
        while True:
            name = "".join(random.choices(RANDOM_NAME_CHARS, k=8))
            if name.casefold() not in used_names:
                break
        used_names.add(name)
        layers.append(
            replace(
                layer,
                archive_name=f"{name}{get_backend(layer.format).archive_extension}",
                name_template=None,
            )
        )
    return replace(config, layers=layers)
