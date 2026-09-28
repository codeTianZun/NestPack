"""配置字段校验：类型、归档文件名与单层参数。"""

from __future__ import annotations

import re
from typing import Any

from core.backends import SUPPORTED_FORMATS, get_backend
from core.models import (
    COMPRESSION_AUTO,
    COMPRESSION_LEVEL_MAX,
    COMPRESSION_LEVEL_MIN,
    FORMAT_RAR,
    FORMAT_ZIP,
    ConfigError,
    DisguiseConfig,
    LayerConfig,
)
from platforms import get_archive_platform

from .sfx import parse_sfx_config

# 分卷大小的写法：数字加可选单位，如 500k / 100m / 1g / 1048576。
VOLUME_SIZE_PATTERN = re.compile(r"\d+(?:\.\d+)?[bBkKmMgG]?")

# 伪装扩展名：以点开头的 1-8 个字母或数字，如 .bin、.dat、.pdf。
DISGUISE_EXTENSION_PATTERN = re.compile(r"^\.[0-9A-Za-z]{1,8}$")


def validate_archive_name(
    raw_name: str, archive_format: str = FORMAT_RAR, *, sfx_extension: str | None = None,
) -> str:
    """校验层文件名并按归档格式或自解压交付目标补充扩展名。"""
    name = get_archive_platform().validate_filename(raw_name)
    extension = sfx_extension or get_backend(archive_format).archive_extension
    if sfx_extension and name.lower().endswith(".rar"):
        name = name[:-4]
    if not name.lower().endswith(extension):
        name += extension
    return name


def validate_password(password: str, archive_format: str) -> None:
    """校验归档工具对密码字符的限制。"""
    if archive_format == FORMAT_ZIP and not password.isascii():
        raise ValueError(
            "zip 层的密码仅支持 ASCII 字符（7-Zip 限制），"
            "请改用英文数字密码，或换 rar / 7z 格式"
        )
    if password.startswith("-"):
        raise ValueError(
            "密码不能以 - 开头（会被归档工具误判为命令行开关），请调整密码"
        )


def validate_volume_size(value: str) -> None:
    """校验非空的分卷大小输入。"""
    if not VOLUME_SIZE_PATTERN.fullmatch(value):
        raise ValueError("分卷大小必须是数字加可选单位（如 500k、100m、1g）")


def validate_disguise_extension(value: str) -> None:
    """校验层产物的伪装扩展名。"""
    if not DISGUISE_EXTENSION_PATTERN.fullmatch(value):
        raise ValueError("伪装扩展名必须是以点开头的 1-8 位字母数字（如 .bin、.dat）")


def require_string(data: dict[str, Any], key: str, location: str) -> str:
    """从 JSON 对象读取非空字符串，并给出清晰的字段错误。"""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{location}.{key} 必须是非空字符串")
    return value


def require_boolean(data: dict[str, Any], key: str, location: str) -> bool:
    """严格读取 JSON 布尔值，避免字符串 true/false 被误接受。"""
    value = data.get(key)
    if not isinstance(value, bool):
        raise ConfigError(f"{location}.{key} 必须是 true 或 false")
    return value


def optional_boolean(
    data: dict[str, Any],
    key: str,
    location: str,
    default: bool,
) -> bool:
    """读取可缺省的 JSON 布尔值，旧配置没有该字段时返回默认值。"""
    if key not in data:
        return default
    return require_boolean(data, key, location)


def parse_compression_level(raw_value: Any, location: str) -> str | int:
    """校验压缩级别：必须是 "auto" 或 0-5 的整数。"""
    if raw_value == COMPRESSION_AUTO:
        return COMPRESSION_AUTO
    if type(raw_value) is int and (
        COMPRESSION_LEVEL_MIN <= raw_value <= COMPRESSION_LEVEL_MAX
    ):
        return raw_value
    raise ConfigError(
        f"{location}.compression_level 必须是 \"auto\" "
        f"或 {COMPRESSION_LEVEL_MIN} 到 {COMPRESSION_LEVEL_MAX} 的整数"
    )


def parse_disguise_config(raw: Any, location: str, *, strict: bool) -> DisguiseConfig:
    """读取逐层伪装设置；草稿保留扩展名的未完成输入。"""
    if not isinstance(raw, dict):
        raise ConfigError(f"{location} 必须是 JSON 对象")
    mode = raw.get("mode", "none")
    if mode not in ("none", "extension", "video"):
        raise ConfigError(f"{location}.mode 必须是 none、extension 或 video")
    extension = raw.get("extension", ".bin")
    video = raw.get("video_path", "")
    overrides = raw.get("source_video_paths", {})
    if not isinstance(extension, str):
        raise ConfigError(f"{location}.extension 必须是字符串")
    if not isinstance(video, str):
        raise ConfigError(f"{location}.video_path 必须是字符串")
    if not isinstance(overrides, dict) or not all(
        isinstance(source, str) and isinstance(path, str) for source, path in overrides.items()
    ):
        raise ConfigError(f"{location}.source_video_paths 必须是来源路径到视频路径的对象")
    if strict and mode == "extension":
        try:
            validate_disguise_extension(extension.strip())
        except ValueError as error:
            raise ConfigError(f"{location}.extension：{error}") from error
    return DisguiseConfig(
        mode=mode, extension=extension.strip(), video_path=video.strip(),
        source_video_paths={source: path.strip() for source, path in overrides.items()},
    )


