"""CLI 配置组装、路径基准与密码文件读取。"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from cli.args import BOOLEAN_OPTIONS
from core.config import load_config, parse_config, save_config
from core.filesystem import normalize_user_path
from core.models import DEFAULT_CONFIG_PATH, AppConfig, ConfigError, LayerConfig


def read_utf8_text(path: Path, label: str) -> str:
    """读取用户文本，把编码与文件错误转换为可操作的提示。"""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeError as error:
        raise ConfigError(f"{label}编码无效：{path}；请以 UTF-8 编码保存") from error
    except OSError as error:
        raise ConfigError(f"无法读取{label}：{path}；{error}") from error


def read_password_file(path: Path) -> list[str]:
    """逐行读取候选密码，保留密码中的空白字符。"""
    return [
        line.removesuffix("\r")
        for line in read_utf8_text(path, "密码文件").split("\n")
        if line.removesuffix("\r") != ""
    ]


def read_layer_password(path: Path) -> str:
    """读取单层密码文件，允许一个末尾换行，密码本身保持原样。"""
    value = read_utf8_text(path, "密码文件")
    if value.endswith("\n"):
        value = value[:-1].removesuffix("\r")
    if "\n" in value or "\r" in value:
        raise ConfigError(f"单层密码文件必须只有一行：{path}")
    return value


def new_config(sources: list[Path] | None = None) -> AppConfig:
    """新建任务的共用默认设置，路径由入口收集。"""
    paths = sources or []
    stem = paths[0].stem if paths else "archive"
    return AppConfig(
        winrar_path="auto",
        source_path=str(paths[0]) if paths else "",
        source_paths=[str(path) for path in paths],
        output_directory="",
        overwrite_existing=False,
        confirm_before_start=False,
        show_winrar_gui=False,
        layers=[LayerConfig(f"{stem}_1.rar", "", None, name_template="{stem}_1")],
    )


def validate_config(config: AppConfig) -> AppConfig:
    """让向导和直接参数使用与 JSON 加载相同的字段校验。"""
    return parse_config(config.to_json_dict())


def absolute_config(config: AppConfig, config_path: Path | None) -> AppConfig:
    """将任务路径固定为绝对路径，使另存配置不改变输入输出位置。"""
    base = config_path.parent if config_path is not None else Path.cwd()
    sources = [str(normalize_user_path(value, base)) for value in config.effective_source_paths()]

    def tool_path(value: str) -> str:
        return "auto" if value.strip().lower() == "auto" else str(normalize_user_path(value, base))

    return replace(
        config,
        source_path=sources[0] if sources else "",
        source_paths=sources,
        output_directory=str(normalize_user_path(config.output_directory, base))
        if config.output_directory
        else "",
        winrar_path=tool_path(config.winrar_path),
        sevenzip_path=tool_path(config.sevenzip_path),
    )


def write_task_config(path: Path, config: AppConfig, config_path: Path | None) -> None:
    """保存当前任务的路径快照，并应用密码持久化设置。"""
    snapshot = absolute_config(config, config_path)
    if path.resolve() in (Path(value) for value in snapshot.effective_source_paths()):
        raise ConfigError("配置保存路径与原始来源冲突，请选择其他配置文件名")
    save_config(path, snapshot if snapshot.persist_passwords else snapshot.without_passwords())


def _layer_from_options(spec: dict, index: int, stem: str) -> dict:
    archive_format = spec["format"]
    raw = LayerConfig(
        f"{stem}_{index}.{archive_format}",
        "",
        None,
        format=archive_format,
        name_template=f"{{stem}}_{index}",
    ).to_json_dict()
    values = dict(spec)
    if "password_file" in values:
        if "password" in values:
            raise ConfigError(
                f"第 {index} 层的 --layer-password 与 --layer-password-file 只能选一个"
            )
        raw["password"] = read_layer_password(normalize_user_path(values.pop("password_file")))
    if "archive_name" in values:
        raw["name_template"] = None
    if "compression_level" in values and values["compression_level"] != "auto":
        try:
            values["compression_level"] = int(values["compression_level"])
        except ValueError as error:
            raise ConfigError(f"第 {index} 层 --layer-level 必须为 auto 或 0–5") from error
    if "recovery_percent" in values:
        try:
            percent = int(values.pop("recovery_percent"))
        except ValueError as error:
            raise ConfigError(f"第 {index} 层 --layer-recovery 必须为 1–100 的整数") from error
        raw["recovery_record"] = {"enabled": True, "percent": percent}
    raw.update(values)
    raw["password_set"] = bool(raw["password"])
    return raw


def configuration_from_arguments(arguments: argparse.Namespace) -> tuple[AppConfig, Path | None]:
    """读取配置并应用本次参数，或直接从来源与层参数构建任务。"""
    if arguments.source is not None and any(not value.strip() for value in arguments.source):
        raise ConfigError("--source 路径不能为空")
    config_path = (
        normalize_user_path(str(arguments.config)) if arguments.config is not None else None
    )
    if config_path is None and arguments.source is None:
        config_path = DEFAULT_CONFIG_PATH
    if config_path is not None:
        if not config_path.is_file():
            raise ConfigError(
                f"未找到配置文件：{config_path}；可无参数打开菜单，"
                "或使用 --source 来源 --output 目录 --layer rar 直接创建任务"
            )
        config = load_config(config_path)
    else:
        config = new_config([normalize_user_path(value) for value in arguments.source])
    raw = config.to_json_dict()
    if arguments.source is not None:
        raw["source_paths"] = [str(normalize_user_path(value)) for value in arguments.source]
        raw["source_path"] = raw["source_paths"][0]
    if arguments.output is not None:
        raw["output_directory"] = str(normalize_user_path(str(arguments.output)))
    for field in (
        "compress_mode",
        "winrar_path",
        "sevenzip_path",
        "disguise_extension",
        *BOOLEAN_OPTIONS,
    ):
        value = getattr(arguments, field)
        if value is not None:
            if field in ("winrar_path", "sevenzip_path") and value.strip().lower() != "auto":
                value = str(normalize_user_path(value))
            raw[field] = value
    if arguments.disguise_extension is not None and arguments.disguise_outer_extension is None:
        raw["disguise_outer_extension"] = True
    if arguments.layer_specs is not None:
        stem = Path(raw["source_path"]).stem or "archive"
        raw["layers"] = [
            _layer_from_options(spec, index, stem)
            for index, spec in enumerate(arguments.layer_specs, start=1)
        ]
    return parse_config(raw), config_path
