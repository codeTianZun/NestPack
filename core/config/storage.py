"""JSON 配置的 UTF-8 读取、错误转换与原子保存。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.filesystem import atomic_write_text
from core.models import AppConfig, ConfigError

from .schema import parse_config


def _read_config_json(config_path: Path) -> dict[str, Any]:
    """读取并解析 JSON，把可预见的格式问题转成 ConfigError。"""
    try:
        raw_config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except UnicodeError as error:
        raise ConfigError(f"配置文件编码无效：{config_path}；请以 UTF-8 编码保存") from error
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"JSON 格式错误：第 {error.lineno} 行，第 {error.colno} 列，{error.msg}"
        ) from error
    except OSError as error:
        raise ConfigError(f"无法读取配置文件：{error}") from error
    if not isinstance(raw_config, dict):
        raise ConfigError("配置文件最外层必须是 JSON 对象")
    return raw_config


def save_config(config_path: Path, config: AppConfig) -> None:
    """以 UTF-8 和易读缩进保存 JSON，便于人工或 GUI 修改。"""
    content = json.dumps(config.to_json_dict(), ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(config_path, content)


def load_config(config_path: Path, *, allow_incomplete: bool = False) -> AppConfig:
    """读取 JSON 文件，并把所有可预见的格式问题转成 ConfigError。

    allow_incomplete=True 时允许 source_path / output_directory 为空、
    winrar_path 可填空字符串并按 auto 解析，用于 GUI 载入草稿配置。
    """
    return parse_config(_read_config_json(config_path), allow_incomplete=allow_incomplete)
