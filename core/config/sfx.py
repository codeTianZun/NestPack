"""自解压字段的类型、脚本值和格式能力校验。"""

from __future__ import annotations

from typing import Any

from core.models import ConfigError, SfxConfig


def parse_sfx_config(raw: Any, *, strict: bool = True) -> SfxConfig:
    """读取可缺省的自解压设置，草稿保留尚未完成的脚本输入。"""
    if not isinstance(raw, dict):
        raise ConfigError("sfx 必须是 JSON 对象")
    defaults = SfxConfig().to_json_dict()
    values: dict[str, Any] = {}
    for key, default in defaults.items():
        value = raw.get(key, default)
        if type(value) is not type(default):
            raise ConfigError(f"sfx.{key} 必须是{'布尔值' if key == 'enabled' else '字符串'}")
        values[key] = value
    for key, choices in (
        ("target", ("windows", "linux")),
        ("overwrite", ("ask", "overwrite", "skip")),
        ("silent", ("show", "hide_start", "hide_all")),
    ):
        if values[key] not in choices:
            raise ConfigError(f"sfx.{key} 必须是 {' / '.join(choices)}")
    settings = SfxConfig(**values)
    if strict and settings.enabled:
        validate_sfx_config(settings)
    return settings


def validate_sfx_config(settings: SfxConfig) -> None:
    """校验实际写入接收者自解压脚本的内容。"""
    if not settings.template_path.strip():
        raise ConfigError("自解压模板请填写 auto 或模板文件路径")
    for key in ("title", "extract_path", "setup"):
        value = getattr(settings, key)
        if any(ord(character) < 32 for character in value):
            raise ConfigError(f"sfx.{key} 必须为单行文本，不能含控制字符")
    if any(ord(character) < 32 and character not in "\r\n\t" for character in settings.text):
        raise ConfigError("sfx.text 不能含换行、制表符以外的控制字符")
    if any(line.lstrip().startswith("}") for line in settings.text.splitlines()):
        raise ConfigError("自解压说明的行首不能是 }（含前置空白，RAR 文本块结束符）")
    if settings.target == "linux" and (
        settings.icon_path or settings.logo_path or settings.title or settings.text
        or settings.extract_path or settings.setup
        or settings.overwrite != "ask" or settings.silent != "show"
    ):
        raise ConfigError(
            "Linux 原生自解压采用终端模块；图标、界面及预设解压行为适用于 Windows 目标，"
            "请调整交付目标或清空对应设置"
        )