def parse_layer_config(
    raw_layer: Any,
    layer_index: int,
    *,
    strict: bool = True,
    separate: bool = False,
) -> LayerConfig:
    """解析并验证 layers 数组中的一项。

    strict=False 用于 GUI 载入草稿，保留文件名、密码和分卷大小的未完成
    输入及自解压的组合冲突；字段类型始终校验。
    """
    location = f"layers[{layer_index}]"
    if not isinstance(raw_layer, dict):
        raise ConfigError(f"{location} 必须是 JSON 对象")

    archive_format = raw_layer.get("format", FORMAT_RAR)
    if archive_format not in SUPPORTED_FORMATS:
        raise ConfigError(
            f"{location}.format 必须是 "
            f"{' 或 '.join(repr(name) for name in SUPPORTED_FORMATS)}"
        )

    sfx = parse_sfx_config(raw_layer.get("sfx", {}), strict=strict)
    if strict and sfx.enabled and archive_format != FORMAT_RAR:
        raise ConfigError(f"{location}.sfx：自解压适用于 RAR 层，请调整格式或关闭自解压")

    auto_name = optional_boolean(raw_layer, "auto_name", location, False)
    if strict and not separate and not auto_name:
        try:
            archive_name = validate_archive_name(
                require_string(raw_layer, "archive_name", location),
                archive_format,
                sfx_extension=sfx.extension if sfx.enabled else None,
            )
        except ValueError as error:
            raise ConfigError(f"{location}.archive_name 无效：{error}") from error
    else:
        raw_name = raw_layer.get("archive_name", "")
        if not isinstance(raw_name, str):
            raise ConfigError(f"{location}.archive_name 必须是字符串")
        archive_name = raw_name.strip()

    password = raw_layer.get("password", "")
    if not isinstance(password, str):
        raise ConfigError(f"{location}.password 必须是字符串")
    if strict:
        try:
            validate_password(password, archive_format)
        except ValueError as error:
            raise ConfigError(f"{location}.password：{error}") from error

    recovery = raw_layer.get("recovery_record")
    if not isinstance(recovery, dict):
        raise ConfigError(f"{location}.recovery_record 必须是 JSON 对象")

    enabled = require_boolean(recovery, "enabled", f"{location}.recovery_record")
    percent = recovery.get("percent", 3)
    if type(percent) is not int or not 1 <= percent <= 100:
        raise ConfigError(
            f"{location}.recovery_record.percent 必须是 1 到 100 的整数"
        )
    if enabled and archive_format != FORMAT_RAR:
        raise ConfigError(
            f"{location}.recovery_record：{archive_format} 格式没有恢复记录，"
            "请关闭该选项或改用 rar 格式"
        )

    compression_level = parse_compression_level(
        raw_layer.get("compression_level", COMPRESSION_AUTO),
        location,
    )

    volume_size = raw_layer.get("volume_size")
    if volume_size is None or (
        isinstance(volume_size, str) and not volume_size.strip()
    ):
        volume_size = None
    elif not isinstance(volume_size, str):
        raise ConfigError(f"{location}.volume_size 必须是字符串或 null")
    else:
        volume_size = volume_size.strip()
        if strict:
            try:
                validate_volume_size(volume_size)
            except ValueError as error:
                raise ConfigError(f"{location}.volume_size：{error}") from error

    password_set = optional_boolean(
        raw_layer, "password_set", location, default=bool(password)
    )

    disguise = parse_disguise_config(
        raw_layer.get("disguise", {}), f"{location}.disguise", strict=strict,
    )
    if strict:
        if disguise.mode == "video" and volume_size:
            raise ConfigError(f"{location}：视频伪装需要单文件归档，请关闭本层分卷")
        if disguise.mode == "video" and sfx.enabled:
            raise ConfigError(f"{location}：视频伪装与本层自解压互斥，请选择其中一种")
        if (sfx.enabled and sfx.target == "windows" and disguise.mode == "extension"
                and disguise.extension.casefold() != ".exe"):
            raise ConfigError(f"{location}：Windows 自解压需要 .exe 后缀")

    return LayerConfig(
        archive_name=archive_name,
        password=password,
        recovery_percent=percent if enabled else None,
        format=archive_format,
        compression_level=compression_level,
        auto_name=auto_name,
        volume_size=volume_size,
        password_set=password_set,
        sfx=sfx,
        disguise=disguise,
    )
