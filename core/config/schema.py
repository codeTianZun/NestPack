"""任务配置文档解析：版本、来源、路径字段与缺省值。"""

from __future__ import annotations

from typing import Any

from core.models import (
    COMPRESS_MODE_COMBINED,
    COMPRESS_MODE_SEPARATE,
    CONFIG_VERSION,
    AppConfig,
    ConfigError,
    LayerConfig,
)

from .validation import (
    optional_boolean,
    parse_layer_config,
    require_boolean,
    require_string,
    validate_disguise_extension,
)


def parse_source_paths(raw_config: dict[str, Any], *, strict: bool) -> list[str]:
    """解析来源列表；旧配置只有 source_path 时回退为单来源。"""
    value = raw_config.get("source_paths")
    if value is not None:
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise ConfigError("配置.source_paths 必须是字符串数组")
        paths = [item.strip() for item in value if item.strip()]
        if paths:
            return paths
    legacy = raw_config.get("source_path")
    if isinstance(legacy, str) and legacy.strip():
        return [legacy.strip()]
    if strict:
        raise ConfigError("配置.source_path 必须是非空字符串")
    return []


def _parse_path_fields(
    raw_config: dict[str, Any], *, allow_incomplete: bool
) -> tuple[str, str, str]:
    """解析 winrar_path、sevenzip_path 与 output_directory；草稿模式允许留空。"""
    sevenzip_raw = raw_config.get("sevenzip_path")
    if sevenzip_raw is not None and not isinstance(sevenzip_raw, str):
        raise ConfigError("配置.sevenzip_path 必须是字符串")
    sevenzip_path = (
        sevenzip_raw.strip() or "auto" if isinstance(sevenzip_raw, str) else "auto"
    )
    if allow_incomplete:
        winrar_path = raw_config.get("winrar_path")
        output_directory = raw_config.get("output_directory")
        if not isinstance(winrar_path, str):
            raise ConfigError("配置.winrar_path 必须是字符串")
        if not isinstance(output_directory, str):
            raise ConfigError("配置.output_directory 必须是字符串")
        return winrar_path.strip() or "auto", sevenzip_path, output_directory.strip()
    return (
        require_string(raw_config, "winrar_path", "配置"),
        sevenzip_path,
        require_string(raw_config, "output_directory", "配置"),
    )


def _parse_compress_mode_field(raw_config: dict[str, Any]) -> str:
    compress_mode = raw_config.get("compress_mode", COMPRESS_MODE_COMBINED)
    if compress_mode not in (COMPRESS_MODE_COMBINED, COMPRESS_MODE_SEPARATE):
        raise ConfigError(
            "配置.compress_mode 必须是 "
            f"'{COMPRESS_MODE_COMBINED}' 或 '{COMPRESS_MODE_SEPARATE}'"
        )
    return compress_mode


def _parse_disguise_extension_field(raw_config: dict[str, Any], *, strict: bool) -> str:
    disguise_extension = raw_config.get("disguise_extension", ".bin")
    if not isinstance(disguise_extension, str):
        raise ConfigError("配置.disguise_extension 必须是字符串")
    if strict:
        try:
            validate_disguise_extension(disguise_extension.strip())
        except ValueError as error:
            raise ConfigError(f"配置.disguise_extension：{error}") from error
    return disguise_extension.strip()


def _build_app_config(
    raw_config: dict[str, Any],
    *,
    layers: list[LayerConfig],
    source_paths: list[str],
    winrar_path: str,
    sevenzip_path: str,
    output_directory: str,
    compress_mode: str,
    disguise_extension: str,
) -> AppConfig:
    """按已解析的必填字段组装 AppConfig，布尔开关在此统一补默认值。"""
    return AppConfig(
        winrar_path=winrar_path,
        sevenzip_path=sevenzip_path,
        source_path=source_paths[0] if source_paths else "",
        source_paths=source_paths,
        compress_mode=compress_mode,
        output_directory=output_directory,
        overwrite_existing=require_boolean(
            raw_config,
            "overwrite_existing",
            "配置",
        ),
        confirm_before_start=require_boolean(
            raw_config,
            "confirm_before_start",
            "配置",
        ),
        # 缺省时显示 WinRAR 压缩界面。
        show_winrar_gui=(
            True
            if "show_winrar_gui" not in raw_config
            else require_boolean(raw_config, "show_winrar_gui", "配置")
        ),
        layers=layers,
        # 隐私与归档选项缺省时使用各自的默认值。
        add_padding=optional_boolean(raw_config, "add_padding", "配置", False),
        randomize_layer_names=optional_boolean(
            raw_config, "randomize_layer_names", "配置", False
        ),
        hide_source_name=optional_boolean(
            raw_config, "hide_source_name", "配置", False
        ),
        disguise_outer_extension=optional_boolean(
            raw_config, "disguise_outer_extension", "配置", False
        ),
        disguise_extension=disguise_extension,
        randomize_timestamps=optional_boolean(
            raw_config, "randomize_timestamps", "配置", False
        ),
        verify_after_compress=optional_boolean(
            raw_config, "verify_after_compress", "配置", True
        ),
        cleanup_on_failure=optional_boolean(
            raw_config, "cleanup_on_failure", "配置", False
        ),
        # 缺省时保存配置中的密码。
        persist_passwords=optional_boolean(
            raw_config, "persist_passwords", "配置", True
        ),
        delete_inner_after_verify=optional_boolean(
            raw_config, "delete_inner_after_verify", "配置", True
        ),
    )


def parse_config(
    raw_config: dict[str, Any], *, allow_incomplete: bool = False
) -> AppConfig:
    """把 JSON 对象解析为任务配置，草稿模式允许路径与层名尚未填完。"""
    version = raw_config.get("config_version")
    if version != CONFIG_VERSION:
        raise ConfigError(
            f"config_version 必须是 {CONFIG_VERSION}，当前值为 {version!r}"
        )

    raw_layers = raw_config.get("layers")
    if not isinstance(raw_layers, list) or not raw_layers:
        raise ConfigError("layers 必须是至少包含一项的数组")

    layers = [
        parse_layer_config(raw_layer, layer_index, strict=not allow_incomplete)
        for layer_index, raw_layer in enumerate(raw_layers)
    ]
    source_paths = parse_source_paths(raw_config, strict=not allow_incomplete)
    winrar_path, sevenzip_path, output_directory = _parse_path_fields(
        raw_config, allow_incomplete=allow_incomplete
    )

    return _build_app_config(
        raw_config,
        layers=layers,
        source_paths=source_paths,
        winrar_path=winrar_path,
        sevenzip_path=sevenzip_path,
        output_directory=output_directory,
        compress_mode=_parse_compress_mode_field(raw_config),
        disguise_extension=_parse_disguise_extension_field(raw_config, strict=not allow_incomplete),
    )
