"""配置入口：加载、保存、随机层名与界面共用的字段校验。"""

from .naming import randomized_layer_names
from .schema import parse_config
from .storage import load_config, save_config
from .validation import (
    DISGUISE_EXTENSION_PATTERN,
    VOLUME_SIZE_PATTERN,
    validate_archive_name,
    validate_disguise_extension,
    validate_password,
    validate_volume_size,
)

__all__ = [
    "DISGUISE_EXTENSION_PATTERN",
    "VOLUME_SIZE_PATTERN",
    "load_config",
    "parse_config",
    "randomized_layer_names",
    "save_config",
    "validate_archive_name",
    "validate_disguise_extension",
    "validate_password",
    "validate_volume_size",
]
